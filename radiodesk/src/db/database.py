from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session as SASession
from src.models.base import Base
from src.models.user import User
from src.models.emission import Emission
from src.models.podcast import Podcast
from src.models.audit_log import AuditLog
import bcrypt


class Database:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )
        event.listen(self._engine, "connect", self._set_sqlite_pragma)
        self._SessionFactory = sessionmaker(bind=self._engine)

    @staticmethod
    def _set_sqlite_pragma(dbapi_conn, _connection_record) -> None:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    def init(self) -> None:
        Base.metadata.create_all(self._engine)
        self._ensure_admin()

    def session(self) -> SASession:
        return self._SessionFactory()

    def _ensure_admin(self) -> None:
        with self.session() as s:
            from src.models.user import Role
            existing = s.query(User).filter_by(role=Role.ADMIN).first()
            if existing:
                return
            pw_hash = bcrypt.hashpw(b"admin123456", bcrypt.gensalt(12)).decode()
            admin = User(
                username="admin",
                email="admin@radiodesk.local",
                password_hash=pw_hash,
                role=Role.ADMIN,
                active=True,
            )
            s.add(admin)
            s.commit()
