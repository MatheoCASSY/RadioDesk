# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 6.x spec for RadioDesk
# Usage: pyinstaller setup/radiodesk.spec  (from the radiodesk/ directory)

import sys
import os
from pathlib import Path

ROOT = Path(SPECPATH).parent          # radiodesk/ root
_icon_path = os.path.join(SPECPATH, "RadioDesk.ico")
ICON = _icon_path if os.path.exists(_icon_path) else None

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[
        # PySide6 multimedia (audio player)
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        # Database
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.sql.default_comparator",
        # Auth
        "bcrypt",
        # Charts & PDF
        "pyqtgraph",
        "reportlab",
        "reportlab.graphics",
        "reportlab.platypus",
        # Requests (Cognito + API)
        "requests",
        "urllib3",
        "certifi",
        "charset_normalizer",
        # Other
        "alembic",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Dev tools — not needed at runtime
        "pytest", "pytest_qt", "mypy", "flake8", "pylint", "black",
        "IPython", "tkinter",
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="RadioDesk",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,               # UPX off — avoids AV false positives
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # No terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
    version_file=None,
)
