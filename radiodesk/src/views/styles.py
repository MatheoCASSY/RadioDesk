STYLESHEET = """
/* ================================================
   RadioDesk — Admin Panel Theme
   FluffRadio Design System
   ================================================ */

/* Base */
QWidget {
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 13px;
    color: #222222;
    background: #F0E5C9;
}

QMainWindow { background: #F0E5C9; }
QDialog     { background: white; }

/* ── Sidebar ──────────────────────────────────── */
QFrame#sidebar {
    background: #0b1220;
    border: none;
}

QLabel#logoLabel {
    color: #AF6F56;
    font-size: 18px;
    font-weight: 700;
    background: transparent;
    border: none;
}

QLabel#logoSub {
    color: #475569;
    font-size: 10px;
    background: transparent;
    border: none;
    letter-spacing: 1px;
}

QLabel#sideSection {
    color: #475569;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    background: transparent;
    border: none;
    padding: 0 4px;
}

QPushButton#navBtn {
    background: transparent;
    color: #94a3b8;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}
QPushButton#navBtn:hover   { background: #1a1f2e; color: #f1f5f9; }
QPushButton#navBtn:checked { background: #6B2EA6; color: white; font-weight: 700; }

QFrame#sidebarDivider {
    background: #1e293b;
    border: none;
    max-height: 1px;
}

QLabel#sideUserName {
    color: #cbd5e1;
    font-size: 13px;
    font-weight: 600;
    background: transparent;
    border: none;
}
QLabel#sideUserRole {
    color: #475569;
    font-size: 11px;
    background: transparent;
    border: none;
}

QPushButton#logoutBtn {
    background: transparent;
    color: #64748b;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
    text-align: left;
}
QPushButton#logoutBtn:hover { background: #1a1f2e; color: #f1f5f9; border-color: #334155; }

/* ── Top bar ──────────────────────────────────── */
QFrame#topbar {
    background: white;
    border: none;
    border-bottom: 1px solid #e5e7eb;
}

QLabel#pageTitle {
    font-size: 18px;
    font-weight: 700;
    color: #222222;
    background: transparent;
    border: none;
}

QLabel#topbarUser {
    font-size: 12px;
    color: #6b7280;
    background: transparent;
    border: none;
}

QLabel#roleBadge {
    background: #f3ecfa;
    color: #6B2EA6;
    border-radius: 9999px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 700;
    border: none;
}

/* ── Primary buttons ──────────────────────────── */
QPushButton#primaryBtn {
    background: #6B2EA6;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 13px;
}
QPushButton#primaryBtn:hover    { background: #5a2490; }
QPushButton#primaryBtn:disabled { background: #c4b5d8; }

/* ── Accent buttons ───────────────────────────── */
QPushButton#accentBtn {
    background: #AF6F56;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 13px;
}
QPushButton#accentBtn:hover { background: #9a5f47; }

/* ── Edit / Danger inline buttons ────────────── */
QPushButton#editBtn {
    background: #f3ecfa;
    color: #6B2EA6;
    border: 1px solid #d8b4fe;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
}
QPushButton#editBtn:hover { background: #e9d5ff; }

QPushButton#dangerBtn {
    background: #fef2f2;
    color: #dc2626;
    border: 1px solid #fecaca;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
}
QPushButton#dangerBtn:hover { background: #fee2e2; }

QPushButton#playBtn {
    background: #6B2EA6;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#playBtn:hover    { background: #5a2490; }
QPushButton#playBtn:disabled { background: #c4b5d8; color: #f3ecfa; }

QPushButton#stopBtn {
    background: white;
    color: #374151;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 12px;
}
QPushButton#stopBtn:hover    { background: #f9fafb; }
QPushButton#stopBtn:disabled { color: #9ca3af; }

/* ── Stat cards ───────────────────────────────── */
QFrame#statCard {
    background: white;
    border-radius: 14px;
    border: 1px solid #ede9fe;
}

QLabel#statNum {
    font-size: 34px;
    font-weight: 800;
    background: transparent;
    border: none;
}

QLabel#statLabel {
    color: #6b7280;
    font-size: 12px;
    background: transparent;
    border: none;
}

/* ── Section titles ───────────────────────────── */
QLabel#sectionTitle {
    font-size: 15px;
    font-weight: 700;
    color: #222222;
    background: transparent;
    border: none;
}

/* ── Emission cards ───────────────────────────── */
QFrame#emissionCard {
    background: white;
    border-radius: 10px;
    border: 1px solid #e5e7eb;
}

/* ── Tables ───────────────────────────────────── */
QTableWidget {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    gridline-color: #f3f4f6;
    outline: none;
    selection-background-color: #f3ecfa;
}
QTableWidget::item {
    padding: 10px 14px;
    border: none;
    color: #222222;
}
QTableWidget::item:selected { background: #f3ecfa; color: #6B2EA6; }
QTableWidget::item:hover    { background: #faf5ff; }
QHeaderView::section {
    background: #6B2EA6;
    color: white;
    font-weight: 700;
    font-size: 12px;
    padding: 10px 14px;
    border: none;
}

/* ── List widget ──────────────────────────────── */
QListWidget {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    outline: none;
}
QListWidget::item {
    padding: 10px 14px;
    border-bottom: 1px solid #f3f4f6;
}
QListWidget::item:last { border-bottom: none; }
QListWidget::item:selected { background: #f3ecfa; color: #6B2EA6; }
QListWidget::item:hover    { background: #faf5ff; }

/* ── Inputs ───────────────────────────────────── */
QLineEdit, QDateTimeEdit {
    background: white;
    border: 1.5px solid #e5e7eb;
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 13px;
    color: #222222;
    selection-background-color: #f3ecfa;
    selection-color: #6B2EA6;
}
QLineEdit:focus, QDateTimeEdit:focus { border-color: #6B2EA6; }
QLineEdit:disabled { background: #f9fafb; color: #9ca3af; }

QTextEdit {
    background: white;
    border: 1.5px solid #e5e7eb;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: #f3ecfa;
    selection-color: #6B2EA6;
}
QTextEdit:focus { border-color: #6B2EA6; }

QComboBox {
    background: white;
    border: 1.5px solid #e5e7eb;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 13px;
    color: #222222;
}
QComboBox:focus { border-color: #6B2EA6; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    selection-background-color: #f3ecfa;
    selection-color: #6B2EA6;
    outline: none;
}

/* ── Sliders ──────────────────────────────────── */
QSlider::groove:horizontal {
    height: 4px;
    background: #e5e7eb;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #6B2EA6;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::sub-page:horizontal {
    background: #6B2EA6;
    border-radius: 2px;
}

/* ── Scroll bars ──────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #c4b5d8;
    border-radius: 3px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #6B2EA6; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: transparent;
    height: 6px;
}
QScrollBar::handle:horizontal {
    background: #c4b5d8;
    border-radius: 3px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Dialogs ──────────────────────────────────── */
QDialogButtonBox QPushButton {
    background: #6B2EA6;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 7px 20px;
    font-weight: 600;
    min-width: 80px;
}
QDialogButtonBox QPushButton:hover { background: #5a2490; }
QDialogButtonBox QPushButton[text="Annuler"] {
    background: white;
    color: #374151;
    border: 1px solid #e5e7eb;
}
QDialogButtonBox QPushButton[text="Annuler"]:hover { background: #f9fafb; }

/* ── Message boxes ────────────────────────────── */
QMessageBox { background: white; }
QMessageBox QPushButton {
    background: #6B2EA6;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 7px 20px;
    font-weight: 600;
    min-width: 80px;
}
QMessageBox QPushButton:hover { background: #5a2490; }

/* ── Tooltips ─────────────────────────────────── */
QToolTip {
    background: #0b1220;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 4px 10px;
}

/* ── Scroll area ──────────────────────────────── */
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }

/* ── Progress bar ─────────────────────────────── */
QProgressBar {
    background: #e5e7eb;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    border: none;
}
QProgressBar::chunk {
    background: #6B2EA6;
    border-radius: 4px;
}

/* ── Calendar popup ───────────────────────────── */
QCalendarWidget QToolButton {
    background: #6B2EA6;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 4px;
}
QCalendarWidget QAbstractItemView {
    selection-background-color: #6B2EA6;
    selection-color: white;
}
"""
