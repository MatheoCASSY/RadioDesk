from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from sqlalchemy.orm import Session
from src.models.user import User, Role


@dataclass
class SessionData:
    user_id: int
    username: str
    role: Role
    logged_in_at: datetime
    timeout_minutes: int

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.logged_in_at + timedelta(minutes=self.timeout_minutes)

    def refresh(self) -> None:
        self.logged_in_at = datetime.utcnow()


class AuthService:
    def __init__(self, db_session: Session, timeout_minutes: int = 30) -> None:
        self._db = db_session
        self._timeout = timeout_minutes
        self._current_session: Optional[SessionData] = None

    def login(self, username: str, password: str) -> SessionData:
        user = self._db.query(User).filter_by(username=username, active=True).first()
        if not user:
            raise ValueError("Identifiants invalides")
        if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            raise ValueError("Identifiants invalides")
        self._current_session = SessionData(
            user_id=user.id,
            username=user.username,
            role=user.role,
            logged_in_at=datetime.utcnow(),
            timeout_minutes=self._timeout,
        )
        return self._current_session

    def logout(self) -> None:
        self._current_session = None

    def get_current_session(self) -> Optional[SessionData]:
        if self._current_session and self._current_session.is_expired():
            self._current_session = None
        return self._current_session

    def require_session(self) -> SessionData:
        session = self.get_current_session()
        if not session:
            raise PermissionError("Non authentifié")
        return session

    def require_role(self, *roles: Role) -> SessionData:
        session = self.require_session()
        if session.role not in roles:
            raise PermissionError(f"Rôle requis: {[r.value for r in roles]}")
        return session

    def set_cognito_session(self, email: str, groups: list[str]) -> SessionData:
        """Inject a synthetic session from a Cognito login (no DB user required)."""
        from src.models.user import Role
        is_admin = any(g in ("admins", "devs") for g in groups)
        role = Role.ADMIN if is_admin else Role.ANIMATEUR
        self._current_session = SessionData(
            user_id=0,
            username=email or "cognito-user",
            role=role,
            logged_in_at=datetime.utcnow(),
            timeout_minutes=self._timeout,
        )
        return self._current_session

    def change_password(self, user_id: int, old_password: str, new_password: str) -> None:
        user = self._db.query(User).filter_by(id=user_id).first()
        if not user:
            raise ValueError("Utilisateur introuvable")
        if not bcrypt.checkpw(old_password.encode(), user.password_hash.encode()):
            raise ValueError("Ancien mot de passe incorrect")
        user.password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt(12)).decode()
        self._db.commit()
