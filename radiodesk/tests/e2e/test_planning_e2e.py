"""E2E tests for PlanningPage — vues Liste / Semaine / Mois."""
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from PySide6.QtWidgets import QApplication
from src.models.base import Base
from src.models.user import User, Role
from src.models.emission import Emission
from src.db.database import Database
from src.config.settings import Settings
from src.auth.auth_service import AuthService
from src.controllers.emission_controller import EmissionController
import bcrypt


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def planning_db(tmp_path):
    db_path = tmp_path / "planning_e2e.db"
    settings = Settings(base_dir=tmp_path)
    settings.db_path = db_path

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    pw_hash = bcrypt.hashpw(b"admin123456", bcrypt.gensalt(12)).decode()
    admin = User(username="admin", email="admin@planning.com",
                 password_hash=pw_hash, role=Role.ADMIN, active=True)
    session.add(admin)
    session.flush()

    # Deux émissions à des dates connues
    now = datetime.now()
    week_start = now - timedelta(days=now.weekday())
    em1 = Emission(
        title="Matinale",
        start_dt=week_start.replace(hour=8, minute=0, second=0, microsecond=0),
        end_dt=week_start.replace(hour=10, minute=0, second=0, microsecond=0),
        color="#6B2EA6",
        user_id=admin.id,
    )
    em2 = Emission(
        title="Soirée",
        start_dt=week_start.replace(hour=20, minute=0, second=0, microsecond=0),
        end_dt=week_start.replace(hour=22, minute=0, second=0, microsecond=0),
        color="#2563EB",
        user_id=admin.id,
    )
    session.add_all([em1, em2])
    session.commit()

    yield session, settings
    session.close()


@pytest.fixture
def planning_page(qtbot, planning_db, qapp):
    from src.views.windows.planning_page import PlanningPage

    db_session, settings = planning_db
    auth = AuthService(db_session, settings.session_timeout_minutes)
    auth.login("admin", "admin123456")
    ctrl = EmissionController(db_session, auth)

    page = PlanningPage(ctrl=ctrl, auth=auth)
    qtbot.addWidget(page)
    page.show()
    qtbot.waitExposed(page)
    return page


class TestPlanningPageViews:
    def test_view_buttons_exist(self, planning_page):
        assert hasattr(planning_page, "_viewbtn_liste")
        assert hasattr(planning_page, "_viewbtn_semaine")
        assert hasattr(planning_page, "_viewbtn_mois")

    def test_default_view_is_liste(self, planning_page):
        assert planning_page._view == "liste"
        assert planning_page._stack.currentIndex() == 0
        assert planning_page._viewbtn_liste.isChecked()

    def test_switch_to_week_view(self, planning_page, qtbot):
        planning_page._switch_view("semaine")
        assert planning_page._view == "semaine"
        assert planning_page._stack.currentIndex() == 1
        assert planning_page._viewbtn_semaine.isChecked()
        assert not planning_page._viewbtn_liste.isChecked()

    def test_switch_to_month_view(self, planning_page, qtbot):
        planning_page._switch_view("mois")
        assert planning_page._view == "mois"
        assert planning_page._stack.currentIndex() == 2
        assert planning_page._viewbtn_mois.isChecked()

    def test_switch_back_to_list(self, planning_page):
        planning_page._switch_view("semaine")
        planning_page._switch_view("liste")
        assert planning_page._stack.currentIndex() == 0
        assert planning_page._viewbtn_liste.isChecked()

    def test_nav_buttons_hidden_in_list_view(self, planning_page):
        planning_page._switch_view("liste")
        assert not planning_page._btn_prev.isVisible()
        assert not planning_page._btn_next.isVisible()
        assert not planning_page._btn_today.isVisible()

    def test_nav_buttons_visible_in_week_view(self, planning_page):
        planning_page._switch_view("semaine")
        assert planning_page._btn_prev.isVisible()
        assert planning_page._btn_next.isVisible()
        assert planning_page._btn_today.isVisible()

    def test_nav_buttons_visible_in_month_view(self, planning_page):
        planning_page._switch_view("mois")
        assert planning_page._btn_prev.isVisible()
        assert planning_page._btn_today.isVisible()

    def test_week_period_label_not_empty(self, planning_page):
        planning_page._switch_view("semaine")
        assert planning_page._period_label.text() != ""

    def test_month_period_label_not_empty(self, planning_page):
        planning_page._switch_view("mois")
        label = planning_page._period_label.text()
        assert label != ""

    def test_next_week_navigation(self, planning_page):
        planning_page._switch_view("semaine")
        label_before = planning_page._period_label.text()
        planning_page._on_next()
        label_after = planning_page._period_label.text()
        assert label_before != label_after

    def test_prev_week_navigation(self, planning_page):
        planning_page._switch_view("semaine")
        planning_page._on_today()
        label_today = planning_page._period_label.text()
        planning_page._on_prev()
        assert planning_page._period_label.text() != label_today

    def test_today_resets_to_current_week(self, planning_page):
        planning_page._switch_view("semaine")
        planning_page._on_next()
        planning_page._on_next()
        planning_page._on_today()
        assert planning_page._ref_date.date() == datetime.now().date()

    def test_next_month_navigation(self, planning_page):
        planning_page._switch_view("mois")
        label_before = planning_page._period_label.text()
        planning_page._on_next()
        label_after = planning_page._period_label.text()
        assert label_before != label_after

    def test_prev_month_navigation(self, planning_page):
        planning_page._switch_view("mois")
        planning_page._on_today()
        label_before = planning_page._period_label.text()
        planning_page._on_prev()
        assert planning_page._period_label.text() != label_before

    def test_week_table_has_7_columns(self, planning_page):
        planning_page._switch_view("semaine")
        assert planning_page._week_table.columnCount() == 7

    def test_week_table_has_hour_rows(self, planning_page):
        from src.views.windows.planning_page import HOURS_START, HOURS_END
        planning_page._switch_view("semaine")
        assert planning_page._week_table.rowCount() == HOURS_END - HOURS_START

    def test_month_table_has_7_columns(self, planning_page):
        planning_page._switch_view("mois")
        assert planning_page._month_table.columnCount() == 7

    def test_month_table_has_6_rows(self, planning_page):
        planning_page._switch_view("mois")
        assert planning_page._month_table.rowCount() == 6

    def test_emissions_appear_in_week_view(self, planning_page):
        """Au moins une cellule non-vide dans la grille de la semaine courante."""
        planning_page._switch_view("semaine")
        from src.views.windows.planning_page import HOURS_START, HOURS_END
        found = False
        for r in range(HOURS_END - HOURS_START):
            for c in range(7):
                item = planning_page._week_table.item(r, c)
                if item and item.text().strip():
                    found = True
                    break
        assert found, "Aucune émission affichée dans la vue semaine"

    def test_month_day_cells_have_widgets(self, planning_page):
        planning_page._switch_view("mois")
        has_widget = any(
            planning_page._month_table.cellWidget(r, c) is not None
            for r in range(6) for c in range(7)
        )
        assert has_widget

    def test_liste_view_shows_table(self, planning_page):
        planning_page._switch_view("liste")
        assert planning_page._table.rowCount() >= 2
