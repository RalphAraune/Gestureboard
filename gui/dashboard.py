from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget, QGridLayout
)

from widgets.sidebar import TitleBar


class StatusCard(QFrame):
    """Compact status card for dashboard."""

    def __init__(self, title, status_text, status_color="#2F9E62", parent=None):
        super().__init__(parent)
        self.setObjectName("statusCard")
        self.setFixedHeight(80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("""
            QFrame#statusCard {
                background: #FFFFFF;
                border: 1px solid #AAC0E1;
                border-radius: 10px;
            }
            QLabel { background: transparent; color: #0E2F76; }
            QLabel#cardTitle { color: #AAC0E1; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; }
            QLabel#cardStatus { font-size: 14px; font-weight: 600; }
            QLabel#statusDot { color: #2F9E62; font-size: 10px; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        # Title
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        layout.addWidget(title_label)

        # Status row
        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {status_color}; font-size: 10px;")
        status = QLabel(status_text)
        status.setObjectName("cardStatus")
        status.setStyleSheet(f"color: {status_color}; font-size: 14px; font-weight: 600;")
        status_row.addWidget(dot)
        status_row.addWidget(status)
        status_row.addStretch()
        layout.addLayout(status_row)


class FeatureCard(QFrame):
    """Larger feature card with icon, description, and action button."""

    def __init__(self, title, icon, description, button_text, callback=None, parent=None):
        super().__init__(parent)
        self.setObjectName("featureCard")
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("""
            QFrame#featureCard {
                background: #FFFFFF;
                border: 1px solid #AAC0E1;
                border-radius: 12px;
            }
            QFrame#featureCard:hover {
                border: 1px solid #6E8FC8;
            }
            QLabel { background: transparent; color: #0E2F76; }
            QLabel#featureTitle { font-size: 15px; font-weight: 800; color: #0E2F76; }
            QLabel#featureDesc { color: #5A6B93; font-size: 12px; }
            QLabel#featureIcon { font-size: 28px; }
            QPushButton {
                background: #0E2F76;
                color: #F5FEFF;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #1B4499;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        # Header: Icon + Title
        header = QHBoxLayout()
        header.setSpacing(12)
        icon_label = QLabel(icon)
        icon_label.setObjectName("featureIcon")
        title_label = QLabel(title)
        title_label.setObjectName("featureTitle")
        header.addWidget(icon_label)
        header.addWidget(title_label)
        header.addStretch()
        layout.addLayout(header)

        # Description
        desc_label = QLabel(description)
        desc_label.setObjectName("featureDesc")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        layout.addStretch()

        # Action button
        btn = QPushButton(button_text)
        btn.setCursor(Qt.PointingHandCursor)
        if callback:
            btn.clicked.connect(callback)
        layout.addWidget(btn)


class DashboardPage(QWidget):
    """Main app dashboard shown after camera verification."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setObjectName("dashboard")
        self.setStyleSheet("""
            QWidget#dashboard { background: #F5FEFF; }
            QLabel { background: transparent; color: #0E2F76; }
            QLabel#heading { font-size: 28px; font-weight: 800; color: #0E2F76; }
            QLabel#subtitle { color: #5A6B93; font-size: 13px; }
        """)

        # Root layout with content only.
        # The navigation sidebar is provided globally by MainWindow, so the
        # Dashboard itself does not create its own sidebar (avoids duplicates).
        view = QVBoxLayout(self)
        view.setContentsMargins(0, 0, 0, 0)
        view.setSpacing(0)

        # Content area
        content = QWidget()
        content.setObjectName("contentArea")
        content.setStyleSheet("""
            QWidget#contentArea { background: #F5FEFF; }
        """)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 24, 32, 24)
        content_layout.setSpacing(24)

        # Dashboard heading
        heading = QLabel("Dashboard")
        heading.setObjectName("heading")
        content_layout.addWidget(heading)

        # Subtitle
        subtitle = QLabel("Control your presentations and computer using gesture interaction.")
        subtitle.setObjectName("subtitle")
        content_layout.addWidget(subtitle)

        content_layout.addSpacing(8)

        # Status cards row
        status_row = QHBoxLayout()
        status_row.setSpacing(16)
        self.status_cards = [
            StatusCard("CAMERA", "Connected", "#2F9E62"),
            StatusCard("HAND TRACKING", "Active", "#2F9E62"),
            StatusCard("GESTURE RECOGNITION", "Ready", "#2F9E62"),
            StatusCard("CURRENT MODE", "Idle", "#E8A33D"),
        ]
        for card in self.status_cards:
            status_row.addWidget(card)
        content_layout.addLayout(status_row)

        content_layout.addSpacing(16)

        # Feature cards grid
        grid = QGridLayout()
        grid.setSpacing(16)
        grid.setContentsMargins(0, 0, 0, 0)

        features = [
            ("Presentation Control", "📺", "Navigate presentation slides using gestures", "Open Presentation", "showPresentation"),
            ("Virtual Mouse", "🖱", "Control your computer cursor using hand gestures", "Open Virtual Mouse", "showVirtualMouse"),
            ("Whiteboard", "🖥", "Draw and write using your mouse", "Open Whiteboard", "showWhiteboard"),
            ("Annotation", "✎", "Annotate presentation materials using mouse controls", "Open Annotation", "showAnnotation"),
        ]

        for idx, (title, icon, desc, btn_text, cb_name) in enumerate(features):
            row, col = divmod(idx, 2)
            callback = getattr(parent, cb_name, None)
            card = FeatureCard(title, icon, desc, btn_text, callback)
            grid.addWidget(card, row, col)

        content_layout.addLayout(grid)
        content_layout.addStretch()

        view.addWidget(content, 1)

    def updateCameraName(self, name):
        """Update camera status card."""
        if self.status_cards:
            self.status_cards[0].findChild(QLabel, "cardStatus").setText(name)

    def setActiveCamera(self, name):
        """Show the active camera name in the CAMERA status card."""
        if self.status_cards:
            self.status_cards[0].findChild(QLabel, "cardStatus").setText(name)

    def setActivePage(self, page_name):
        """No-op: sidebar is managed globally by MainWindow."""