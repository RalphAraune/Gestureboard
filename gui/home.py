from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout
)
from PyQt5.QtCore import Qt


class HomePage(QWidget):

    def __init__(self, parent=None):
        super().__init__()

        self.parent_window = parent

        # Let MainWindow control the window
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(False)

        # ----------------------------
        # Style
        # ----------------------------

        self.setStyleSheet("""
            QWidget{
                background: transparent;
            }

            QLabel{
                background: transparent;
                color: white;
            }

            QPushButton{
                background-color:#2563EB;
                color:white;
                border:none;
                border-radius:10px;
                padding:12px;
                font-size:15px;
                min-width:220px;
            }

            QPushButton:hover{
                background-color:#3B82F6;
            }

            QPushButton:pressed{
                background-color:#1D4ED8;
            }
        """)

        # ----------------------------
        # Layout
        # ----------------------------

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)

        title = QLabel("GestureBoard")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size:42px;
            font-weight:bold;
            color:white;
        """)

        subtitle = QLabel(
            "Gesture-Controlled Presentation System"
        )

        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            font-size:18px;
            color:#9CA3AF;
        """)

        self.startButton = QPushButton("Start Camera")
        self.savedButton = QPushButton("Saved Files")
        self.settingsButton = QPushButton("Settings")
        self.exitButton = QPushButton("Exit")

        # ----------------------------
        # Button Connections
        # ----------------------------

        self.startButton.clicked.connect(self.startCamera)
        self.exitButton.clicked.connect(self.closeApplication)

        # ----------------------------
        # Add Widgets
        # ----------------------------

        layout.addStretch()

        layout.addWidget(title)
        layout.addWidget(subtitle)

        layout.addSpacing(40)

        layout.addWidget(self.startButton)
        layout.addWidget(self.savedButton)
        layout.addWidget(self.settingsButton)
        layout.addWidget(self.exitButton)

        layout.addStretch()

        self.setLayout(layout)

    # =========================================================
    # Start Camera
    # =========================================================

    def startCamera(self):
        print("Start Camera Clicked")

        # Later:
        # self.parent_window.showCameraSetup()

    # =========================================================
    # Exit Application
    # =========================================================

    def closeApplication(self):

        if self.parent_window:
            self.parent_window.close()