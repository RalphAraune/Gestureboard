from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
    QGridLayout, QScrollArea,
)

from widgets import page_background
from widgets.sidebar import sidebar_logo


# Brand accent used on the navy welcome banner.
CYAN = "#22C3DE"


def _colors():
    from settings import theme as app_theme
    return page_background.page_colors(), app_theme.is_dark()


class StatusCard(QFrame):
    """One cell of the system status strip: a label and a coloured state."""

    def __init__(self, title, status_text, status_color="#2F9E62", parent=None):
        super().__init__(parent)
        self.setObjectName("statusCell")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._status_color = status_color

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("cellTitle")
        layout.addWidget(title_label)

        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        self._dot = QLabel("●")
        self._status = QLabel(status_text)
        self._status.setObjectName("cellStatus")
        status_row.addWidget(self._dot)
        status_row.addWidget(self._status, 1)
        layout.addLayout(status_row)

        self._status_color = None
        self.set_status(status_text, status_color)

    def apply_theme(self):
        """Colours come from the page stylesheet; nothing to do here."""

    def set_status(self, text, color):
        if self._status.text() == text and self._status_color == color:
            return
        self._status_color = color
        self._status.setText(text)
        self._status.setToolTip(text)
        self._dot.setStyleSheet(f"color: {color}; font-size: 11px;")
        self._status.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: 700;")


class FeatureCard(QFrame):
    """Tool card: icon, title, description and an Open button."""

    def __init__(self, title, icon, description, button_text, callback=None, parent=None):
        super().__init__(parent)
        self.setObjectName("featureCard")
        self.setMinimumHeight(178)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(14)

        icon_label = QLabel(icon)
        icon_label.setObjectName("featureIcon")
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)

        title_label = QLabel(title)
        title_label.setObjectName("featureTitle")
        title_label.setWordWrap(True)

        header.addWidget(icon_label)
        header.addWidget(title_label, 1)
        layout.addLayout(header)

        desc_label = QLabel(description)
        desc_label.setObjectName("featureDesc")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        layout.addStretch()

        btn = QPushButton(button_text)
        btn.setObjectName("featureButton")
        btn.setCursor(Qt.PointingHandCursor)
        if callback:
            btn.clicked.connect(callback)
        layout.addWidget(btn, 0, Qt.AlignLeft)

    def apply_theme(self):
        """Colours come from the page stylesheet; nothing to do here."""


