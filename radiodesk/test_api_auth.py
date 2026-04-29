"""Test rapide auth API Cognito — lance avec: python test_api_auth.py"""
import json
import sys
from pathlib import Path
import requests

API_BASE = "https://nu8n9r0hl5.execute-api.eu-west-1.amazonaws.com"
SESSION_FILE = Path.home() / ".radiodesk" / "cognito_session.json"


def test(label: str, token: str | None) -> None:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = requests.get(f"{API_BASE}/musics", headers=headers, params={"page": 0}, timeout=10)
        print(f"[{label}] HTTP {r.status_code} — {r.text[:150]}")
    except Exception as e:
        print(f"[{label}] ERREUR: {e}")


if not SESSION_FILE.exists():
    print(f"Pas de session trouvée dans {SESSION_FILE}")
    print("Lance l'app et connecte-toi via Cognito d'abord.")
    sys.exit(1)

tokens = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
access_token = tokens.get("access_token")
id_token = tokens.get("id_token")

print(f"Session trouvée: {SESSION_FILE}\n")
test("Sans token     ", None)
test("access_token   ", access_token)
test("id_token       ", id_token)
