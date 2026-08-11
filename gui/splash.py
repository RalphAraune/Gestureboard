from pathlib import Path

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap


class SplashPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(True)

        # Save the MainWindow reference
        self.parent_window = parent

        # self.setWindowFlag(Qt.FramelessWindowHint)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(40, 40, 40, 40)

        # -----------------------
        # Logo
        # -----------------------

        self.logo = QLabel()

        logo_path = Path(__file__).resolve().parent.parent / "assets" / "logo" / "logo.jpg"
        pixmap = QPixmap(str(logo_path))

        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                240,
                240,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.logo.setPixmap(pixmap)

        self.logo.setAlignment(Qt.AlignCenter)

        # The splash is intentionally logo-only.
        layout.addStretch()
        layout.addWidget(self.logo)
        layout.addStretch()

        self.setLayout(layout)

        # -----------------------
        # Style
        # -----------------------

        self.setStyleSheet("""
        QWidget{
            background-color:#071426;
        }

        QLabel{
            background:transparent;
            color:white;
        }
        """)

        # Splash duration
        QTimer.singleShot(5000, self.next_page)

    # -----------------------
    # Next Page
    # -----------------------

    def next_page(self):

        if self.parent_window:
            self.parent_window.stack.setCurrentWidget(
                self.parent_window.tutorial
            )
