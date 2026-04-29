import pytest
from src.auth.auth_service import AuthService
from src.models.user import Role


class TestAuthService:
    def test_login_success(self, db_session, admin_user):
        auth = AuthService(db_session)
        session = auth.login("admin", "admin123456")
        assert session.username == "admin"
        assert session.role == Role.ADMIN

    def test_login_wrong_password(self, db_session, admin_user):
        auth = AuthService(db_session)
        with pytest.raises(ValueError, match="Identifiants invalides"):
            auth.login("admin", "wrongpassword")

    def test_login_unknown_user(self, db_session):
        auth = AuthService(db_session)
        with pytest.raises(ValueError, match="Identifiants invalides"):
            auth.login("nobody", "pass")

    def test_logout_clears_session(self, db_session, admin_user):
        auth = AuthService(db_session)
        auth.login("admin", "admin123456")
        assert auth.get_current_session() is not None
        auth.logout()
        assert auth.get_current_session() is None

    def test_require_session_raises_when_not_logged(self, db_session):
        auth = AuthService(db_session)
        with pytest.raises(PermissionError):
            auth.require_session()

    def test_require_role_wrong_role(self, db_session, animateur_user):
        auth = AuthService(db_session)
        auth.login("animateur1", "anim123456")
        with pytest.raises(PermissionError):
            auth.require_role(Role.ADMIN)

    def test_require_role_correct(self, db_session, admin_user):
        auth = AuthService(db_session)
        auth.login("admin", "admin123456")
        session = auth.require_role(Role.ADMIN)
        assert session.username == "admin"

    def test_session_refresh(self, db_session, admin_user):
        auth = AuthService(db_session, timeout_minutes=30)
        session = auth.login("admin", "admin123456")
        before = session.logged_in_at
        session.refresh()
        assert session.logged_in_at >= before

    def test_inactive_user_cannot_login(self, db_session, animateur_user):
        animateur_user.active = False
        db_session.commit()
        auth = AuthService(db_session)
        with pytest.raises(ValueError, match="Identifiants invalides"):
            auth.login("animateur1", "anim123456")
