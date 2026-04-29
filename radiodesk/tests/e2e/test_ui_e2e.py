import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from src.models.base import Base
from src.models.user import User, Role
from src.db.database import Database
from src.config.settings import Settings
from src.auth.auth_service import AuthService
import bcrypt


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def e2e_db(tmp_path):
    db_path = tmp_path / "test_e2e.db"
    settings = Settings(base_dir=tmp_path)
    settings.db_path = db_path

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    pw_hash = bcrypt.hashpw(b"admin123456", bcrypt.gensalt(12)).decode()
    admin = User(username="admin", email="admin@e2e.com", password_hash=pw_hash, role=Role.ADMIN, active=True)
    session.add(admin)

    tech_hash = bcrypt.hashpw(b"tech123456", bcrypt.gensalt(12)).decode()
    technicien = User(username="technicien", email="tech@e2e.com", password_hash=tech_hash, role=Role.TECHNICIEN, active=True)
    session.add(technicien)
    session.commit()

    yield session, settings
    session.close()


class MockDB:
    def __init__(self, session):
        self._session = session

    def session(self):
        return self._session

    def init(self):
        pass


class TestLoginWindowE2E:
    def test_login_window_opens(self, qtbot, e2e_db):
        from src.views.windows.login_window import LoginWindow
        db_session, settings = e2e_db
        win = LoginWindow(db=MockDB(db_session), settings=settings)
        qtbot.addWidget(win)
        win.show()
        assert win.isVisible()

    def test_empty_fields_show_error(self, qtbot, e2e_db):
        from src.views.windows.login_window import LoginWindow
        db_session, settings = e2e_db
        win = LoginWindow(db=MockDB(db_session), settings=settings)
        qtbot.addWidget(win)
        win.show()

        win._on_login()
        assert "champs" in win._error_label.text().lower()

    def test_wrong_password_shows_error(self, qtbot, e2e_db):
        from src.views.windows.login_window import LoginWindow
        db_session, settings = e2e_db
        win = LoginWindow(db=MockDB(db_session), settings=settings)
        qtbot.addWidget(win)
        win.show()

        win._username_input.setText("admin")
        win._password_input.setText("wrongpassword")
        win._on_login()
        assert win._error_label.text() != ""

    def test_correct_login_opens_main_window(self, qtbot, e2e_db):
        from src.views.windows.login_window import LoginWindow
        db_session, settings = e2e_db
        win = LoginWindow(db=MockDB(db_session), settings=settings)
        qtbot.addWidget(win)
        win.show()

        win._username_input.setText("admin")
        win._password_input.setText("admin123456")
        win._on_login()

        assert hasattr(win, "_main_window")
        qtbot.addWidget(win._main_window)


class TestEmissionDialogE2E:
    def test_dialog_validates_empty_title(self, qtbot):
        from src.views.dialogs.emission_dialog import EmissionDialog
        dlg = EmissionDialog()
        qtbot.addWidget(dlg)
        dlg.show()

        dlg._validate_and_accept()
        assert not dlg.result()

    def test_dialog_validates_date_order(self, qtbot):
        from src.views.dialogs.emission_dialog import EmissionDialog
        from PySide6.QtCore import QDateTime
        dlg = EmissionDialog()
        qtbot.addWidget(dlg)
        dlg.show()

        dlg._title_input.setText("Test")
        dlg._start_input.setDateTime(QDateTime(2024, 7, 1, 12, 0))
        dlg._end_input.setDateTime(QDateTime(2024, 7, 1, 10, 0))
        dlg._validate_and_accept()
        assert "fin" in dlg._error_label.text().lower()

    def test_dialog_returns_correct_data(self, qtbot):
        from src.views.dialogs.emission_dialog import EmissionDialog
        from PySide6.QtCore import QDateTime
        dlg = EmissionDialog()
        qtbot.addWidget(dlg)
        dlg.show()

        dlg._title_input.setText("Mon Émission")
        dlg._start_input.setDateTime(QDateTime(2024, 7, 1, 10, 0))
        dlg._end_input.setDateTime(QDateTime(2024, 7, 1, 11, 0))
        dlg._validate_and_accept()

        data = dlg.get_data()
        assert data["title"] == "Mon Émission"
        assert data["end_dt"] > data["start_dt"]


