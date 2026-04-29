from __future__ import annotations
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import pyqtgraph as pg
from src.controllers.emission_controller import EmissionController


def _stat_card(number: str, label: str, color: str) -> QFrame:
    card = QFrame()
    card.setObjectName("statCard")
    card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(22, 18, 22, 18)
    layout.setSpacing(4)

    num = QLabel(number)
    num.setObjectName("statNum")
    f = QFont("Segoe UI", 28)
    f.setBold(True)
    num.setFont(f)
    num.setStyleSheet(f"color: {color}; border: none; background: transparent;")

    lbl = QLabel(label)
    lbl.setObjectName("statLabel")
    layout.addWidget(num)
    layout.addWidget(lbl)
    return card


class DashboardPage(QWidget):
    def __init__(self, emission_ctrl: EmissionController) -> None:
        super().__init__()
        self._ctrl = emission_ctrl
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 32)
        layout.setSpacing(20)

        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        week_end = today_start + timedelta(days=7)

        try:
            today_emissions = self._ctrl.list_all(from_dt=today_start, to_dt=today_end)
            week_emissions = self._ctrl.list_all(from_dt=today_start, to_dt=week_end)
        except Exception:
            today_emissions = []
            week_emissions = []

        # Stat cards
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)
        stats_row.addWidget(_stat_card(str(len(today_emissions)), "Émissions aujourd'hui", "#6B2EA6"))
        stats_row.addWidget(_stat_card(str(len(week_emissions)), "Cette semaine", "#AF6F56"))
        total = sum(len(e.podcasts) for e in week_emissions)
        stats_row.addWidget(_stat_card(str(total), "Podcasts liés", "#059669"))
        layout.addLayout(stats_row)

        # Chart
        chart_lbl = QLabel("Activité de la semaine")
        chart_lbl.setObjectName("sectionTitle")
        layout.addWidget(chart_lbl)
        layout.addWidget(self._build_week_chart(today_start, week_emissions))

        # Prochaines émissions
        upcoming_lbl = QLabel("Prochaines émissions — 7 jours")
        upcoming_lbl.setObjectName("sectionTitle")
        layout.addWidget(upcoming_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        cl = QVBoxLayout(container)
        cl.setSpacing(8)
        cl.setContentsMargins(0, 0, 0, 0)

        if not week_emissions:
            empty = QLabel("Aucune émission prévue cette semaine.")
            empty.setStyleSheet("color: #9ca3af; font-size: 13px; background: transparent; border: none;")
            cl.addWidget(empty)
        else:
            for em in week_emissions:
                card = QFrame()
                card.setObjectName("emissionCard")
                card.setStyleSheet(f"""
                    QFrame#emissionCard {{
                        background: white; border-radius: 10px;
                        border-left: 4px solid {em.color};
                        border-top: 1px solid #e5e7eb;
                        border-right: 1px solid #e5e7eb;
                        border-bottom: 1px solid #e5e7eb;
                    }}
                """)
                row = QHBoxLayout(card)
                row.setContentsMargins(16, 10, 16, 10)

                title = QLabel(em.title)
                title.setStyleSheet("font-weight: 700; font-size: 13px; border: none; background: transparent;")

                meta = QLabel(em.start_dt.strftime("%d/%m à %H:%M"))
                meta.setStyleSheet("color: #6b7280; font-size: 12px; border: none; background: transparent;")

                statut = QLabel(em.statut_technique.upper())
                statut.setStyleSheet("""
                    background: #f3ecfa; color: #6B2EA6; border-radius: 9999px;
                    padding: 2px 10px; font-size: 10px; font-weight: 700; border: none;
                """)

                row.addWidget(title)
                row.addStretch()
                row.addWidget(statut)
                row.addSpacing(12)
                row.addWidget(meta)
                cl.addWidget(card)

        cl.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

    def _build_week_chart(self, week_start: datetime, emissions: list) -> pg.PlotWidget:
        day_labels = []
        day_counts = [0] * 7
        for i in range(7):
            day = week_start + timedelta(days=i)
            day_labels.append(day.strftime("%a %d"))
            day_counts[i] = sum(1 for e in emissions if e.start_dt.date() == day.date())

        chart = pg.PlotWidget()
        chart.setBackground("white")
        chart.setMaximumHeight(160)
        chart.showGrid(x=False, y=True, alpha=0.2)
        chart.setLabel("left", "Émissions")
        chart.getAxis("bottom").setTicks([list(enumerate(day_labels))])
        chart.setYRange(0, max(max(day_counts) + 1, 3))
        chart.getAxis("left").setTextPen("#6b7280")
        chart.getAxis("bottom").setTextPen("#6b7280")

        bar = pg.BarGraphItem(x=list(range(7)), height=day_counts, width=0.6, brush="#6B2EA6")
        chart.addItem(bar)
        chart.setMouseEnabled(x=False, y=False)
        chart.setStyleSheet("border-radius: 10px; border: 1px solid #e5e7eb;")
        return chart
