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
from gui.camera_setup import CameraSetupPage
from gui.dashboard import DashboardPage


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        # ======================================================
        # Window Settings
        # ======================================================

        self.setWindowTitle("GestureBoard")
        self.active_camera_index = None
        self.active_camera_name = "No camera selected"

        # Remove the default Windows title bar
        self.setWindowFlags(Qt.FramelessWindowHint)

        # Dark background
        self.setStyleSheet("""
            QMainWindow{
                background-color:#071426;
            }

            QWidget{
                background-color:#071426;
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
        self.mainLayout.setStretch(1, 1)

        # ======================================================
        # Pages
        # ======================================================

        self.splash = SplashPage(self)

        self.tutorial = TutorialPage(self)

        self.home = HomePage(self)
        self.camera_setup = CameraSetupPage(self)
        self.dashboard = DashboardPage(self)

        # ======================================================
        # Add Pages
        # ======================================================

        self.stack.addWidget(self.splash)

        self.stack.addWidget(self.tutorial)

        self.stack.addWidget(self.home)
        self.stack.addWidget(self.camera_setup)
        self.stack.addWidget(self.dashboard)

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

    def showCameraSetup(self):
        self.stack.setCurrentWidget(self.camera_setup)

    def showDashboard(self):
        self.dashboard.updateCameraName(self.active_camera_name)
        self.stack.setCurrentWidget(self.dashboard)

    def setActiveCamera(self, index, name):
        self.active_camera_index = index
        self.active_camera_name = name
        self.home.updateCameraName(name)
