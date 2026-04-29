from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTextEdit, QFrame
)
from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QFont
from src.lib.api_client import ApiConfigManager, ApiClient
from src.lib.worker import ApiWorker


class ApiConfigPage(QWidget):
    def __init__(self, config_manager: ApiConfigManager) -> None:
        super().__init__()
        self._cfg = config_manager
        self._pool = QThreadPool.globalInstance()
        self._setup_ui()
        self._load()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 32)
        layout.setSpacing(20)

        lbl = QLabel("Configuration de l'API FluffRadio")
        lbl.setObjectName("sectionTitle")
        layout.addWidget(lbl)

        desc = QLabel(
            "Renseignez l'URL de votre API et votre token JWT Cognito pour "
            "activer la bibliothèque musicale et la gestion des playlists."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #6b7280; font-size: 13px; background: transparent; border: none;")
        layout.addWidget(desc)

        card = QFrame()
        card.setObjectName("statCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(14)

        # URL
        url_lbl = QLabel("URL de base de l'API")
        url_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #374151; background: transparent; border: none;")
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://nu8n9r0hl5.execute-api.eu-west-1.amazonaws.com")
        self._url_input.setFixedHeight(40)
        card_layout.addWidget(url_lbl)
        card_layout.addWidget(self._url_input)

        # Token
        token_lbl = QLabel("Token JWT (Bearer)")
        token_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #374151; background: transparent; border: none;")
        self._token_input = QTextEdit()
        self._token_input.setPlaceholderText("eyJhbGciOi...")
        self._token_input.setFixedHeight(100)
        self._token_input.setStyleSheet("font-family: monospace; font-size: 11px;")
        card_layout.addWidget(token_lbl)
        card_layout.addWidget(self._token_input)

        # Buttons
        btn_row = QHBoxLayout()
        save_btn = QPushButton("Enregistrer")
        save_btn.setObjectName("primaryBtn")
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(self._save)

        test_btn = QPushButton("Tester la connexion")
        test_btn.setObjectName("accentBtn")
        test_btn.setFixedHeight(40)
        test_btn.clicked.connect(self._test)

        btn_row.addWidget(save_btn)
        btn_row.addWidget(test_btn)
        btn_row.addStretch()
        card_layout.addLayout(btn_row)

        self._status = QLabel("")
        self._status.setStyleSheet("font-size: 13px; background: transparent; border: none;")
        card_layout.addWidget(self._status)

        layout.addWidget(card)

        # Info
        info = QFrame()
        info.setObjectName("statCard")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(24, 16, 24, 16)
        info_lbl = QLabel(
            "💡  Pour obtenir un token JWT :\n"
            "1. Connectez-vous sur l'admin-panel-front dans votre navigateur\n"
            "2. Ouvrez les DevTools → Application → Local Storage\n"
            "3. Copiez la valeur de la clé 'id_token' ou 'access_token'"
        )
        info_lbl.setStyleSheet("color: #6b7280; font-size: 12px; background: transparent; border: none; line-height: 1.6;")
        info_lbl.setWordWrap(True)
        info_layout.addWidget(info_lbl)
        layout.addWidget(info)

        layout.addStretch()

    def _load(self) -> None:
        cfg = self._cfg.load()
        self._url_input.setText(cfg.get("api_base_url", ""))
        self._token_input.setPlainText(cfg.get("api_token", ""))

    def _save(self) -> None:
        self._cfg.save({
            "api_base_url": self._url_input.text().strip(),
            "api_token": self._token_input.toPlainText().strip(),
        })
        self._status.setText("✅ Configuration enregistrée.")
        self._status.setStyleSheet("color: #059669; font-size: 13px; background: transparent; border: none;")

    def _test(self) -> None:
        self._status.setText("⏳ Test en cours…")
        self._status.setStyleSheet("color: #6b7280; font-size: 13px; background: transparent; border: none;")
        url = self._url_input.text().strip()
        token = self._token_input.toPlainText().strip()
        client = ApiClient(url, token or None)
        worker = ApiWorker(client.test_connection)
        worker.signals.result.connect(self._on_test_result)
        self._pool.start(worker)

    def _on_test_result(self, msg: str) -> None:
        color = "#059669" if msg.startswith("✅") else "#dc2626"
        self._status.setText(msg)
        self._status.setStyleSheet(f"color: {color}; font-size: 13px; background: transparent; border: none;")
