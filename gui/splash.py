from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap

from gui.tutorial import TutorialScreen


class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("GestureBoard")
        self.setFixedSize(1000, 600)

        # -----------------------
        # Main Layout
        # -----------------------

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        # -----------------------
        # Logo
        # -----------------------

        self.logo = QLabel()

        # Change this path if your logo has another filename
        pixmap = QPixmap("assets/logo/logo.png")

        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                120,
                120,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.logo.setPixmap(pixmap)

        self.logo.setAlignment(Qt.AlignCenter)

        # -----------------------
        # Title
        # -----------------------

        self.title = QLabel("GestureBoard")
        self.title.setAlignment(Qt.AlignCenter)

        # -----------------------
        # Subtitle
        # -----------------------

        self.subtitle = QLabel(
            "Gesture-Controlled Presentation and Annotation System"
        )
        self.subtitle.setAlignment(Qt.AlignCenter)

        # -----------------------
        # Loading Text
        # -----------------------

        self.loading = QLabel("Loading...")
        self.loading.setAlignment(Qt.AlignCenter)

        # -----------------------
        # Footer
        # -----------------------

        self.footer = QLabel("Version 1.0")
        self.footer.setAlignment(Qt.AlignCenter)

        # -----------------------
        # Add Widgets
        # -----------------------

        layout.addStretch()

        layout.addWidget(self.logo)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addSpacing(20)
        layout.addWidget(self.loading)

        layout.addStretch()

        layout.addWidget(self.footer)

        self.setLayout(layout)

        # -----------------------
        # Styles
        # -----------------------

        self.setStyleSheet("""
            QWidget{
                background-color:#111827;
            }

            QLabel{
                color:white;
            }

            QLabel#title{
                font-size:42px;
                font-weight:bold;
            }
        """)

        self.title.setStyleSheet("""
            font-size:40px;
            font-weight:bold;
            color:white;
        """)

        self.subtitle.setStyleSheet("""
            font-size:18px;
            color:#9CA3AF;
        """)

        self.loading.setStyleSheet("""
            font-size:15px;
            color:#60A5FA;
        """)

        self.footer.setStyleSheet("""
            font-size:12px;
            color:#6B7280;
            margin-bottom:15px;
        """)

        # -----------------------
        # Open Tutorial after 3 seconds
        # -----------------------

        QTimer.singleShot(3000, self.openTutorial)

    # -----------------------
    # Open Tutorial
    # -----------------------

    def openTutorial(self):
        self.tutorial = TutorialScreen()
        self.tutorial.show()
        self.close()