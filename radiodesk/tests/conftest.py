import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.base import Base
from src.models.user import User, Role
from src.models.emission import Emission
from src.db.database import Database
from src.auth.auth_service import AuthService
import bcrypt
from datetime import datetime, timedelta


@pytest.fixture
def in_memory_engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(in_memory_engine):
    Session = sessionmaker(bind=in_memory_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def admin_user(db_session):
    pw_hash = bcrypt.hashpw(b"admin123456", bcrypt.gensalt(12)).decode()
    user = User(username="admin", email="admin@test.com", password_hash=pw_hash,
                role=Role.ADMIN, active=True)
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def animateur_user(db_session):
    pw_hash = bcrypt.hashpw(b"anim123456", bcrypt.gensalt(12)).decode()
    user = User(username="animateur1", email="anim@test.com", password_hash=pw_hash,
                role=Role.ANIMATEUR, active=True)
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def auth_admin(db_session, admin_user):
    auth = AuthService(db_session, timeout_minutes=30)
    auth.login("admin", "admin123456")
    return auth


@pytest.fixture
def auth_animateur(db_session, animateur_user):
    auth = AuthService(db_session, timeout_minutes=30)
    auth.login("animateur1", "anim123456")
    return auth


@pytest.fixture
def sample_emission(db_session, admin_user):
    em = Emission(
        title="Matinale",
        description="Émission du matin",
        start_dt=datetime(2024, 6, 1, 8, 0),
        end_dt=datetime(2024, 6, 1, 10, 0),
        color="#2563EB",
        user_id=admin_user.id,
    )
    db_session.add(em)
    db_session.commit()
    return em
