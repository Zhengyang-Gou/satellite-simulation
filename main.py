import sys
import os
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow


def configure_linux_display_backend() -> None:
    if not sys.platform.startswith("linux"):
        return

    if os.environ.get("XDG_SESSION_TYPE", "").lower() != "wayland":
        return

    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
    os.environ.setdefault("GDK_BACKEND", "x11")


if __name__ == "__main__":
    configure_linux_display_backend()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