class DashboardPage(QWidget):
    """Home: welcome banner, live system status and the main tools."""

    GREEN = "#2F9E62"
    AMBER = "#D08A24"
    RED = "#D9534F"
    GREY = "#7F92B0"

    FEATURES = [
        ("Presentation control", "📺",
         "Move through slides, point and draw on them with hand gestures.",
         "Open presentation control", "showPresentation"),
        ("Virtual mouse", "🖱",
         "Move the cursor, click and scroll anywhere with your hand.",
         "Open virtual mouse", "showVirtualMouse"),
        ("Whiteboard", "🖥",
         "Write and sketch with gestures or a regular mouse.",
         "Open whiteboard", "showWhiteboard"),
        ("Saved files", "📁",
         "Open, rename and manage saved whiteboards and annotations.",
         "Open saved files", "showSavedFiles"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setObjectName("dashboard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setObjectName("dashScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root.addWidget(scroll)

        content = QWidget()
        content.setObjectName("contentArea")
        self._content = content
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(36, 28, 36, 32)
        layout.setSpacing(22)

        layout.addWidget(self._build_banner())

        # ---------------- System status ----------------
        layout.addWidget(self._section("System status"))

        strip = QFrame()
        strip.setObjectName("statusStrip")
        strip_layout = QHBoxLayout(strip)
        strip_layout.setContentsMargins(0, 0, 0, 0)
        strip_layout.setSpacing(0)

        self.status_cards = [
            StatusCard("Camera", "Not selected", self.GREY),
            StatusCard("Hand tracking", "Off", self.GREY),
            StatusCard("Gesture recognition", "Checking…", self.GREY),
            StatusCard("Virtual mouse", "Off", self.GREY),
        ]

        for i, card in enumerate(self.status_cards):
            if i:
                divider = QFrame()
                divider.setObjectName("divider")
                divider.setFixedWidth(1)
                strip_layout.addWidget(divider)
            strip_layout.addWidget(card, 1)

        layout.addWidget(strip)

        # ---------------- Tools ----------------
        layout.addWidget(self._section("Tools"))

        self.grid = QGridLayout()
        self.grid.setSpacing(16)

        self.feature_cards = []
        for title, icon, desc, btn_text, cb_name in self.FEATURES:
            callback = getattr(parent, cb_name, None)
            self.feature_cards.append(FeatureCard(title, icon, desc, btn_text, callback))

        self._columns = 0
        self._reflow(2)

        layout.addLayout(self.grid)
        layout.addStretch()

        page_background.clear_layers(self)
        self.apply_theme()

        # Status reflects the real app state, refreshed while visible.
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self.refresh_status)

    # ==========================================================
    # PIECES
    # ==========================================================

    def _section(self, text):
        label = QLabel(text)
        label.setObjectName("section")
        return label

    def _build_banner(self):

        banner = QFrame()
        banner.setObjectName("banner")
        banner.setMinimumHeight(190)

        layout = QHBoxLayout(banner)
        layout.setContentsMargins(34, 26, 34, 26)
        layout.setSpacing(28)

        self.banner_logo = QLabel()
        self.banner_logo.setObjectName("bannerLogo")
        self.banner_logo.setFixedWidth(130)
        self.banner_logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.banner_logo)

        text = QVBoxLayout()
        text.setSpacing(8)

        title = QLabel("Welcome to GestureBoard")
        title.setObjectName("bannerTitle")
        title.setWordWrap(True)

        subtitle = QLabel(
            "Control your slides, your cursor and a whiteboard with your hand."
        )
        subtitle.setObjectName("bannerText")
        subtitle.setWordWrap(True)

        chips = QHBoxLayout()
        chips.setSpacing(10)

        self.camera_chip = QLabel("Camera: not selected")
        self.camera_chip.setObjectName("chip")
        self.vmouse_chip = QLabel("Virtual mouse: off")
        self.vmouse_chip.setObjectName("chip")

        chips.addWidget(self.camera_chip)
        chips.addWidget(self.vmouse_chip)
        chips.addStretch()

        text.addStretch()
        text.addWidget(title)
        text.addWidget(subtitle)
        text.addSpacing(6)
        text.addLayout(chips)
        text.addStretch()

        layout.addLayout(text, 1)

        actions = QVBoxLayout()
        actions.setSpacing(10)
        actions.addStretch()

        start = QPushButton("Start virtual mouse")
        start.setObjectName("bannerPrimary")
        start.setCursor(Qt.PointingHandCursor)
        start.clicked.connect(self._start_virtual_mouse)

        camera = QPushButton("Camera setup")
        camera.setObjectName("bannerGhost")
        camera.setCursor(Qt.PointingHandCursor)
        callback = getattr(self.parent_window, "showCameraSetup", None)
        if callback:
            camera.clicked.connect(callback)

        actions.addWidget(start)
        actions.addWidget(camera)
        actions.addStretch()

        layout.addLayout(actions)

        return banner

    def _start_virtual_mouse(self):
        """Open the Virtual Mouse page and start tracking."""
        win = self.parent_window
        if win is None:
            return
        show = getattr(win, "showVirtualMouse", None)
        if show:
            show()
        vmouse = getattr(win, "virtual_mouse", None)
        if vmouse is not None and not getattr(vmouse, "camera_running", False):
            vmouse.start_tracking()

    def _reflow(self, columns):
        if columns == self._columns:
            return
        self._columns = columns
        for card in self.feature_cards:
            self.grid.removeWidget(card)
        for i, card in enumerate(self.feature_cards):
            self.grid.addWidget(card, i // columns, i % columns)
        for c in range(4):
            self.grid.setColumnStretch(c, 1 if c < columns else 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        width = self.width()
        self._reflow(4 if width >= 1280 else 2 if width >= 640 else 1)

    # ==========================================================
    # STATUS
    # ==========================================================

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
            camera_text = "Camera: not selected"
        else:
            camera.set_status(win.active_camera_name, self.GREEN)
            camera_text = f"Camera: {win.active_camera_name}"

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
            vm_text = "Virtual mouse: on"
        elif vm_paused:
            tracking.set_status("Paused", self.AMBER)
            vmouse_card.set_status("Paused", self.AMBER)
            vm_text = "Virtual mouse: paused"
        else:
            tracking.set_status("Off", self.GREY)
            vmouse_card.set_status("Off", self.GREY)
            vm_text = "Virtual mouse: off"

        if self.camera_chip.text() != camera_text:
            self.camera_chip.setText(camera_text)
        if self.vmouse_chip.text() != vm_text:
            self.vmouse_chip.setText(vm_text)

    # ==========================================================
    # THEME
    # ==========================================================

    def apply_theme(self):

        c, dark = _colors()

        banner_bg = c["sidebar"]
        banner_text = c["sidebar_text"]

        self.banner_logo.setPixmap(sidebar_logo(120, banner_text))

        self._page_colors = c

        self.setStyleSheet(page_background.LAYER_RULE + f"""
            QWidget#dashboard, QWidget#contentArea, QScrollArea#dashScroll {{
                background: transparent;
                border: none;
            }}
            QLabel {{ background: transparent; color: {c['text']}; }}
            QLabel#section {{ font-size: 17px; font-weight: 700; color: {c['text']}; }}

            QFrame#banner {{
                background: {banner_bg};
                border: none;
                border-radius: 20px;
            }}
            QFrame#banner QLabel {{ color: {banner_text}; }}
            QLabel#bannerTitle {{ font-size: 30px; font-weight: 800; }}
            QLabel#bannerText {{ font-size: 15px; color: {c['muted'] if not dark else c['text_secondary']}; }}
            QFrame#banner QLabel#bannerText {{ color: #C9D8EE; }}
            QFrame#banner QLabel#chip {{
                background: rgba(255, 255, 255, 0.10);
                color: {banner_text};
                border-radius: 12px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#bannerPrimary {{
                background: {CYAN};
                color: #0B1F4D;
                border: none;
                border-radius: 10px;
                padding: 12px 22px;
                font-size: 14px;
                font-weight: 800;
                min-width: 190px;
            }}
            QPushButton#bannerPrimary:hover {{ background: #4BD3EA; }}
            QPushButton#bannerGhost {{
                background: transparent;
                color: {banner_text};
                border: 1px solid rgba(255, 255, 255, 0.35);
                border-radius: 10px;
                padding: 11px 22px;
                font-size: 14px;
                font-weight: 600;
                min-width: 190px;
            }}
            QPushButton#bannerGhost:hover {{ background: rgba(255, 255, 255, 0.10); }}

            QFrame#statusStrip {{
                background: {c['card']};
                border: 1px solid {c['border']};
                border-radius: 14px;
            }}
            QFrame#statusCell {{ background: transparent; border: none; }}
            QFrame#divider {{ background: {c['border']}; border: none; margin: 14px 0; }}
            QLabel#cellTitle {{ color: {c['text_secondary']}; font-size: 13px; }}

            QFrame#featureCard {{
                background: {c['card']};
                border: 1px solid {c['border']};
                border-radius: 16px;
            }}
            QFrame#featureCard:hover {{ border: 1px solid {c['primary']}; }}
            QLabel#featureIcon {{
                background: {c['button_hover']};
                border-radius: 12px;
                font-family: "Segoe UI Emoji";
                font-size: 24px;
            }}
            QLabel#featureTitle {{ font-size: 17px; font-weight: 800; color: {c['text']}; }}
            QLabel#featureDesc {{ color: {c['text_secondary']}; font-size: 13px; }}
            QPushButton#featureButton {{
                background: {c['primary']};
                color: {c['primary_text']};
                border: none;
                border-radius: 9px;
                padding: 9px 16px;
                font-size: 13px;
                font-weight: 700;
            }}
            QPushButton#featureButton:hover {{ background: {c['sidebar_hover']}; }}
        """)

        self.update()

    def paintEvent(self, event):
        page_background.paint_page_background(self, self._page_colors)

    # ==========================================================
    # API USED BY MAIN WINDOW
    # ==========================================================

    def updateCameraName(self, name):
        """Update camera status."""
        self.refresh_status()

    def setActiveCamera(self, name):
        """Show the active camera name in the status strip."""
        self.refresh_status()

    def setActivePage(self, page_name):
        """No-op: sidebar is managed globally by MainWindow."""
