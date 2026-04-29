from __future__ import annotations
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from sqlalchemy.orm import Session
from src.auth.auth_service import AuthService
from src.db.database import Database
from src.config.settings import Settings
from src.models.user import Role
from src.controllers.emission_controller import EmissionController
from src.controllers.user_controller import UserController
from src.controllers.podcast_controller import PodcastController
from src.lib.api_client import ApiConfigManager
from src.lib.cognito_auth import CognitoSession

# Hardcoded API base URL (from the web app .env)
_API_BASE_URL = "https://nu8n9r0hl5.execute-api.eu-west-1.amazonaws.com"

PAGE_TITLES = {
    0: ("📊", "Tableau de bord"),
    1: ("📅", "Planning des émissions"),
    2: ("🎵", "Podcasts"),
    3: ("👥", "Utilisateurs"),
    4: ("🎶", "Bibliothèque musicale"),
    5: ("📋", "Playlists"),
    6: ("⚙️", "Paramètres API"),
}

NAV_SECTIONS = {
    "RADIO": [("📊  Tableau de bord", 0), ("📅  Planning", 1), ("🎵  Podcasts", 2)],
    "FLUFFRADIO": [("🎶  Bibliothèque", 4), ("📋  Playlists", 5)],
}


class MainWindow(QMainWindow):
    def __init__(
        self,
        db: Database,
        db_session: Session,
        auth: AuthService,
        settings: Settings,
        cognito_session: Optional[CognitoSession] = None,
    ) -> None:
        super().__init__()
        self._db = db
        self._session = db_session
        self._auth = auth
        self._settings = settings
        self._cognito = cognito_session
        self._emission_ctrl = EmissionController(db_session, auth)
        self._user_ctrl = UserController(db_session, auth)
        self._podcast_ctrl = PodcastController(db_session, auth, settings.media_path)
        config_path = Path(settings.base_dir) / "api_config.json"
        self._api_cfg = ApiConfigManager(config_path)

        # Ensure a synthetic local session exists so controllers work with Cognito
        if self._cognito:
            try:
                self._auth.require_session()
            except (PermissionError, ValueError):
                self._auth.set_cognito_session(self._cognito.email, self._cognito.groups)

        # Auto-inject Cognito token into API config if logged via Cognito
        if self._cognito and self._cognito.access_token:
            self._api_cfg.save({
                "api_base_url": _API_BASE_URL,
                "api_token": self._cognito.access_token,
            })

        self._setup_ui()

    # ── User info helper ─────────────────────────────────────────────────────
    # Returns (display_name, role_label, is_admin) regardless of auth mode.

    def _current_user(self) -> tuple[str, str, bool]:
        if self._cognito:
            name = self._cognito.email or self._cognito.username or "Utilisateur"
            is_admin = self._cognito.is_admin()
            role_label = "ADMIN" if is_admin else "PROGRAMMATEUR"
            return name, role_label, is_admin
        try:
            cur = self._auth.require_session()
            is_admin = cur.role == Role.ADMIN
            return cur.username, cur.role.value.upper(), is_admin
        except ValueError:
            return "Inconnu", "—", False

    # ── UI setup ─────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setWindowTitle("RadioDesk")
        self.setMinimumSize(1280, 780)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        right = QWidget()
        right.setObjectName("contentArea")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self._build_topbar())

        self._stack = QStackedWidget()
        right_layout.addWidget(self._stack, 1)
        root.addWidget(right, 1)

        self._load_pages()
        self._navigate(0)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(228)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 28, 14, 24)
        layout.setSpacing(0)

        dot = QLabel("●  RadioDesk")
        dot.setObjectName("logoLabel")
        f = QFont("Segoe UI", 17)
        f.setBold(True)
        dot.setFont(f)
        layout.addWidget(dot)

        sub = QLabel("ADMIN PANEL")
        sub.setObjectName("logoSub")
        layout.addWidget(sub)
        layout.addSpacing(24)

        username, role_label, is_admin = self._current_user()

        self._nav_buttons: list[QPushButton] = []
        self._nav_index_map: list[int] = []

        def _section_label(text: str) -> None:
            div = QFrame()
            div.setObjectName("sidebarDivider")
            div.setFixedHeight(1)
            layout.addSpacing(8)
            layout.addWidget(div)
            layout.addSpacing(8)
            lbl = QLabel(text)
            lbl.setObjectName("sideSection")
            layout.addWidget(lbl)
            layout.addSpacing(4)

        _section_label("RADIO")
        for label, idx in NAV_SECTIONS["RADIO"]:
            self._add_nav_btn(layout, label, idx)

        _section_label("FLUFFRADIO")
        for label, idx in NAV_SECTIONS["FLUFFRADIO"]:
            self._add_nav_btn(layout, label, idx)

        if is_admin:
            _section_label("ADMINISTRATION")
            self._add_nav_btn(layout, "👥  Utilisateurs", 3)
            self._add_nav_btn(layout, "⚙️  Paramètres API", 6)
        else:
            # Non-admin Cognito users can still access API config
            _section_label("CONFIGURATION")
            self._add_nav_btn(layout, "⚙️  Paramètres API", 6)

        layout.addStretch()

        div2 = QFrame()
        div2.setObjectName("sidebarDivider")
        div2.setFixedHeight(1)
        layout.addWidget(div2)
        layout.addSpacing(12)

        user_name = QLabel(username)
        user_name.setObjectName("sideUserName")
        layout.addWidget(user_name)
        role_lbl = QLabel(role_label)
        role_lbl.setObjectName("sideUserRole")
        layout.addWidget(role_lbl)

        # Show Cognito badge if applicable
        if self._cognito:
            cognito_badge = QLabel("🔐 FluffRadio SSO")
            cognito_badge.setStyleSheet(
                "color: #6B2EA6; font-size: 10px; background: transparent; border: none;"
            )
            layout.addWidget(cognito_badge)

        layout.addSpacing(10)

        logout_btn = QPushButton("⏻  Déconnexion")
        logout_btn.setObjectName("logoutBtn")
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.setFixedHeight(36)
        logout_btn.clicked.connect(self._logout)
        layout.addWidget(logout_btn)
        return sidebar

    def _add_nav_btn(self, layout, label: str, idx: int) -> None:
        btn = QPushButton(label)
        btn.setObjectName("navBtn")
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(40)
        self._nav_buttons.append(btn)
        self._nav_index_map.append(idx)
        btn.clicked.connect(lambda _, i=idx: self._navigate(i))
        layout.addWidget(btn)

    def _build_topbar(self) -> QFrame:
        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(62)
        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(28, 0, 28, 0)

        self._page_icon_lbl = QLabel("📊")
        self._page_icon_lbl.setStyleSheet("font-size: 18px; background: transparent; border: none;")
        self._page_title_lbl = QLabel("Tableau de bord")
        self._page_title_lbl.setObjectName("pageTitle")
        layout.addWidget(self._page_icon_lbl)
        layout.addSpacing(8)
        layout.addWidget(self._page_title_lbl)
        layout.addStretch()

        username, role_label, _ = self._current_user()
        user_lbl = QLabel(f"Connecté : {username}")
        user_lbl.setObjectName("topbarUser")
        layout.addWidget(user_lbl)
        layout.addSpacing(10)
        role_badge = QLabel(role_label)
        role_badge.setObjectName("roleBadge")
        layout.addWidget(role_badge)
        return topbar

    def _navigate(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        icon, title = PAGE_TITLES.get(index, ("", ""))
        self._page_icon_lbl.setText(icon)
        self._page_title_lbl.setText(title)
        for btn, idx in zip(self._nav_buttons, self._nav_index_map):
            btn.setChecked(idx == index)

    def _load_pages(self) -> None:
        from src.views.windows.dashboard_page import DashboardPage
        from src.views.windows.planning_page import PlanningPage
        from src.views.windows.podcasts_page import PodcastsPage
        from src.views.windows.music_manager_page import MusicManagerPage
        from src.views.windows.playlist_manager_page import PlaylistManagerPage
        from src.views.windows.api_config_page import ApiConfigPage

        _, _, is_admin = self._current_user()

        self._stack.addWidget(DashboardPage(self._emission_ctrl))             # 0
        self._stack.addWidget(PlanningPage(self._emission_ctrl, self._auth))  # 1
        self._stack.addWidget(PodcastsPage(self._podcast_ctrl, self._emission_ctrl))  # 2

        if is_admin and not self._cognito:
            from src.views.windows.users_page import UsersPage
            self._stack.addWidget(UsersPage(self._user_ctrl))                 # 3
        else:
            self._stack.addWidget(QWidget())                                  # 3 placeholder

        self._stack.addWidget(MusicManagerPage(self._api_cfg))                # 4
        self._stack.addWidget(PlaylistManagerPage(self._api_cfg))             # 5
        self._stack.addWidget(ApiConfigPage(self._api_cfg))                   # 6

    def _logout(self) -> None:
        if self._cognito:
            # Clear saved cognito session
            token_path = Path(self._settings.base_dir) / "cognito_session.json"
            if token_path.exists():
                token_path.unlink(missing_ok=True)
            # Clear auto-injected API token
            self._api_cfg.save({"api_base_url": _API_BASE_URL, "api_token": ""})
            self._cognito = None
        else:
            self._auth.logout()

        from src.views.windows.login_window import LoginWindow
        self._login_window = LoginWindow(db=self._db, settings=self._settings)
        self._login_window.show()
        self.close()
