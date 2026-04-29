from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QAbstractItemView, QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from src.controllers.user_controller import UserController
from src.models.user import Role


class UsersPage(QWidget):
    def __init__(self, ctrl: UserController) -> None:
        super().__init__()
        self._ctrl = ctrl
        self._setup_ui()
        self._load()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Gestion des utilisateurs")
        f = QFont()
        f.setPointSize(18)
        f.setBold(True)
        title.setFont(f)
        header.addWidget(title)
        header.addStretch()
        add_btn = QPushButton("+ Nouvel utilisateur")
        add_btn.setObjectName("primaryBtn")
        add_btn.setStyleSheet("")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._on_add)
        header.addWidget(add_btn)
        layout.addLayout(header)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["Nom d'utilisateur", "Email", "Rôle", "Actif", "Actions"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setColumnWidth(4, 180)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet("""
            QTableWidget { border: 1px solid #e5e7eb; border-radius: 8px; background: white; gridline-color: #f3f4f6; }
            QHeaderView::section { background: #f3ecfa; font-weight: 600; font-size: 12px; padding: 8px; border: none; border-bottom: 1px solid #e5e7eb; color: #5a2490; }
            QTableWidget::item { padding: 8px; font-size: 13px; }
        """)
        layout.addWidget(self._table)

    def _load(self) -> None:
        try:
            users = self._ctrl.list_all()
        except Exception:
            users = []
        self._table.setRowCount(0)
        for user in users:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(user.username))
            self._table.setItem(row, 1, QTableWidgetItem(user.email))
            self._table.setItem(row, 2, QTableWidgetItem(user.role.value))
            self._table.setItem(row, 3, QTableWidgetItem("Oui" if user.active else "Non"))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(6)

            toggle_btn = QPushButton("Désactiver" if user.active else "Activer")
            toggle_btn.setObjectName("editBtn")
            toggle_btn.setStyleSheet("")
            toggle_btn.clicked.connect(lambda _, u=user: self._on_toggle(u))

            del_btn = QPushButton("Supprimer")
            del_btn.setObjectName("dangerBtn")
            del_btn.setStyleSheet("")
            del_btn.clicked.connect(lambda _, u=user: self._on_delete(u))

            btn_layout.addWidget(toggle_btn)
            btn_layout.addWidget(del_btn)
            self._table.setCellWidget(row, 4, btn_widget)

    def _on_add(self) -> None:
        dlg = _UserDialog(parent=self)
        if dlg.exec():
            data = dlg.get_data()
            try:
                self._ctrl.create(**data)
                self._load()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def _on_toggle(self, user) -> None:
        try:
            self._ctrl.toggle_active(user.id)
            self._load()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def _on_delete(self, user) -> None:
        reply = QMessageBox.question(self, "Confirmation",
                                     f"Supprimer l'utilisateur « {user.username} » ?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._ctrl.delete(user.id)
                self._load()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))


class _UserDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nouvel utilisateur")
        self.setMinimumWidth(380)
        self.setModal(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        form = QFormLayout()
        self._username = QLineEdit()
        self._username.setFixedHeight(34)
        form.addRow("Nom d'utilisateur *", self._username)
        self._email = QLineEdit()
        self._email.setFixedHeight(34)
        form.addRow("Email *", self._email)
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.setFixedHeight(34)
        form.addRow("Mot de passe *", self._password)
        self._role = QComboBox()
        for r in Role:
            self._role.addItem(r.value, r)
        form.addRow("Rôle", self._role)
        layout.addLayout(form)
        self._error = QLabel("")
        self._error.setStyleSheet("color: #dc2626; font-size: 12px;")
        layout.addWidget(self._error)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._validate)
        btns.rejected.connect(self.reject)
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("Créer")
        btns.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        layout.addWidget(btns)

    def _validate(self) -> None:
        if not self._username.text().strip() or not self._email.text().strip() or not self._password.text():
            self._error.setText("Tous les champs obligatoires doivent être remplis.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "username": self._username.text().strip(),
            "email": self._email.text().strip(),
            "password": self._password.text(),
            "role": self._role.currentData(),
        }
