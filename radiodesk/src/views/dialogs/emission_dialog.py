from __future__ import annotations
from datetime import datetime
from typing import Optional, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QTextEdit, QDateTimeEdit, QPushButton,
    QDialogButtonBox, QFrame, QColorDialog
)
from PySide6.QtCore import Qt, QDateTime
from PySide6.QtGui import QColor


class EmissionDialog(QDialog):
    def __init__(self, emission=None, parent=None) -> None:
        super().__init__(parent)
        self._emission = emission
        self._color = "#6B2EA6"
        self._setup_ui()
        if emission:
            self._populate(emission)

    def _setup_ui(self) -> None:
        self.setWindowTitle("Nouvelle émission" if not self._emission else "Modifier l'émission")
        self.setMinimumWidth(460)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 24)
        layout.setSpacing(16)

        # Titre dialog
        dlg_title = QLabel("Nouvelle émission" if not self._emission else "Modifier l'émission")
        dlg_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #6B2EA6; background: transparent; border: none;")
        layout.addWidget(dlg_title)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #e5e7eb; background: #e5e7eb; border: none; max-height: 1px;")
        layout.addWidget(sep)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._title_input = QLineEdit()
        self._title_input.setPlaceholderText("Titre de l'émission")
        self._title_input.setFixedHeight(38)
        form.addRow("Titre *", self._title_input)

        self._desc_input = QTextEdit()
        self._desc_input.setPlaceholderText("Description optionnelle…")
        self._desc_input.setFixedHeight(76)
        form.addRow("Description", self._desc_input)

        self._start_input = QDateTimeEdit()
        self._start_input.setDisplayFormat("dd/MM/yyyy HH:mm")
        self._start_input.setCalendarPopup(True)
        self._start_input.setDateTime(QDateTime.currentDateTime())
        self._start_input.setFixedHeight(38)
        form.addRow("Début *", self._start_input)

        self._end_input = QDateTimeEdit()
        self._end_input.setDisplayFormat("dd/MM/yyyy HH:mm")
        self._end_input.setCalendarPopup(True)
        self._end_input.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        self._end_input.setFixedHeight(38)
        form.addRow("Fin *", self._end_input)

        # Color picker
        color_row = QHBoxLayout()
        self._color_preview = QFrame()
        self._color_preview.setFixedSize(38, 38)
        self._color_preview.setStyleSheet(f"background: {self._color}; border-radius: 8px; border: 1.5px solid #e5e7eb;")
        self._color_btn = QPushButton("Choisir la couleur…")
        self._color_btn.setObjectName("editBtn")
        self._color_btn.setFixedHeight(38)
        self._color_btn.clicked.connect(self._pick_color)
        color_row.addWidget(self._color_preview)
        color_row.addWidget(self._color_btn)
        color_row.addStretch()

        color_widget = QWidget()
        color_widget.setLayout(color_row)
        form.addRow("Couleur", color_widget)

        layout.addLayout(form)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #dc2626; font-size: 12px; background: transparent; border: none;")
        self._error_label.setWordWrap(True)
        layout.addWidget(self._error_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Enregistrer")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        layout.addWidget(buttons)

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._color), self, "Choisir une couleur")
        if color.isValid():
            self._color = color.name()
            self._color_preview.setStyleSheet(f"background: {self._color}; border-radius: 8px; border: 1.5px solid #e5e7eb;")

    def _populate(self, emission) -> None:
        self._title_input.setText(emission.title)
        self._desc_input.setPlainText(emission.description or "")
        self._start_input.setDateTime(QDateTime(
            emission.start_dt.year, emission.start_dt.month, emission.start_dt.day,
            emission.start_dt.hour, emission.start_dt.minute,
        ))
        self._end_input.setDateTime(QDateTime(
            emission.end_dt.year, emission.end_dt.month, emission.end_dt.day,
            emission.end_dt.hour, emission.end_dt.minute,
        ))
        self._color = emission.color
        self._color_preview.setStyleSheet(f"background: {self._color}; border-radius: 8px; border: 1.5px solid #e5e7eb;")

    def _validate_and_accept(self) -> None:
        self._error_label.setText("")
        if not self._title_input.text().strip():
            self._error_label.setText("Le titre est obligatoire.")
            return
        start = self._start_input.dateTime().toPython()
        end = self._end_input.dateTime().toPython()
        if end <= start:
            self._error_label.setText("La fin doit être après le début.")
            return
        self.accept()

    def get_data(self) -> dict[str, Any]:
        start_qt = self._start_input.dateTime().toPython()
        end_qt = self._end_input.dateTime().toPython()
        return {
            "title": self._title_input.text().strip(),
            "description": self._desc_input.toPlainText().strip() or None,
            "start_dt": datetime(start_qt.year, start_qt.month, start_qt.day, start_qt.hour, start_qt.minute),
            "end_dt": datetime(end_qt.year, end_qt.month, end_qt.day, end_qt.hour, end_qt.minute),
            "color": self._color,
        }
