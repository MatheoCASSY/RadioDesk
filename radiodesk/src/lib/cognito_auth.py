from __future__ import annotations
import base64
import hashlib
import json
import secrets
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional

import requests
from PySide6.QtCore import QThread, Signal

CLIENT_ID = "2ivt73p7f9md1758qgi95dnfhd"
COGNITO_DOMAIN = "eu-west-1e3giVfjQy.auth.eu-west-1.amazoncognito.com"
TOKEN_ENDPOINT = f"https://{COGNITO_DOMAIN}/oauth2/token"
AUTH_ENDPOINT = f"https://{COGNITO_DOMAIN}/oauth2/authorize"
LOGOUT_ENDPOINT = f"https://{COGNITO_DOMAIN}/logout"
REDIRECT_URI = "http://localhost:3000/dashboard"
SCOPES = "openid email profile"

CALLBACK_HTML = (
    "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
    "<title>RadioDesk</title>"
    "<style>body{font-family:Segoe UI,sans-serif;display:flex;flex-direction:column;"
    "align-items:center;justify-content:center;min-height:100vh;margin:0;"
    "background:linear-gradient(135deg,#3d1a6e,#6B2EA6,#AF6F56);color:white;}"
    "h1{font-size:2rem;margin-bottom:.5rem;}p{opacity:.85;}</style></head>"
    "<body><h1>&#10003; Connexion r&eacute;ussie</h1>"
    "<p>Vous pouvez fermer cet onglet et revenir sur RadioDesk.</p></body></html>"
).encode("utf-8")


def _generate_pkce() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def _build_auth_url(challenge: str, state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    return f"{AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"


def _decode_jwt_payload(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return {}
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        return {}


class _CallbackHandler(BaseHTTPRequestHandler):
    code: Optional[str] = None
    state: Optional[str] = None
    received = threading.Event()

    def do_GET(self) -> None:  # noqa: N802
        print(f"[DEBUG] Requête reçue : {self.path}")
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/dashboard":
            self.send_response(404)
            self.end_headers()
            return
        params = dict(urllib.parse.parse_qsl(parsed.query))
        _CallbackHandler.code = params.get("code")
        _CallbackHandler.state = params.get("state")
        print(f"[DEBUG] Code reçu : {bool(_CallbackHandler.code)}")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(CALLBACK_HTML)
        _CallbackHandler.received.set()

    def log_message(self, *args) -> None:  # noqa: ANN002
        pass  # suppress server log output


class CognitoLoginThread(QThread):
    tokens_ready = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._verifier, challenge = _generate_pkce()
        self._state = secrets.token_hex(16)
        self._auth_url = _build_auth_url(challenge, self._state)

    @property
    def auth_url(self) -> str:
        return self._auth_url

    def run(self) -> None:
        _CallbackHandler.code = None
        _CallbackHandler.received.clear()

        try:
            server = HTTPServer(("localhost", 3000), _CallbackHandler)
            server.timeout = 1
            print("[DEBUG] Serveur démarré sur http://localhost:3000")
        except OSError as e:
            self.error_occurred.emit(f"Port 3000 occupé : {e}")
            return

        def _serve() -> None:
            while not _CallbackHandler.received.is_set():
                server.handle_request()

        t = threading.Thread(target=_serve, daemon=True)
        t.start()
        _CallbackHandler.received.wait(timeout=180)
        server.server_close()

        code = _CallbackHandler.code
        if not code:
            self.error_occurred.emit("Délai dépassé ou connexion annulée.")
            return

        try:
            resp = requests.post(
                TOKEN_ENDPOINT,
                data={
                    "grant_type": "authorization_code",
                    "client_id": CLIENT_ID,
                    "code": code,
                    "redirect_uri": REDIRECT_URI,
                    "code_verifier": self._verifier,
                },
                timeout=15,
            )
            resp.raise_for_status()
            tokens = resp.json()
            # Decode user info from id_token
            id_token = tokens.get("id_token", "")
            payload = _decode_jwt_payload(id_token)
            tokens["_user"] = {
                "email": payload.get("email") or payload.get("cognito:username", ""),
                "username": payload.get("preferred_username") or payload.get("cognito:username", ""),
                "groups": payload.get("cognito:groups", []),
                "sub": payload.get("sub", ""),
            }
            self.tokens_ready.emit(tokens)
        except Exception as exc:
            self.error_occurred.emit(f"Échange de token échoué : {exc}")


class CognitoSession:
    def __init__(self, tokens: dict) -> None:
        self._tokens = tokens
        self._user = tokens.get("_user", {})

    @property
    def access_token(self) -> str:
        return self._tokens.get("access_token", "")

    @property
    def id_token(self) -> str:
        return self._tokens.get("id_token", "")

    @property
    def email(self) -> str:
        return self._user.get("email", "")

    @property
    def username(self) -> str:
        return self._user.get("username", "") or self.email

    @property
    def groups(self) -> list[str]:
        return self._user.get("groups", [])

    def is_admin(self) -> bool:
        return any(g in ("admins", "devs") for g in self.groups)

    def is_programmateur(self) -> bool:
        return any(g in ("programmateur", "admins", "devs") for g in self.groups)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        saved = {k: v for k, v in self._tokens.items() if not k.startswith("_")}
        saved["_user"] = self._user
        path.write_text(json.dumps(saved, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Optional["CognitoSession"]:
        if not path.exists():
            return None
        try:
            tokens = json.loads(path.read_text(encoding="utf-8"))
            if not tokens.get("access_token"):
                return None
            return cls(tokens)
        except Exception:
            return None

    def logout_url(self, redirect_after: str = "http://localhost:3000/dashboard") -> str:
        params = {
            "client_id": CLIENT_ID,
            "logout_uri": redirect_after,
        }
        return f"{LOGOUT_ENDPOINT}?{urllib.parse.urlencode(params)}"
