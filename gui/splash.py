from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap


class SplashPage(QWidget):
    def __init__(self, parent=None):
        super().__init__()

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(True)

        # Save the MainWindow reference
        self.parent_window = parent

        self.setWindowFlag(Qt.FramelessWindowHint)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        # -----------------------
        # Logo
        # -----------------------

        self.logo = QLabel()

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
        # Loading
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
        # Style
        # -----------------------

        self.setStyleSheet("""
        QWidget{
            background-color:#111827;
        }

        QLabel{
            background:transparent;
            color:white;
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

        # Splash duration
        QTimer.singleShot(3000, self.next_page)

    # -----------------------
    # Next Page
    # -----------------------

    def next_page(self):

        if self.parent_window:
            self.parent_window.stack.setCurrentWidget(
                self.parent_window.tutorial
            )