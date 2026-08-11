from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from gui.camera_setup import CameraPickerDialog


class HomePage(QWidget):
    """Main landing page displayed after the tutorial."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setObjectName("homePage")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget#homePage { background: #071426; }
            QFrame#heroPanel {
                background: qradialgradient(cx:0.5, cy:0.45, radius:0.58,
                    fx:0.5, fy:0.45, stop:0 #102546, stop:0.99 #102546, stop:1 #071426);
            }
            QLabel { background: transparent; color: #F4F7FF; }
            QLabel#appMark {
                background: #3E7CF7; border: 2px solid #5C96FF; border-radius: 48px;
                color: white; font-size: 38px; font-weight: 700;
            }
            QLabel#appTitle { font-size: 30px; font-weight: 700; }
            QLabel#subtitle { color: #95A1B8; font-size: 13px; }
            QFrame#readyBadge { background: #10223D; border: 1px solid #294263; border-radius: 15px; }
            QLabel#readyText { color: #45D99A; font-size: 12px; }
            QPushButton {
                background: #152842; color: #AEB9CD; border: 1px solid #294263; border-radius: 8px;
                min-height: 34px; font-size: 12px;
            }
            QPushButton:hover { background: #1B3555; color: white; }
            QPushButton#startButton {
                background: #3E7CF7; color: white; border: none; border-radius: 10px;
                min-height: 44px; font-size: 14px; font-weight: 700;
            }
            QPushButton#startButton:hover { background: #5790FF; }
            QFrame#statusCard { background: #0F1E35; border: 1px solid #294263; border-radius: 8px; }
            QLabel#statusCaption { color: #7E8AA2; font-size: 11px; }
            QLabel#statusValue { color: #DCE5F7; font-size: 13px; font-weight: 600; }
            QLabel#footer { color: #59657E; font-size: 11px; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 12)
        root.addStretch()

        hero = QFrame()
        hero.setObjectName("heroPanel")
        hero.setFixedSize(650, 465)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(54, 24, 54, 18)
        hero_layout.setSpacing(10)
        hero_layout.setAlignment(Qt.AlignCenter)

        mark = QLabel("G")
        mark.setObjectName("appMark")
        mark.setFixedSize(96, 96)
        mark.setAlignment(Qt.AlignCenter)
        title = QLabel("GestureBoard")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Gesture-Controlled Presentation & Annotation System")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignCenter)

        badge = QFrame()
        badge.setObjectName("readyBadge")
        badge.setFixedHeight(30)
        badge_layout = QHBoxLayout(badge)
        badge_layout.setContentsMargins(12, 0, 12, 0)
        ready = QLabel("●  OpenCV & MediaPipe Ready")
        ready.setObjectName("readyText")
        badge_layout.addWidget(ready, 0, Qt.AlignCenter)

        self.startButton = QPushButton("Start Camera")
        self.startButton.setObjectName("startButton")
        self.startButton.setFixedWidth(180)
        self.startButton.clicked.connect(self.startCamera)
        self.proceedButton = QPushButton("Proceed to Dashboard")
        self.proceedButton.setObjectName("startButton")
        self.proceedButton.setFixedWidth(180)
        self.proceedButton.setEnabled(False)
        self.proceedButton.clicked.connect(self.openDashboard)

        controls = QHBoxLayout()
        controls.setSpacing(12)
        self.settingsButton = QPushButton("Settings")
        self.guideButton = QPushButton("User Guide")
        self.exitButton = QPushButton("Exit")
        self.guideButton.clicked.connect(self.showTutorial)
        self.exitButton.clicked.connect(self.closeApplication)
        controls.addWidget(self.settingsButton)
        controls.addWidget(self.guideButton)
        controls.addWidget(self.exitButton)

        hero_layout.addWidget(mark, 0, Qt.AlignCenter)
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        hero_layout.addSpacing(5)
        hero_layout.addWidget(badge, 0, Qt.AlignCenter)
        hero_layout.addSpacing(8)
        primary_actions = QHBoxLayout()
        primary_actions.addStretch()
        primary_actions.addWidget(self.startButton)
        primary_actions.addWidget(self.proceedButton)
        primary_actions.addStretch()
        hero_layout.addLayout(primary_actions)
        hero_layout.addSpacing(4)
        hero_layout.addLayout(controls)
        hero_layout.addSpacing(12)
        hero_layout.addLayout(self._status_cards())

        root.addWidget(hero, 0, Qt.AlignCenter)
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
            card.setFixedSize(122, 50)
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
