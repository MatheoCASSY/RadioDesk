import pytest
from datetime import datetime
from pathlib import Path
from src.controllers.emission_controller import EmissionController
from src.controllers.user_controller import UserController
from src.controllers.podcast_controller import PodcastController
from src.models.user import Role


class TestEmissionIntegration:
    def test_full_crud_emission(self, db_session, auth_admin):
        ctrl = EmissionController(db_session, auth_admin)

        em = ctrl.create(
            title="Integration Show",
            start_dt=datetime(2024, 8, 1, 9, 0),
            end_dt=datetime(2024, 8, 1, 11, 0),
            description="Test intégration",
        )
        assert em.id is not None

        all_em = ctrl.list_all()
        assert any(e.id == em.id for e in all_em)

        updated = ctrl.update(em.id, title="Updated Show", color="#7c3aed")
        assert updated.title == "Updated Show"
        assert updated.color == "#7c3aed"

        ctrl.delete(em.id)
        assert ctrl.get(em.id) is None

    def test_animateur_owns_only_own_emissions(self, db_session, auth_admin, auth_animateur, admin_user, animateur_user):
        admin_ctrl = EmissionController(db_session, auth_admin)
        anim_ctrl = EmissionController(db_session, auth_animateur)

        admin_em = admin_ctrl.create(
            title="Admin emission",
            start_dt=datetime(2024, 8, 2, 9, 0),
            end_dt=datetime(2024, 8, 2, 10, 0),
        )
        anim_em = anim_ctrl.create(
            title="Anim emission",
            start_dt=datetime(2024, 8, 3, 9, 0),
            end_dt=datetime(2024, 8, 3, 10, 0),
        )

        with pytest.raises(PermissionError):
            anim_ctrl.delete(admin_em.id)

        anim_ctrl.delete(anim_em.id)
        assert anim_ctrl.get(anim_em.id) is None


class TestUserIntegration:
    def test_full_user_lifecycle(self, db_session, auth_admin):
        ctrl = UserController(db_session, auth_admin)

        user = ctrl.create("newstaff", "staff@test.com", "securepass123", Role.ANIMATEUR)
        assert user.id is not None

        users = ctrl.list_all()
        assert any(u.id == user.id for u in users)

        updated = ctrl.update_role(user.id, Role.TECHNICIEN)
        assert updated.role == Role.TECHNICIEN

        ctrl.toggle_active(user.id)
        db_session.refresh(user)
        assert user.active is False

        ctrl.toggle_active(user.id)
        db_session.refresh(user)
        assert user.active is True

        ctrl.delete(user.id)
        assert ctrl.get(user.id) is None


class TestPodcastIntegration:
    def test_add_and_delete_podcast(self, db_session, auth_admin, sample_emission, tmp_path):
        fake_audio = tmp_path / "test_show.mp3"
        fake_audio.write_bytes(b"ID3" + b"\x00" * 100)

        ctrl = PodcastController(db_session, auth_admin, tmp_path / "media")
        (tmp_path / "media").mkdir(exist_ok=True)

        pod = ctrl.add(
            emission_id=sample_emission.id,
            title="Mon podcast",
            source_path=fake_audio,
        )
        assert pod.id is not None
        assert pod.title == "Mon podcast"

        pods = ctrl.list_for_emission(sample_emission.id)
        assert any(p.id == pod.id for p in pods)

        ctrl.delete(pod.id)
        pods_after = ctrl.list_for_emission(sample_emission.id)
        assert not any(p.id == pod.id for p in pods_after)

    def test_rejects_invalid_file_type(self, db_session, auth_admin, sample_emission, tmp_path):
        fake_file = tmp_path / "document.pdf"
        fake_file.write_bytes(b"%PDF")
        ctrl = PodcastController(db_session, auth_admin, tmp_path / "media")
        (tmp_path / "media").mkdir(exist_ok=True)
        with pytest.raises(ValueError, match="non autorisé"):
            ctrl.add(emission_id=sample_emission.id, title="Bad", source_path=fake_file)


class TestAuthIntegration:
    def test_login_then_create_then_logout(self, db_session, animateur_user):
        from src.auth.auth_service import AuthService
        auth = AuthService(db_session, timeout_minutes=30)

        session = auth.login("animateur1", "anim123456")
        assert session is not None

        ctrl = EmissionController(db_session, auth)
        em = ctrl.create(
            title="Live show",
            start_dt=datetime(2024, 9, 1, 14, 0),
            end_dt=datetime(2024, 9, 1, 16, 0),
        )
        assert em.id is not None

        auth.logout()

        with pytest.raises(PermissionError):
            ctrl.list_all()
