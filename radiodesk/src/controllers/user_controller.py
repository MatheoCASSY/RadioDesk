from __future__ import annotations
from typing import Optional
import bcrypt
from sqlalchemy.orm import Session
from src.models.user import User, Role
from src.models.audit_log import AuditLog
from src.auth.auth_service import AuthService


class UserController:
    def __init__(self, db: Session, auth: AuthService) -> None:
        self._db = db
        self._auth = auth

    def list_all(self) -> list[User]:
        self._auth.require_role(Role.ADMIN)
        return self._db.query(User).order_by(User.username).all()

    def get(self, user_id: int) -> Optional[User]:
        self._auth.require_role(Role.ADMIN)
        return self._db.query(User).filter_by(id=user_id).first()

    def create(self, username: str, email: str, password: str, role: Role = Role.ANIMATEUR) -> User:
        current = self._auth.require_role(Role.ADMIN)
        if self._db.query(User).filter_by(username=username).first():
            raise ValueError(f"Le nom d'utilisateur '{username}' est déjà pris")
        if self._db.query(User).filter_by(email=email).first():
            raise ValueError(f"L'email '{email}' est déjà utilisé")
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()
        user = User(username=username, email=email, password_hash=pw_hash, role=role, active=True)
        self._db.add(user)
        self._db.add(AuditLog(user_id=current.user_id, action="user_create", details=f"username={username} role={role.value}"))
        self._db.commit()
        self._db.refresh(user)
        return user

    def update_role(self, user_id: int, new_role: Role) -> User:
        self._auth.require_role(Role.ADMIN)
        user = self._db.query(User).filter_by(id=user_id).first()
        if not user:
            raise ValueError("Utilisateur introuvable")
        user.role = new_role
        self._db.commit()
        return user

    def toggle_active(self, user_id: int) -> User:
        current = self._auth.require_role(Role.ADMIN)
        user = self._db.query(User).filter_by(id=user_id).first()
        if not user:
            raise ValueError("Utilisateur introuvable")
        user.active = not user.active
        self._db.add(AuditLog(user_id=current.user_id, action="user_toggle_active", details=f"user_id={user_id} active={user.active}"))
        self._db.commit()
        return user

    def delete(self, user_id: int) -> None:
        current = self._auth.require_role(Role.ADMIN)
        if current.user_id == user_id:
            raise ValueError("Impossible de supprimer votre propre compte")
        user = self._db.query(User).filter_by(id=user_id).first()
        if not user:
            raise ValueError("Utilisateur introuvable")
        self._db.add(AuditLog(user_id=current.user_id, action="user_delete", details=f"username={user.username}"))
        self._db.delete(user)
        self._db.commit()
