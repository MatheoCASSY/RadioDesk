import pytest
from src.controllers.user_controller import UserController
from src.models.user import Role


class TestUserController:
    def test_create_user(self, db_session, auth_admin):
        ctrl = UserController(db_session, auth_admin)
        user = ctrl.create("newuser", "new@test.com", "password123", Role.ANIMATEUR)
        assert user.id is not None
        assert user.username == "newuser"

    def test_create_duplicate_username_fails(self, db_session, auth_admin, admin_user):
        ctrl = UserController(db_session, auth_admin)
        with pytest.raises(ValueError, match="déjà pris"):
            ctrl.create("admin", "other@test.com", "pass123")

    def test_create_duplicate_email_fails(self, db_session, auth_admin, admin_user):
        ctrl = UserController(db_session, auth_admin)
        with pytest.raises(ValueError, match="déjà utilisé"):
            ctrl.create("newuser", "admin@test.com", "pass123")

    def test_list_requires_admin(self, db_session, auth_animateur):
        ctrl = UserController(db_session, auth_animateur)
        with pytest.raises(PermissionError):
            ctrl.list_all()

    def test_update_role(self, db_session, auth_admin, animateur_user):
        ctrl = UserController(db_session, auth_admin)
        updated = ctrl.update_role(animateur_user.id, Role.TECHNICIEN)
        assert updated.role == Role.TECHNICIEN

    def test_toggle_active(self, db_session, auth_admin, animateur_user):
        ctrl = UserController(db_session, auth_admin)
        assert animateur_user.active is True
        ctrl.toggle_active(animateur_user.id)
        db_session.refresh(animateur_user)
        assert animateur_user.active is False

    def test_cannot_delete_self(self, db_session, auth_admin, admin_user):
        ctrl = UserController(db_session, auth_admin)
        with pytest.raises(ValueError, match="propre compte"):
            ctrl.delete(admin_user.id)
