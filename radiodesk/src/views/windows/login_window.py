from __future__ import annotations
import webbrowser
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QStackedWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QLinearGradient, QColor, QPainter
from src.auth.auth_service import AuthService
from src.db.database import Database
from src.config.settings import Settings
from src.lib.cognito_auth import CognitoLoginThread, CognitoSession
from pathlib import Path


class _GradientWidget(QWidget):
    def paintEvent(self, _event):
        p = QPainter(self)
        g = QLinearGradient(0, 0, self.width(), self.height())
        g.setColorAt(0.0, QColor("#1a0d2e"))
        g.setColorAt(0.45, QColor("#6B2EA6"))
        g.setColorAt(1.0, QColor("#AF6F56"))
        p.fillRect(self.rect(), g)


class LoginWindow(QMainWindow):
    def __init__(self, db: Database, settings: Settings) -> None:
        super().__init__()
        self._db = db
        self._settings = settings
        self._db_session = db.session()
        self._auth = AuthService(self._db_session, settings.session_timeout_minutes)
        self._cognito_thread: CognitoLoginThread | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("RadioDesk — Connexion")
        self.setFixedSize(520, 640)

        bg = _GradientWidget()
        self.setCentralWidget(bg)
        outer = QVBoxLayout(bg)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.setContentsMargins(44, 44, 44, 44)

        # Card
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 22px;
                border: none;
            }
        """)
        card.setFixedWidth(400)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(40, 38, 40, 36)
        cl.setSpacing(0)

        # Logo
        logo_row = QHBoxLayout()
        dot = QLabel("●")
        dot.setStyleSheet("color:#6B2EA6;font-size:20px;background:transparent;border:none;")
        name = QLabel("RadioDesk")
        name.setStyleSheet("color:#6B2EA6;font-size:22px;font-weight:800;background:transparent;border:none;")
        logo_row.addWidget(dot)
        logo_row.addSpacing(4)
        logo_row.addWidget(name)
        logo_row.addStretch()
        cl.addLayout(logo_row)
        cl.addSpacing(6)
        sub = QLabel("Panneau d'administration FluffRadio")
        sub.setStyleSheet("color:#9ca3af;font-size:12px;background:transparent;border:none;")
        cl.addWidget(sub)
        cl.addSpacing(28)

        # Stack: main view (Cognito + divider + local) vs loading
        self._stack = QStackedWidget()
        cl.addWidget(self._stack)

        # ── Page 0 : formulaire ──────────────────────────────────────────
        form_page = QWidget()
        form_page.setStyleSheet("background:transparent;")
        fl = QVBoxLayout(form_page)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(0)

        # Cognito button
        cognito_btn = QPushButton("  Se connecter avec FluffRadio")
        cognito_btn.setObjectName("primaryBtn")
        cognito_btn.setFixedHeight(48)
        cognito_btn.setStyleSheet("""
            QPushButton {
                background: #6B2EA6; color: white; border: none;
                border-radius: 10px; font-size: 14px; font-weight: 700;
            }
            QPushButton:hover { background: #5a2490; }
        """)
        cognito_btn.clicked.connect(self._on_cognito_login)
        fl.addWidget(cognito_btn)

        cognito_hint = QLabel("Utilise ton compte Cognito FluffRadio")
        cognito_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cognito_hint.setStyleSheet("color:#9ca3af;font-size:11px;background:transparent;border:none;margin-top:6px;")
        fl.addWidget(cognito_hint)

        fl.addSpacing(22)

        # Divider
        div_row = QHBoxLayout()
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet("color:#e5e7eb;background:#e5e7eb;border:none;max-height:1px;")
        div_lbl = QLabel("ou connexion locale")
        div_lbl.setStyleSheet("color:#9ca3af;font-size:11px;background:transparent;border:none;")
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet("color:#e5e7eb;background:#e5e7eb;border:none;max-height:1px;")
        div_row.addWidget(line1)
        div_row.addSpacing(8)
        div_row.addWidget(div_lbl)
        div_row.addSpacing(8)
        div_row.addWidget(line2)
        fl.addLayout(div_row)
        fl.addSpacing(18)

        # Local login form
        user_lbl = QLabel("Identifiant")
        user_lbl.setStyleSheet("font-size:12px;font-weight:700;color:#374151;background:transparent;border:none;")
        fl.addWidget(user_lbl)
        fl.addSpacing(4)
        self._username_input = QLineEdit()
        self._username_input.setPlaceholderText("admin")
        self._username_input.setFixedHeight(40)
        fl.addWidget(self._username_input)
        fl.addSpacing(12)

        pw_lbl = QLabel("Mot de passe")
        pw_lbl.setStyleSheet("font-size:12px;font-weight:700;color:#374151;background:transparent;border:none;")
        fl.addWidget(pw_lbl)
        fl.addSpacing(4)
        self._password_input = QLineEdit()
        self._password_input.setPlaceholderText("••••••••")
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_input.setFixedHeight(40)
        self._password_input.returnPressed.connect(self._on_local_login)
        fl.addWidget(self._password_input)
        fl.addSpacing(8)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color:#dc2626;font-size:12px;background:transparent;border:none;")
        self._error_label.setFixedHeight(16)
        fl.addWidget(self._error_label)
        fl.addSpacing(10)

        local_btn = QPushButton("Connexion locale")
        local_btn.setFixedHeight(42)
        local_btn.setStyleSheet("""
            QPushButton {
                background: white; color: #374151;
                border: 1.5px solid #e5e7eb; border-radius: 10px;
                font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background: #f9fafb; }
        """)
        local_btn.clicked.connect(self._on_local_login)
        fl.addWidget(local_btn)

        self._stack.addWidget(form_page)

        # ── Page 1 : Cognito en attente ─────────────────────────────────
        wait_page = QWidget()
        wait_page.setStyleSheet("background:transparent;")
        wl = QVBoxLayout(wait_page)
        wl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wl.setContentsMargins(0, 20, 0, 20)
        wl.setSpacing(14)

        spinner = QLabel("🔐")
        spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spinner.setStyleSheet("font-size:40px;background:transparent;border:none;")
        wl.addWidget(spinner)

        wait_title = QLabel("Connexion en cours…")
        wait_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wait_title.setStyleSheet("font-size:15px;font-weight:700;color:#6B2EA6;background:transparent;border:none;")
        wl.addWidget(wait_title)

        self._wait_info = QLabel("En attente dans votre navigateur.\nConnectez-vous à votre compte FluffRadio.")
        self._wait_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._wait_info.setWordWrap(True)
        self._wait_info.setStyleSheet("color:#6b7280;font-size:13px;background:transparent;border:none;")
        wl.addWidget(self._wait_info)

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setFixedHeight(38)
        cancel_btn.setFixedWidth(120)
        cancel_btn.setStyleSheet("""
            QPushButton { background:white;color:#374151;border:1.5px solid #e5e7eb;
                border-radius:8px;font-size:13px; }
            QPushButton:hover { background:#f9fafb; }
        """)
        cancel_btn.clicked.connect(self._cancel_cognito)
        wl.addWidget(cancel_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self._stack.addWidget(wait_page)

        outer.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

        version = QLabel("RadioDesk v1.0.0 · FluffRadio Admin Panel")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet("color:rgba(255,255,255,0.35);font-size:11px;background:transparent;border:none;")
        outer.addWidget(version)

    # ── Cognito ─────────────────────────────────────────────────────────────

    def _on_cognito_login(self) -> None:
        self._stack.setCurrentIndex(1)
        self._cognito_thread = CognitoLoginThread()
        self._cognito_thread.tokens_ready.connect(self._on_cognito_success)
        self._cognito_thread.error_occurred.connect(self._on_cognito_error)
        self._cognito_thread.start()
        webbrowser.open(self._cognito_thread.auth_url)

    def _on_cognito_success(self, tokens: dict) -> None:
        session = CognitoSession(tokens)
        token_path = Path(self._settings.base_dir) / "cognito_session.json"
        session.save(token_path)
        # Inject a synthetic local session so controllers don't crash
        self._auth.set_cognito_session(session.email, session.groups)
        self._open_main_window(cognito_session=session)

    def _on_cognito_error(self, msg: str) -> None:
        self._stack.setCurrentIndex(0)
        self._error_label.setText(f"Cognito : {msg}")

    def _cancel_cognito(self) -> None:
        if self._cognito_thread:
            self._cognito_thread.terminate()
            self._cognito_thread = None
        self._stack.setCurrentIndex(0)

    # ── Local ────────────────────────────────────────────────────────────────

    def _on_local_login(self) -> None:
        username = self._username_input.text().strip()
        password = self._password_input.text()
        self._error_label.setText("")
        if not username or not password:
            self._error_label.setText("Veuillez remplir tous les champs.")
            return
        try:
            self._auth.login(username, password)
            self._open_main_window(cognito_session=None)
        except ValueError as e:
            self._error_label.setText(str(e))

    # ── Open main ────────────────────────────────────────────────────────────

    def _open_main_window(self, cognito_session=None) -> None:
        from src.views.windows.main_window import MainWindow
        self._main_window = MainWindow(
            db=self._db,
            db_session=self._db_session,
            auth=self._auth,
            settings=self._settings,
            cognito_session=cognito_session,
        )
        self._main_window.show()
        self.close()
