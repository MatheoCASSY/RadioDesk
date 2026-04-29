from __future__ import annotations
import shutil
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session
from src.models.podcast import Podcast
from src.models.audit_log import AuditLog
from src.models.user import Role
from src.auth.auth_service import AuthService


class PodcastController:
    def __init__(self, db: Session, auth: AuthService, media_path: Path) -> None:
        self._db = db
        self._auth = auth
        self._media_path = media_path

    def list_for_emission(self, emission_id: int) -> list[Podcast]:
        self._auth.require_session()
        return self._db.query(Podcast).filter_by(emission_id=emission_id).all()

    def add(self, emission_id: int, title: str, source_path: Path,
            description: Optional[str] = None, duration_seconds: Optional[int] = None) -> Podcast:
        session = self._auth.require_role(Role.ADMIN, Role.ANIMATEUR)
        allowed = {".mp3", ".wav", ".ogg", ".m4a"}
        if source_path.suffix.lower() not in allowed:
            raise ValueError(f"Type de fichier non autorisé: {source_path.suffix}")
        dest = self._media_path / f"{emission_id}_{source_path.name}"
        shutil.copy2(source_path, dest)
        podcast = Podcast(
            title=title,
            description=description,
            file_path=str(dest),
            duration_seconds=duration_seconds,
            emission_id=emission_id,
        )
        self._db.add(podcast)
        self._db.add(AuditLog(user_id=session.user_id, action="podcast_add", details=f"emission_id={emission_id} title={title}"))
        self._db.commit()
        self._db.refresh(podcast)
        return podcast

    def delete(self, podcast_id: int) -> None:
        session = self._auth.require_role(Role.ADMIN, Role.ANIMATEUR)
        podcast = self._db.query(Podcast).filter_by(id=podcast_id).first()
        if not podcast:
            raise ValueError("Podcast introuvable")
        file_path = Path(podcast.file_path)
        self._db.add(AuditLog(user_id=session.user_id, action="podcast_delete", details=f"id={podcast_id} title={podcast.title}"))
        self._db.delete(podcast)
        self._db.commit()
        if file_path.exists():
            file_path.unlink()
