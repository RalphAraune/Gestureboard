from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from widgets.sidebar import Sidebar


class DashboardPage(QWidget):
    """Main app dashboard shown after a camera has been verified."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setObjectName("dashboard")
        self.setStyleSheet("""
            QWidget#dashboard { background: #071426; }
            QLabel { background: transparent; color: #EAF1FF; }
            QLabel#heading { font-size: 26px; font-weight: 700; }
            QLabel#muted { color: #90A0BB; font-size: 13px; }
            QFrame#contentCard { background: #0F1E35; border: 1px solid #294263; border-radius: 14px; }
        """)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(Sidebar(parent, "Dashboard"))

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(42, 34, 42, 34)
        heading = QLabel("Main Dashboard")
        heading.setObjectName("heading")
        subtitle = QLabel("Your selected camera is ready. Choose a mode from the sidebar to begin.")
        subtitle.setObjectName("muted")
        card = QFrame()
        card.setObjectName("contentCard")
        card.setFixedSize(600, 260)
        card_layout = QVBoxLayout(card)
        ready = QLabel("GestureBoard is ready")
        ready.setStyleSheet("font-size: 22px; font-weight: 700;")
        message = QLabel("Select Virtual Mouse, Presentation, or Whiteboard & Annotation from the sidebar.")
        message.setObjectName("muted")
        message.setWordWrap(True)
        card_layout.addStretch()
        card_layout.addWidget(ready, 0, Qt.AlignCenter)
        card_layout.addWidget(message, 0, Qt.AlignCenter)
        card_layout.addStretch()
        content_layout.addWidget(heading)
        content_layout.addWidget(subtitle)
        self.camera_name = QLabel("Current camera: No camera selected")
        self.camera_name.setObjectName("muted")
        content_layout.addWidget(self.camera_name)
        content_layout.addSpacing(20)
        content_layout.addWidget(card)
        content_layout.addStretch()
        root.addWidget(content, 1)

    def updateCameraName(self, name):
        self.camera_name.setText(f"Current camera: {name}")
