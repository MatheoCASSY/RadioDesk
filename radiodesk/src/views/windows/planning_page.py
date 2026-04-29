from __future__ import annotations
import calendar as cal_module
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QAbstractItemView, QFileDialog, QComboBox, QStackedWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from src.controllers.emission_controller import EmissionController
from src.auth.auth_service import AuthService
from src.models.user import Role
from src.views.dialogs.emission_dialog import EmissionDialog

HOURS_START = 6
HOURS_END = 23
DAYS_FR = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
MONTHS_FR = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]


class PlanningPage(QWidget):
    def __init__(self, ctrl: EmissionController, auth: AuthService) -> None:
        super().__init__()
        self._ctrl = ctrl
        self._auth = auth
        self._view = "liste"
        self._ref_date = datetime.now()
        self._setup_ui()
        self._switch_view("liste")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        layout.addLayout(self._build_header())
        layout.addLayout(self._build_nav_bar())

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_list_view())
        self._stack.addWidget(self._build_week_view())
        self._stack.addWidget(self._build_month_view())
        layout.addWidget(self._stack)

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        title = QLabel("Planning des émissions")
        f = QFont()
        f.setPointSize(18)
        f.setBold(True)
        title.setFont(f)
        header.addWidget(title)
        header.addStretch()

        cur = self._auth.require_session()

        export_btn = QPushButton("Exporter PDF")
        export_btn.setObjectName("accentBtn")
        export_btn.setStyleSheet("")
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.clicked.connect(self._on_export_pdf)
        header.addWidget(export_btn)

        if cur.role in (Role.ADMIN, Role.ANIMATEUR):
            add_btn = QPushButton("+ Nouvelle émission")
            add_btn.setObjectName("primaryBtn")
            add_btn.setStyleSheet("")
            add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            add_btn.clicked.connect(self._on_add)
            header.addWidget(add_btn)

        return header

    def _build_nav_bar(self) -> QHBoxLayout:
        nav = QHBoxLayout()

        self._btn_prev = QPushButton("◀ Précédent")
        self._btn_prev.clicked.connect(self._on_prev)
        self._btn_today = QPushButton("Aujourd'hui")
        self._btn_today.clicked.connect(self._on_today)
        self._btn_next = QPushButton("Suivant ▶")
        self._btn_next.clicked.connect(self._on_next)

        nav.addWidget(self._btn_prev)
        nav.addWidget(self._btn_today)
        nav.addWidget(self._btn_next)
        nav.addStretch()

        self._period_label = QLabel("")
        self._period_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = QFont()
        f.setPointSize(13)
        f.setBold(True)
        self._period_label.setFont(f)
        nav.addWidget(self._period_label)
        nav.addStretch()

        # View switcher buttons
        _btn_style = """
            QPushButton { border: 1px solid #d1d5db; border-radius: 6px; padding: 4px 14px; font-size: 13px; }
            QPushButton:checked { background: #6B2EA6; color: white; border-color: #6B2EA6; }
            QPushButton:hover:!checked { background: #f3ecfa; }
        """
        for label, view in [("Liste", "liste"), ("Semaine", "semaine"), ("Mois", "mois")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(_btn_style)
            btn.clicked.connect(lambda checked, v=view: self._switch_view(v))
            setattr(self, f"_viewbtn_{view}", btn)
            nav.addWidget(btn)

        return nav

    _TABLE_STYLE = """
        QTableWidget { border: 1px solid #e5e7eb; border-radius: 8px; background: white; gridline-color: #f3f4f6; }
        QHeaderView::section { background: #f3ecfa; font-weight: 600; font-size: 12px; padding: 8px;
                                border: none; border-bottom: 1px solid #e5e7eb; color: #5a2490; }
        QTableWidget::item { padding: 8px; font-size: 13px; }
    """

    def _build_list_view(self) -> QTableWidget:
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(["Titre", "Début", "Fin", "Animateur", "Statut technique", "Actions"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 5):
            self._table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(5, 200)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(self._TABLE_STYLE)
        return self._table

    def _build_week_view(self) -> QTableWidget:
        n_rows = HOURS_END - HOURS_START
        self._week_table = QTableWidget(n_rows, 7)
        self._week_table.setVerticalHeaderLabels([f"{h:02d}h" for h in range(HOURS_START, HOURS_END)])
        self._week_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._week_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._week_table.verticalHeader().setDefaultSectionSize(54)
        self._week_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._week_table.setStyleSheet(self._TABLE_STYLE)
        return self._week_table

    def _build_month_view(self) -> QTableWidget:
        self._month_table = QTableWidget(6, 7)
        self._month_table.setHorizontalHeaderLabels(DAYS_FR)
        self._month_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._month_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._month_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._month_table.verticalHeader().setVisible(False)
        self._month_table.verticalHeader().setDefaultSectionSize(100)
        self._month_table.setStyleSheet(self._TABLE_STYLE)
        return self._month_table

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _switch_view(self, view: str) -> None:
        self._view = view
        for v in ("liste", "semaine", "mois"):
            btn = getattr(self, f"_viewbtn_{v}", None)
            if btn:
                btn.setChecked(v == view)

        nav_visible = view in ("semaine", "mois")
        self._btn_prev.setVisible(nav_visible)
        self._btn_today.setVisible(nav_visible)
        self._btn_next.setVisible(nav_visible)
        self._period_label.setVisible(nav_visible)

        page = {"liste": 0, "semaine": 1, "mois": 2}[view]
        self._stack.setCurrentIndex(page)
        self._load()

    def _on_prev(self) -> None:
        if self._view == "semaine":
            self._ref_date -= timedelta(weeks=1)
        else:
            m = self._ref_date.month - 1 or 12
            y = self._ref_date.year - (1 if self._ref_date.month == 1 else 0)
            self._ref_date = self._ref_date.replace(year=y, month=m, day=1)
        self._load()

    def _on_today(self) -> None:
        self._ref_date = datetime.now()
        self._load()

    def _on_next(self) -> None:
        if self._view == "semaine":
            self._ref_date += timedelta(weeks=1)
        else:
            m = self._ref_date.month % 12 + 1
            y = self._ref_date.year + (1 if self._ref_date.month == 12 else 0)
            self._ref_date = self._ref_date.replace(year=y, month=m, day=1)
        self._load()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._view == "liste":
            self._load_table()
        elif self._view == "semaine":
            self._load_week()
        else:
            self._load_month()

    def _get_emissions(self) -> list:
        try:
            return self._ctrl.list_all()
        except Exception:
            return []

    def _load_table(self) -> None:
        emissions = self._get_emissions()
        self._table.setRowCount(0)
        cur = self._auth.require_session()
        for em in emissions:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(em.title))
            self._table.setItem(row, 1, QTableWidgetItem(em.start_dt.strftime("%d/%m/%Y %H:%M")))
            self._table.setItem(row, 2, QTableWidgetItem(em.end_dt.strftime("%d/%m/%Y %H:%M")))
            user_name = em.user.username if em.user else "—"
            self._table.setItem(row, 3, QTableWidgetItem(user_name))
            self._table.setItem(row, 4, QTableWidgetItem(em.statut_technique))
            color_item = self._table.item(row, 0)
            if color_item:
                color_item.setForeground(QColor(em.color))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(6)

            if cur.role in (Role.ADMIN, Role.ANIMATEUR, Role.TECHNICIEN):
                statut_combo = QComboBox()
                statut_combo.addItems(["normal", "en_test", "probleme", "ok"])
                idx = statut_combo.findText(em.statut_technique)
                if idx >= 0:
                    statut_combo.setCurrentIndex(idx)
                statut_combo.setStyleSheet("QComboBox { font-size: 11px; padding: 2px 4px; }")
                statut_combo.currentTextChanged.connect(lambda val, e=em: self._on_statut_change(e, val))
                btn_layout.addWidget(statut_combo)

            can_edit = cur.role == Role.ADMIN or em.user_id == cur.user_id
            if can_edit:
                edit_btn = QPushButton("Modifier")
                edit_btn.setObjectName("editBtn")
                edit_btn.setStyleSheet("")
                edit_btn.clicked.connect(lambda _, e=em: self._on_edit(e))
                del_btn = QPushButton("Supprimer")
                del_btn.setObjectName("dangerBtn")
                del_btn.setStyleSheet("")
                del_btn.clicked.connect(lambda _, e=em: self._on_delete(e))
                btn_layout.addWidget(edit_btn)
                btn_layout.addWidget(del_btn)

            if btn_layout.count() > 0:
                self._table.setCellWidget(row, 5, btn_widget)

    def _load_week(self) -> None:
        ref = self._ref_date
        week_start = (ref - timedelta(days=ref.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)

        # Update column headers with day + date
        self._week_table.setHorizontalHeaderLabels([
            f"{DAYS_FR[i]}\n{(week_start + timedelta(days=i)).strftime('%d/%m')}"
            for i in range(7)
        ])
        self._period_label.setText(
            f"Semaine du {week_start.strftime('%d/%m/%Y')} au {(week_end - timedelta(days=1)).strftime('%d/%m/%Y')}"
        )

        # Clear grid (remove spans first, then items)
        self._week_table.clearSpans()
        n_rows = HOURS_END - HOURS_START
        for r in range(n_rows):
            for c in range(7):
                item = QTableWidgetItem("")
                item.setBackground(QColor("#ffffff"))
                self._week_table.setItem(r, c, item)

        emissions = self._get_emissions()
        for em in emissions:
            if em.end_dt <= week_start or em.start_dt >= week_end:
                continue
            col = em.start_dt.weekday()
            if not (0 <= col < 7):
                continue
            start_row = max(em.start_dt.hour - HOURS_START, 0)
            end_row = min(em.end_dt.hour - HOURS_START, n_rows - 1)
            if start_row >= n_rows:
                continue
            span = max(end_row - start_row, 1)

            duration = f"{em.start_dt.strftime('%H:%M')}–{em.end_dt.strftime('%H:%M')}"
            item = QTableWidgetItem(f"{em.title}\n{duration}")
            item.setForeground(QColor("white"))
            item.setBackground(QColor(em.color))
            item.setToolTip(f"{em.title}\n{em.user.username if em.user else '—'}\n{duration}")
            self._week_table.setItem(start_row, col, item)
            if span > 1:
                self._week_table.setSpan(start_row, col, span, 1)

    def _load_month(self) -> None:
        year, month = self._ref_date.year, self._ref_date.month
        self._period_label.setText(f"{MONTHS_FR[month - 1]} {year}")

        first_wd = cal_module.monthrange(year, month)[0]
        days_in_month = cal_module.monthrange(year, month)[1]

        self._month_table.clearContents()
        emissions = self._get_emissions()
        today = datetime.now().date()

        day = 1
        for row in range(6):
            for col in range(7):
                if row == 0 and col < first_wd:
                    # Empty cell before month starts
                    cell = QWidget()
                    cell.setStyleSheet("background: #f9fafb;")
                    self._month_table.setCellWidget(row, col, cell)
                    continue
                if day > days_in_month:
                    cell = QWidget()
                    cell.setStyleSheet("background: #f9fafb;")
                    self._month_table.setCellWidget(row, col, cell)
                    continue

                cell_date = datetime(year, month, day).date()
                cell = QWidget()
                cell_layout = QVBoxLayout(cell)
                cell_layout.setContentsMargins(4, 4, 4, 2)
                cell_layout.setSpacing(2)
                cell_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

                day_label = QLabel(str(day))
                if cell_date == today:
                    day_label.setStyleSheet(
                        "font-weight: bold; color: white; background: #6B2EA6;"
                        " border-radius: 10px; padding: 1px 6px; font-size: 11px;"
                    )
                elif col >= 5:
                    day_label.setStyleSheet("font-size: 11px; color: #9ca3af; font-weight: bold;")
                else:
                    day_label.setStyleSheet("font-size: 11px; color: #374151; font-weight: bold;")
                cell_layout.addWidget(day_label)

                for em in emissions:
                    if em.start_dt.date() == cell_date:
                        em_label = QLabel(f"  {em.start_dt.strftime('%H:%M')} {em.title}")
                        em_label.setStyleSheet(
                            f"background: {em.color}; color: white; border-radius: 3px;"
                            f" font-size: 9px; padding: 1px 3px;"
                        )
                        em_label.setToolTip(
                            f"{em.title}\n{em.user.username if em.user else '—'}\n"
                            f"{em.start_dt.strftime('%H:%M')}–{em.end_dt.strftime('%H:%M')}"
                        )
                        cell_layout.addWidget(em_label)

                self._month_table.setCellWidget(row, col, cell)
                day += 1

    # ------------------------------------------------------------------
    # Actions (statut, CRUD, PDF)
    # ------------------------------------------------------------------

    def _on_statut_change(self, emission, statut: str) -> None:
        try:
            self._ctrl.update_statut_technique(emission.id, statut)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def _on_add(self) -> None:
        dlg = EmissionDialog(parent=self)
        if dlg.exec():
            data = dlg.get_data()
            try:
                self._ctrl.create(**data)
                self._load()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def _on_edit(self, emission) -> None:
        dlg = EmissionDialog(emission=emission, parent=self)
        if dlg.exec():
            data = dlg.get_data()
            try:
                self._ctrl.update(emission.id, **data)
                self._load()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def _on_delete(self, emission) -> None:
        reply = QMessageBox.question(
            self, "Confirmation",
            f"Supprimer l'émission « {emission.title} » ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._ctrl.delete(emission.id)
                self._load()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def _on_export_pdf(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Exporter le planning en PDF", "planning.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors

            doc = SimpleDocTemplate(path, pagesize=A4)
            styles = getSampleStyleSheet()
            elements = []

            elements.append(Paragraph("Planning des émissions — RadioDesk", styles["Title"]))
            elements.append(Spacer(1, 12))

            emissions = self._get_emissions()
            data = [["Titre", "Début", "Fin", "Animateur", "Statut"]]
            for em in emissions:
                data.append([
                    em.title,
                    em.start_dt.strftime("%d/%m/%Y %H:%M"),
                    em.end_dt.strftime("%d/%m/%Y %H:%M"),
                    em.user.username if em.user else "—",
                    em.statut_technique,
                ])

            table = Table(data, colWidths=[160, 110, 110, 90, 80])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6B2EA6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3ecfa")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(table)
            doc.build(elements)
            QMessageBox.information(self, "Export réussi", f"Planning exporté dans :\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur export PDF", str(e))
