from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
import requests


class ApiClient:
    def __init__(self, base_url: str, token: Optional[str] = None, timeout: int = 15) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _headers(self) -> dict:
        h: dict = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _get(self, path: str, params: Optional[dict] = None) -> requests.Response:
        r = requests.get(f"{self.base_url}{path}", headers=self._headers(),
                         params=params, timeout=self.timeout)
        if r.status_code == 401:
            print(f"[DEBUG 401] URL: {self.base_url}{path}")
            print(f"[DEBUG 401] Token présent: {bool(self.token)}, début: {self.token[:30] if self.token else 'None'}")
            print(f"[DEBUG 401] Réponse: {r.text[:200]}")
        return r

    def _post(self, path: str, json_body: Optional[dict] = None,
              files: Optional[dict] = None) -> requests.Response:
        headers = self._headers()
        if files:
            headers.pop("Accept", None)
            return requests.post(f"{self.base_url}{path}", headers=headers,
                                 files=files, timeout=60)
        headers["Content-Type"] = "application/json"
        return requests.post(f"{self.base_url}{path}", headers=headers,
                             json=json_body, timeout=self.timeout)

    def _patch(self, path: str, json_body: dict) -> requests.Response:
        headers = {**self._headers(), "Content-Type": "application/json"}
        return requests.patch(f"{self.base_url}{path}", headers=headers,
                              json=json_body, timeout=self.timeout)

    def _put(self, path: str, json_body: dict) -> requests.Response:
        headers = {**self._headers(), "Content-Type": "application/json"}
        return requests.put(f"{self.base_url}{path}", headers=headers,
                            json=json_body, timeout=self.timeout)

    def _delete(self, path: str) -> requests.Response:
        return requests.delete(f"{self.base_url}{path}", headers=self._headers(),
                               timeout=self.timeout)

    # ── Music endpoints ──────────────────────────────────────────────────────

    def get_musics_page(self, page: int = 0) -> dict:
        r = self._get("/musics", {"page": page})
        r.raise_for_status()
        ct = r.headers.get("content-type", "")
        if "application/json" in ct or r.text.strip().startswith(("{", "[")):
            data = r.json()
            total_pages_header = r.headers.get("Total-Page")
            next_page_header = r.headers.get("Next-Page")
            return {
                "data": data,
                "total_pages_header": int(total_pages_header) if total_pages_header else None,
                "next_page_header": int(next_page_header) if next_page_header else None,
            }
        return {"data": r.text, "total_pages_header": None, "next_page_header": None}

    def get_all_musics(self) -> list[dict]:
        all_musics: dict[str, dict] = {}
        page = 0
        visited: set[int] = set()
        for _ in range(500):
            if page in visited:
                break
            visited.add(page)
            result = self.get_musics_page(page)
            raw = result["data"]
            rows = self._normalize_music_list(raw)
            new = 0
            for m in rows:
                if m.get("id") and m["id"] not in all_musics:
                    all_musics[m["id"]] = m
                    new += 1
            next_p = result["next_page_header"]
            total_p = result["total_pages_header"]
            if next_p is not None and next_p != page:
                page = next_p
            elif total_p is not None and page + 1 < total_p:
                page += 1
            elif new > 0 and total_p is None:
                page += 1
            else:
                break
        return list(all_musics.values())

    def _normalize_music_list(self, raw) -> list[dict]:
        if isinstance(raw, list):
            return [self._normalize_music(m) for m in raw]
        if isinstance(raw, dict):
            items = raw.get("musics") or raw.get("data") or []
            return [self._normalize_music(m) for m in items]
        if isinstance(raw, str):
            return self._parse_csv_musics(raw)
        return []

    def _normalize_music(self, item) -> dict:
        if not isinstance(item, dict):
            return {}
        meta = item.get("metadata", {}) or {}
        def pick(*keys):
            for k in keys:
                v = item.get(k) or meta.get(k)
                if v:
                    return str(v)
            return ""
        tags_raw = item.get("tags") or meta.get("tags") or []
        if isinstance(tags_raw, str):
            tags = [t.strip() for t in tags_raw.replace(";", ",").split(",") if t.strip()]
        elif isinstance(tags_raw, list):
            tags = [str(t) for t in tags_raw if t]
        else:
            tags = []
        return {
            "id": pick("id", "ID", "music_id", "uuid", "key"),
            "title": pick("title", "name", "filename") or "Sans titre",
            "artist": pick("artist", "author"),
            "album": pick("album"),
            "genre": pick("genre"),
            "year": pick("year"),
            "duration": pick("duration", "length"),
            "uploadedAt": pick("uploadedAt", "uploaded_at", "createdAt", "created_at"),
            "tags": tags,
        }

    def _parse_csv_musics(self, text: str) -> list[dict]:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if len(lines) < 2:
            return []
        headers = [h.strip() for h in lines[0].split(",")]
        results = []
        for line in lines[1:]:
            parts = [p.strip() for p in line.split(",")]
            row = dict(zip(headers, parts))
            m = self._normalize_music(row)
            if m.get("id"):
                results.append(m)
        return results

    def patch_music(self, music_id: str, payload: dict) -> None:
        r = self._patch(f"/musics/{requests.utils.quote(music_id, safe='')}", payload)
        r.raise_for_status()

    def delete_music(self, music_id: str) -> None:
        r = self._delete(f"/musics/{requests.utils.quote(music_id, safe='')}")
        r.raise_for_status()

    def upload_music(self, file_path: Path) -> dict:
        with open(file_path, "rb") as f:
            r = self._post("/musics", files={"file": (file_path.name, f, "audio/mpeg")})
        r.raise_for_status()
        return r.json() if r.text else {}

    # ── Playlist endpoints ────────────────────────────────────────────────────

    def get_playlists(self) -> list[dict]:
        r = self._get("/playlists")
        r.raise_for_status()
        raw = r.json()
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict):
            return raw.get("playlists") or raw.get("data") or []
        return []

    def get_playlist(self, playlist_id: str) -> dict:
        r = self._get(f"/playlists/{playlist_id}")
        r.raise_for_status()
        raw = r.json()
        if isinstance(raw, dict) and "data" in raw:
            return raw["data"]
        return raw

    def create_playlist(self, name: str, author: str = "radiodesk") -> dict:
        r = self._post("/playlists", {"name": name, "author": author})
        r.raise_for_status()
        return r.json()

    def save_playlist(self, playlist_id: str, name: str, author: str,
                      music_ids: list[str]) -> None:
        payload = {"name": name, "author": author, "musics": music_ids}
        r = self._patch(f"/playlists/{playlist_id}", payload)
        if not r.ok:
            r = self._put(f"/playlists/{playlist_id}", payload)
        r.raise_for_status()

    def delete_playlist(self, playlist_id: str) -> None:
        r = self._delete(f"/playlists/{playlist_id}")
        r.raise_for_status()

    # ── Connection test ───────────────────────────────────────────────────────

    def test_connection(self) -> str:
        try:
            r = self._get("/musics", {"page": 0})
            if r.ok:
                return f"✅ Connexion OK (HTTP {r.status_code})"
            return f"⚠️ Réponse HTTP {r.status_code}"
        except requests.exceptions.ConnectionError:
            return "❌ Impossible de joindre l'API"
        except requests.exceptions.Timeout:
            return "❌ Timeout — API trop lente"
        except Exception as e:
            return f"❌ Erreur: {e}"


class ApiConfigManager:
    def __init__(self, config_path: Path) -> None:
        self._path = config_path

    def load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"api_base_url": "", "api_token": ""}

    def save(self, config: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    def get_client(self) -> Optional[ApiClient]:
        cfg = self.load()
        url = cfg.get("api_base_url", "").strip()
        if not url:
            return None
        return ApiClient(url, token=cfg.get("api_token", "").strip() or None)
