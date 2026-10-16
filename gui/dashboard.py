from PyQt5.QtCore import Qt, QTimer
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

        self._status_color = status_color

        self.setStyleSheet(self._stylesheet())

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
        status = QLabel(status_text)
        status.setObjectName("cardStatus")
        self._dot = dot
        self._status = status
        self.set_status(status_text, status_color)
        status_row.addWidget(dot)
        status_row.addWidget(status)
        status_row.addStretch()
        layout.addLayout(status_row)

    def _stylesheet(self):
        from settings import theme as app_theme
        c = app_theme.colors()
        return f"""
            QFrame#statusCard {{
                background: {c['card']};
                border: 1px solid {c['border']};
                border-radius: 10px;
            }}
            QLabel {{ background: transparent; color: {c['text']}; }}
            QLabel#cardTitle {{ color: {c['text_secondary']}; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; }}
            QLabel#cardStatus {{ font-size: 14px; font-weight: 600; }}
        """

    def apply_theme(self):
        self.setStyleSheet(self._stylesheet())

    def set_status(self, text, color):
        if self._status.text() == text and self._status_color == color:
            return
        self._status_color = color
        self._status.setText(text)
        self._status.setToolTip(text)
        self._dot.setStyleSheet(f"color: {color}; font-size: 10px;")
        self._status.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: 600;")


class FeatureCard(QFrame):
    """Larger feature card with icon, description, and action button."""

    def __init__(self, title, icon, description, button_text, callback=None, parent=None):
        super().__init__(parent)
        self.setObjectName("featureCard")
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(self._stylesheet())

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

    def _stylesheet(self):
        from settings import theme as app_theme
        c = app_theme.colors()
        return f"""
            QFrame#featureCard {{
                background: {c['card']};
                border: 1px solid {c['border']};
                border-radius: 12px;
            }}
            QFrame#featureCard:hover {{
                border: 1px solid {c['accent']};
            }}
            QLabel {{ background: transparent; color: {c['text']}; }}
            QLabel#featureTitle {{ font-size: 15px; font-weight: 800; color: {c['text']}; }}
            QLabel#featureDesc {{ color: {c['text_secondary']}; font-size: 12px; }}
            QLabel#featureIcon {{ font-size: 28px; }}
            QPushButton {{
                background: {c['primary']};
                color: {c['primary_text']};
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {c['sidebar_hover']};
            }}
        """

    def apply_theme(self):
        self.setStyleSheet(self._stylesheet())


class DashboardPage(QWidget):
    """Main app dashboard shown after camera verification."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setObjectName("dashboard")
        self.setStyleSheet(self._stylesheet())

        # Root layout with content only.
        # The navigation sidebar is provided globally by MainWindow, so the
        # Dashboard itself does not create its own sidebar (avoids duplicates).
        view = QVBoxLayout(self)
        view.setContentsMargins(0, 0, 0, 0)
        view.setSpacing(0)

        # Content area
        content = QWidget()
        content.setObjectName("contentArea")
        content.setStyleSheet(self._content_stylesheet())
        self._content = content
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
            StatusCard("CAMERA", "Not selected", self.GREY),
            StatusCard("HAND TRACKING", "Off", self.GREY),
            StatusCard("GESTURE RECOGNITION", "Checking…", self.GREY),
            StatusCard("VIRTUAL MOUSE", "Off", self.GREY),
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
            ("Saved Files", "📁", "Open, rename and manage your saved whiteboards and annotations", "Open Saved Files", "showSavedFiles"),
        ]

        self.feature_cards = []
        for idx, (title, icon, desc, btn_text, cb_name) in enumerate(features):
            row, col = divmod(idx, 2)
            callback = getattr(parent, cb_name, None)
            card = FeatureCard(title, icon, desc, btn_text, callback)
            self.feature_cards.append(card)
            grid.addWidget(card, row, col)

        content_layout.addLayout(grid)
        content_layout.addStretch()

        view.addWidget(content, 1)

        # Status cards reflect the real app state, refreshed while visible.
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self.refresh_status)

    GREEN = "#2F9E62"
    AMBER = "#E8A33D"
    RED = "#D9534F"
    GREY = "#8A9BB5"

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_status()
        self._status_timer.start(1000)

    def hideEvent(self, event):
        super().hideEvent(event)
        self._status_timer.stop()

    def refresh_status(self):
        win = self.parent_window
        if win is None or not self.status_cards:
            return

        camera, tracking, gestures, vmouse_card = self.status_cards

        if getattr(win, "active_camera_index", None) is None:
            camera.set_status("Not selected", self.AMBER)
        else:
            camera.set_status(win.active_camera_name, self.GREEN)

        vmouse = getattr(win, "virtual_mouse", None)
        vm_running = bool(vmouse and getattr(vmouse, "camera_running", False))
        vm_paused = bool(vmouse and getattr(vmouse, "camera_paused", False))
        has_mediapipe = bool(vmouse and getattr(vmouse, "hands", None) is not None)

        if not has_mediapipe:
            gestures.set_status("Unavailable", self.RED)
        else:
            gestures.set_status("Ready", self.GREEN)

        if vm_running and not vm_paused:
            hand = vmouse.get_latest_hand() if hasattr(vmouse, "get_latest_hand") else None
            tracking.set_status(
                "Hand detected" if hand is not None else "Looking for hand",
                self.GREEN if hand is not None else self.AMBER,
            )
            vmouse_card.set_status("On", self.GREEN)
        elif vm_paused:
            tracking.set_status("Paused", self.AMBER)
            vmouse_card.set_status("Paused", self.AMBER)
        else:
            tracking.set_status("Off", self.GREY)
            vmouse_card.set_status("Off", self.GREY)

    def _stylesheet(self):
        from settings import theme as app_theme
        c = app_theme.colors()
        return f"""
            QWidget#dashboard {{ background: {c['bg']}; }}
            QLabel {{ background: transparent; color: {c['text']}; }}
            QLabel#heading {{ font-size: 28px; font-weight: 800; color: {c['text']}; }}
            QLabel#subtitle {{ color: {c['text_secondary']}; font-size: 13px; }}
        """

    def _content_stylesheet(self):
        from settings import theme as app_theme
        c = app_theme.colors()
        return f"""
            QWidget#contentArea {{ background: {c['bg']}; }}
        """

    def apply_theme(self):
        self.setStyleSheet(self._stylesheet())
        if hasattr(self, "_content"):
            self._content.setStyleSheet(self._content_stylesheet())
        for card in getattr(self, "status_cards", []):
            if hasattr(card, "apply_theme"):
                card.apply_theme()
        for card in getattr(self, "feature_cards", []):
            if hasattr(card, "apply_theme"):
                card.apply_theme()

    def updateCameraName(self, name):
        """Update camera status card."""
        self.refresh_status()

    def setActiveCamera(self, name):
        """Show the active camera name in the CAMERA status card."""
        self.refresh_status()

    def setActivePage(self, page_name):
        """No-op: sidebar is managed globally by MainWindow."""