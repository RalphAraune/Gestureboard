from PyQt5.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout


class Sidebar(QFrame):
    """Shared left navigation for camera setup and the main dashboard."""

    def __init__(self, main_window, active_page):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("sidebar")
        self.setFixedWidth(190)
        self.setStyleSheet("""
            QFrame#sidebar { background: #0B1B32; border-right: 1px solid #203C5C; }
            QLabel { background: transparent; color: #EAF1FF; }
            QLabel#brand { font-size: 17px; font-weight: 700; }
            QLabel#section { color: #71809C; font-size: 10px; font-weight: 700; }
            QPushButton { background: transparent; border: none; border-radius: 7px; color: #AEBBD0; text-align: left; padding: 9px 12px; }
            QPushButton:hover, QPushButton#active { background: #153969; color: #69A0FF; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 18, 14, 16)
        layout.addWidget(self._label("G   GestureBoard", "brand"))
        layout.addSpacing(28)
        layout.addWidget(self._label("NAVIGATION", "section"))

        pages = (
            ("Home", "⌂  Home", main_window.showHome),
            ("Camera Setup", "▣  Camera Setup", main_window.showCameraSetup),
            ("Dashboard", "▦  Dashboard", main_window.showDashboard),
            ("Virtual Mouse", "✋  Virtual Mouse", None),
            ("Presentation", "▸  Presentation", None),
            ("Whiteboard", "✎  Whiteboard & Annotation", None),
            ("Saved Files", "▣  Saved Files", None),
            ("Settings", "⚙  Settings", None),
        )
        for key, label, callback in pages:
            button = QPushButton(label)
            if key == active_page:
                button.setObjectName("active")
            if callback:
                button.clicked.connect(callback)
            layout.addWidget(button)
        layout.addStretch()
        camera_state = QLabel("●  Camera active")
        camera_state.setStyleSheet("color: #45D99A; font-size: 11px;")
        layout.addWidget(camera_state)

    @staticmethod
    def _label(text, object_name):
        label = QLabel(text)
        label.setObjectName(object_name)
        return label
