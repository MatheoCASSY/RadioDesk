from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from src.models.emission import Emission
from src.models.audit_log import AuditLog
from src.models.user import Role
from src.auth.auth_service import AuthService


class EmissionController:
    def __init__(self, db: Session, auth: AuthService) -> None:
        self._db = db
        self._auth = auth

    def list_all(self, from_dt: Optional[datetime] = None, to_dt: Optional[datetime] = None) -> list[Emission]:
        self._auth.require_session()
        q = self._db.query(Emission)
        if from_dt:
            q = q.filter(Emission.start_dt >= from_dt)
        if to_dt:
            q = q.filter(Emission.end_dt <= to_dt)
        return q.order_by(Emission.start_dt).all()

    def get(self, emission_id: int) -> Optional[Emission]:
        self._auth.require_session()
        return self._db.query(Emission).filter_by(id=emission_id).first()

    def create(self, title: str, start_dt: datetime, end_dt: datetime,
               description: Optional[str] = None, color: str = "#2563EB") -> Emission:
        session = self._auth.require_role(Role.ADMIN, Role.ANIMATEUR)
        if end_dt <= start_dt:
            raise ValueError("La date de fin doit être après la date de début")
        emission = Emission(
            title=title,
            description=description,
            start_dt=start_dt,
            end_dt=end_dt,
            color=color,
            user_id=session.user_id,
        )
        self._db.add(emission)
        self._db.add(AuditLog(user_id=session.user_id, action="emission_create", details=f"title={title}"))
        self._db.commit()
        self._db.refresh(emission)
        return emission

    def update(self, emission_id: int, **kwargs) -> Emission:
        session = self._auth.require_session()
        emission = self._db.query(Emission).filter_by(id=emission_id).first()
        if not emission:
            raise ValueError("Émission introuvable")
        if session.role not in (Role.ADMIN,) and emission.user_id != session.user_id:
            raise PermissionError("Vous ne pouvez modifier que vos propres émissions")
        if "start_dt" in kwargs or "end_dt" in kwargs:
            start = kwargs.get("start_dt", emission.start_dt)
            end = kwargs.get("end_dt", emission.end_dt)
            if end <= start:
                raise ValueError("La date de fin doit être après la date de début")
        for key, value in kwargs.items():
            setattr(emission, key, value)
        self._db.add(AuditLog(user_id=session.user_id, action="emission_update", details=f"id={emission_id}"))
        self._db.commit()
        self._db.refresh(emission)
        return emission

    def update_statut_technique(self, emission_id: int, statut: str) -> Emission:
        session = self._auth.require_session()
        emission = self._db.query(Emission).filter_by(id=emission_id).first()
        if not emission:
            raise ValueError("Émission introuvable")
        emission.statut_technique = statut
        self._db.add(AuditLog(user_id=session.user_id, action="emission_statut", details=f"id={emission_id} statut={statut}"))
        self._db.commit()
        self._db.refresh(emission)
        return emission

    def delete(self, emission_id: int) -> None:
        session = self._auth.require_session()
        emission = self._db.query(Emission).filter_by(id=emission_id).first()
        if not emission:
            raise ValueError("Émission introuvable")
        if session.role not in (Role.ADMIN,) and emission.user_id != session.user_id:
            raise PermissionError("Accès refusé")
        self._db.add(AuditLog(user_id=session.user_id, action="emission_delete", details=f"id={emission_id} title={emission.title}"))
        self._db.delete(emission)
        self._db.commit()
