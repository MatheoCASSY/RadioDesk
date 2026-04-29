import pytest
from datetime import datetime, timedelta
from src.controllers.emission_controller import EmissionController
from src.models.user import Role


class TestEmissionController:
    def test_create_emission_as_admin(self, db_session, auth_admin, admin_user):
        ctrl = EmissionController(db_session, auth_admin)
        em = ctrl.create(
            title="Test",
            start_dt=datetime(2024, 7, 1, 10, 0),
            end_dt=datetime(2024, 7, 1, 11, 0),
        )
        assert em.id is not None
        assert em.title == "Test"

    def test_create_emission_as_animateur(self, db_session, auth_animateur, animateur_user):
        ctrl = EmissionController(db_session, auth_animateur)
        em = ctrl.create(
            title="Anim show",
            start_dt=datetime(2024, 7, 1, 10, 0),
            end_dt=datetime(2024, 7, 1, 11, 0),
        )
        assert em.user_id == animateur_user.id

    def test_create_fails_end_before_start(self, db_session, auth_admin):
        ctrl = EmissionController(db_session, auth_admin)
        with pytest.raises(ValueError, match="date de fin"):
            ctrl.create(
                title="Bad",
                start_dt=datetime(2024, 7, 1, 11, 0),
                end_dt=datetime(2024, 7, 1, 10, 0),
            )

    def test_list_returns_all_for_admin(self, db_session, auth_admin, sample_emission):
        ctrl = EmissionController(db_session, auth_admin)
        emissions = ctrl.list_all()
        assert len(emissions) >= 1

    def test_update_emission(self, db_session, auth_admin, sample_emission):
        ctrl = EmissionController(db_session, auth_admin)
        updated = ctrl.update(sample_emission.id, title="Updated Title")
        assert updated.title == "Updated Title"

    def test_delete_emission(self, db_session, auth_admin, sample_emission):
        ctrl = EmissionController(db_session, auth_admin)
        ctrl.delete(sample_emission.id)
        assert ctrl.get(sample_emission.id) is None

    def test_animateur_cannot_delete_others_emission(self, db_session, auth_animateur, sample_emission):
        ctrl = EmissionController(db_session, auth_animateur)
        with pytest.raises(PermissionError):
            ctrl.delete(sample_emission.id)

    def test_requires_auth_to_list(self, db_session):
        from src.auth.auth_service import AuthService
        unauth = AuthService(db_session)
        ctrl = EmissionController(db_session, unauth)
        with pytest.raises(PermissionError):
            ctrl.list_all()

    def test_filter_by_date_range(self, db_session, auth_admin, sample_emission):
        ctrl = EmissionController(db_session, auth_admin)
        results = ctrl.list_all(
            from_dt=datetime(2024, 6, 1, 0, 0),
            to_dt=datetime(2024, 6, 1, 23, 59),
        )
        assert any(e.id == sample_emission.id for e in results)

    def test_filter_excludes_out_of_range(self, db_session, auth_admin, sample_emission):
        ctrl = EmissionController(db_session, auth_admin)
        results = ctrl.list_all(
            from_dt=datetime(2024, 7, 1, 0, 0),
            to_dt=datetime(2024, 7, 31, 23, 59),
        )
        assert not any(e.id == sample_emission.id for e in results)
