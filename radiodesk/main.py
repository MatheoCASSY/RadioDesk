import sys
from PySide6.QtWidgets import QApplication
from src.config.settings import Settings
from src.db.database import Database
from src.views.windows.login_window import LoginWindow
from src.views.styles import STYLESHEET


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("RadioDesk")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("RadioDesk")
    app.setStyleSheet(STYLESHEET)

    settings = Settings()
    db = Database(settings.db_path)
    db.init()

    window = LoginWindow(db=db, settings=settings)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
