from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QStackedWidget
)
from PyQt5.QtCore import Qt

from widgets.titlebar import TitleBar

from gui.splash import SplashPage
from gui.tutorial import TutorialPage
from gui.home import HomePage


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        # ======================================================
        # Window Settings
        # ======================================================

        self.setWindowTitle("GestureBoard")

        # Remove the default Windows title bar
        self.setWindowFlags(Qt.FramelessWindowHint)

        # Start maximized (recommended)
        self.showMaximized()

        # Dark background
        self.setStyleSheet("""
            QMainWindow{
                background-color:#111827;
            }

            QWidget{
                background-color:#111827;
                color:white;
            }
        """)

        # ======================================================
        # Main Container
        # ======================================================

        self.central = QWidget()

        self.setCentralWidget(self.central)

        self.mainLayout = QVBoxLayout()

        self.mainLayout.setContentsMargins(0, 0, 0, 0)

        self.mainLayout.setSpacing(0)

        self.central.setLayout(self.mainLayout)

        # ======================================================
        # Custom Title Bar
        # ======================================================

        self.titlebar = TitleBar(self)

        self.mainLayout.addWidget(self.titlebar)

        # ======================================================
        # Page Container
        # ======================================================

        self.stack = QStackedWidget()

        self.stack.setObjectName("MainStack")

        self.mainLayout.addWidget(self.stack)

        # ======================================================
        # Pages
        # ======================================================

        self.splash = SplashPage(self)

        self.tutorial = TutorialPage(self)

        self.home = HomePage(self)

        # ======================================================
        # Add Pages
        # ======================================================

        self.stack.addWidget(self.splash)

        self.stack.addWidget(self.tutorial)

        self.stack.addWidget(self.home)

        # ======================================================
        # First Page
        # ======================================================

        self.stack.setCurrentWidget(self.splash)

    # ======================================================
    # Navigation
    # ======================================================

    def showSplash(self):
        self.stack.setCurrentWidget(self.splash)

    def showTutorial(self):
        self.stack.setCurrentWidget(self.tutorial)

    def showHome(self):
        self.stack.setCurrentWidget(self.home)