class TestPodcastsPageE2E:
    """E2E : ajout d'un podcast à une émission."""

    def test_add_podcast_requires_emission_selection(self, qtbot, e2e_db, tmp_path):
        from src.views.windows.podcasts_page import PodcastsPage
        from src.controllers.podcast_controller import PodcastController
        from src.controllers.emission_controller import EmissionController

        db_session, settings = e2e_db
        auth = AuthService(db_session, settings.session_timeout_minutes)
        auth.login("admin", "admin123456")

        emission_ctrl = EmissionController(db_session, auth)
        podcast_ctrl = PodcastController(db_session, auth, settings.media_path)

        page = PodcastsPage(podcast_ctrl=podcast_ctrl, emission_ctrl=emission_ctrl)
        qtbot.addWidget(page)
        page.show()

        # Sans sélection d'émission, le bouton ajouter doit afficher un warning
        # On simule le clic via _on_add directement
        page._on_add()
        # Si pas d'émission sélectionnée, _on_add doit gérer sans crash
        assert page._emission_combo.currentData() is None

    def test_podcasts_list_visible_after_emission_selection(self, qtbot, e2e_db, tmp_path):
        from src.views.windows.podcasts_page import PodcastsPage
        from src.controllers.podcast_controller import PodcastController
        from src.controllers.emission_controller import EmissionController
        from datetime import datetime, timedelta

        db_session, settings = e2e_db
        auth = AuthService(db_session, settings.session_timeout_minutes)
        auth.login("admin", "admin123456")

        emission_ctrl = EmissionController(db_session, auth)
        podcast_ctrl = PodcastController(db_session, auth, settings.media_path)

        now = datetime.now()
        emission_ctrl.create(
            title="Émission Podcast E2E",
            start_dt=now,
            end_dt=now + timedelta(hours=1),
        )

        page = PodcastsPage(podcast_ctrl=podcast_ctrl, emission_ctrl=emission_ctrl)
        qtbot.addWidget(page)
        page.show()

        assert page._emission_combo.count() > 1
        page._emission_combo.setCurrentIndex(1)
        assert page._list.isVisible()


class TestAccessControlE2E:
    """E2E : vérification accès refusé hors du rôle."""

    def test_technicien_cannot_create_emission(self, e2e_db):
        from src.controllers.emission_controller import EmissionController
        from datetime import datetime, timedelta

        db_session, settings = e2e_db
        auth = AuthService(db_session, settings.session_timeout_minutes)
        auth.login("technicien", "tech123456")

        ctrl = EmissionController(db_session, auth)
        now = datetime.now()

        with pytest.raises(PermissionError):
            ctrl.create(
                title="Émission interdite",
                start_dt=now,
                end_dt=now + timedelta(hours=1),
            )

    def test_technicien_can_update_statut_technique(self, e2e_db):
        from src.controllers.emission_controller import EmissionController
        from src.auth.auth_service import AuthService
        from datetime import datetime, timedelta

        db_session, settings = e2e_db
        admin_auth = AuthService(db_session, settings.session_timeout_minutes)
        admin_auth.login("admin", "admin123456")
        admin_ctrl = EmissionController(db_session, admin_auth)
        now = datetime.now()
        em = admin_ctrl.create(
            title="Émission pour technicien",
            start_dt=now,
            end_dt=now + timedelta(hours=1),
        )
        admin_auth.logout()

        tech_auth = AuthService(db_session, settings.session_timeout_minutes)
        tech_auth.login("technicien", "tech123456")
        tech_ctrl = EmissionController(db_session, tech_auth)

        updated = tech_ctrl.update_statut_technique(em.id, "en_test")
        assert updated.statut_technique == "en_test"

    def test_technicien_cannot_delete_emission(self, e2e_db):
        from src.controllers.emission_controller import EmissionController
        from src.auth.auth_service import AuthService
        from datetime import datetime, timedelta

        db_session, settings = e2e_db
        admin_auth = AuthService(db_session, settings.session_timeout_minutes)
        admin_auth.login("admin", "admin123456")
        admin_ctrl = EmissionController(db_session, admin_auth)
        now = datetime.now()
        em = admin_ctrl.create(
            title="Émission à ne pas supprimer",
            start_dt=now,
            end_dt=now + timedelta(hours=1),
        )
        admin_auth.logout()

        tech_auth = AuthService(db_session, settings.session_timeout_minutes)
        tech_auth.login("technicien", "tech123456")
        tech_ctrl = EmissionController(db_session, tech_auth)

        with pytest.raises(PermissionError):
            tech_ctrl.delete(em.id)
