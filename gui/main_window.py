from PyQt5.QtWidgets import QMainWindow, QStackedWidget
from PyQt5.QtCore import Qt

from gui.splash import SplashPage
from gui.tutorial import TutorialPage
from gui.home import HomePage


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        # ---------------------------
        # Window Settings
        # ---------------------------
        self.setWindowTitle("GestureBoard")

        # Fullscreen
        self.showFullScreen()

        # Prevent white background
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(True)

        # Global Application Style
        self.setStyleSheet("""
            QMainWindow{
                background-color:#111827;
            }

            QStackedWidget{
                background-color:#111827;
            }
        """)

        # ---------------------------
        # Stacked Widget
        # ---------------------------
        self.stack = QStackedWidget()

        self.stack.setObjectName("MainStack")
        self.setCentralWidget(self.stack)

        # ---------------------------
        # Pages
        # ---------------------------
        self.splash = SplashPage(self)
        self.tutorial = TutorialPage(self)
        self.home = HomePage(self)

        # Add pages
        self.stack.addWidget(self.splash)
        self.stack.addWidget(self.tutorial)
        self.stack.addWidget(self.home)

        # Show Splash First
        self.stack.setCurrentWidget(self.splash)

    # ======================================================
    # Navigation Functions
    # ======================================================

    def showSplash(self):
        self.stack.setCurrentWidget(self.splash)

    def showTutorial(self):
        self.stack.setCurrentWidget(self.tutorial)

    def showHome(self):
        self.stack.setCurrentWidget(self.home)