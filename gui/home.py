from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget
from gui.camera_setup import CameraPickerDialog


class HomePage(QWidget):
    """Main landing page displayed after the tutorial."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setObjectName("homePage")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget#homePage { background: #F4F6FB; }
            QFrame#heroPanel {
                background: #FFFFFF; border: 1px solid #E4E8F2; border-radius: 20px;
            }
            QLabel { background: transparent; color: #1F2430; }
            QLabel#appMark {
                background: #3E7CF7; border-radius: 28px;
                color: white; font-size: 38px; font-weight: 700;
            }
            QLabel#appTitle { font-size: 30px; font-weight: 800; color: #1F2430; }
            QLabel#subtitle { color: #7B87A0; font-size: 13px; }
            QFrame#readyBadge { background: #EDF3FF; border: 1px solid #D7E5FF; border-radius: 15px; }
            QLabel#readyText { color: #2F9E62; font-size: 12px; }
            QPushButton {
                background: #FFFFFF; color: #5A6470; border: 1px solid #E4E8F2; border-radius: 8px;
                min-height: 34px; font-size: 12px;
            }
            QPushButton:hover { background: #F0F3FA; color: #1F2430; }
            QPushButton#startButton {
                background: #3E7CF7; color: white; border: none; border-radius: 10px;
                min-height: 44px; font-size: 14px; font-weight: 700;
            }
            QPushButton#startButton:hover { background: #5790FF; }
            QFrame#statusCard { background: #FFFFFF; border: 1px solid #E4E8F2; border-radius: 8px; }
            QLabel#statusCaption { color: #8A94A6; font-size: 11px; }
            QLabel#statusValue { color: #1F2430; font-size: 13px; font-weight: 600; }
            QLabel#footer { color: #A0AABC; font-size: 11px; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 12)
        root.addStretch()

        # Initialize camera_value attribute (used when camera is selected)
        self.camera_value = QLabel("Not Connected")
        self.camera_value.setObjectName("statusValue")

        hero = QFrame()
        hero.setObjectName("heroPanel")
        hero.setMinimumWidth(360)
        hero.setMaximumWidth(650)
        hero.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(40, 40, 40, 40)
        hero_layout.setSpacing(15)
        hero_layout.setAlignment(Qt.AlignCenter)

        mark = QLabel("G")
        mark.setObjectName("appMark")
        mark.setFixedSize(80, 80)
        mark.setAlignment(Qt.AlignCenter)
        mark.setStyleSheet("font-size: 48px;")
        title = QLabel("GestureBoard")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Gesture-Controlled Presentation & Annotation System")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignCenter)

        # Get Started button - prominent action
        self.getStartedButton = QPushButton("Get Started")
        self.getStartedButton.setObjectName("startButton")
        self.getStartedButton.setMinimumWidth(180)
        self.getStartedButton.setMinimumHeight(50)
        self.getStartedButton.setStyleSheet("""
            QPushButton#getStartedButton {
                background: #3E7CF7; color: white; border: none; border-radius: 10px;
                min-height: 44px; font-size: 16px; font-weight: 700;
                padding: 12px 24px;
            }
            QPushButton#getStartedButton:hover { background: #5790FF; }
        """)
        self.getStartedButton.clicked.connect(self.showTutorial)

        # Camera selection hint
        cameraHint = QLabel("• Click 'User Guide' to start or connect a camera •")
        cameraHint.setObjectName("muted")
        cameraHint.setAlignment(Qt.AlignCenter)
        cameraHint.setStyleSheet("font-size: 10px; color: #A0AABC; margin: 8px 0;")

        hero_layout.addWidget(mark, 0, Qt.AlignCenter)
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        hero_layout.addSpacing(15)
        hero_layout.addWidget(self.getStartedButton, 0, Qt.AlignCenter)
        hero_layout.addWidget(cameraHint)
        hero_layout.addStretch()

        root.addWidget(hero, 0, Qt.AlignCenter)
        root.addStretch()

        # Bottom controls: Settings, User Guide, Exit
        controls = QHBoxLayout()
        controls.setSpacing(20)
        controls.setAlignment(Qt.AlignCenter)
        self.settingsButton = QPushButton("Settings")
        self.guideButton = QPushButton("User Guide")
        self.exitButton = QPushButton("Exit")
        self.settingsButton.setMinimumWidth(100)
        self.guideButton.setMinimumWidth(100)
        self.exitButton.setMinimumWidth(100)
        self.guideButton.clicked.connect(self.showTutorial)
        self.exitButton.clicked.connect(self.closeApplication)
        controls.addWidget(self.settingsButton)
        controls.addWidget(self.guideButton)
        controls.addWidget(self.exitButton)

        root.addLayout(controls)
        root.addStretch()

        footer = QLabel("GestureBoard  •  Computer Vision Lab  •  2026")
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignCenter)
        root.addWidget(footer)

    def _status_cards(self):
        cards = QHBoxLayout()
        cards.setSpacing(10)
        for caption, value in (("Camera", "Not Connected"), ("Resolution", "1280×720"),
                               ("FPS", "—"), ("Mode", "Idle")):
            card = QFrame()
            card.setObjectName("statusCard")
            card.setMinimumSize(90, 50)
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            layout = QVBoxLayout(card)
            layout.setContentsMargins(10, 6, 10, 6)
            layout.setSpacing(1)
            caption_label = QLabel(caption)
            caption_label.setObjectName("statusCaption")
            value_label = QLabel(value)
            value_label.setObjectName("statusValue")
            if caption == "Camera":
                self.camera_value = value_label
            layout.addWidget(caption_label)
            layout.addWidget(value_label)
            cards.addWidget(card)
        return cards

    def startCamera(self):
        picker = CameraPickerDialog(self)
        picker.move(self.mapToGlobal(QPoint(22, 22)))
        if picker.exec_() and self.parent_window:
            self.parent_window.setActiveCamera(picker.selected_index, picker.selected_name)
            self.proceedButton.setEnabled(True)

    def updateCameraName(self, name):
        self.camera_value.setText(name)

    def openDashboard(self):
        if self.parent_window:
            self.parent_window.showDashboard()

    def showTutorial(self):
        if self.parent_window:
            self.parent_window.showTutorial()

    def closeApplication(self):
        if self.parent_window:
            self.parent_window.close()
