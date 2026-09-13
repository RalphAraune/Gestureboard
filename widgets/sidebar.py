from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt5.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy


class Sidebar(QFrame):
    """Left navigation sidebar for GestureBoard dashboard."""

    NAV_ITEMS = [
        ("Home", "🏠", "showDashboard"),
        ("Camera Setup", "📷", "showCameraSetup"),
        ("Presentation Control", "🎞", "showPresentation"),
        ("Virtual Mouse", "🖱", "showVirtualMouse"),
        ("Whiteboard", "🖥", "showWhiteboard"),
        ("Annotation", "✎", "showAnnotation"),
        ("Saved Files", "📁", "showSavedFiles"),
        ("Settings", "⚙", "showSettings"),
    ]

    def __init__(self, main_window, active_page="Home"):
        super().__init__()
        self.main_window = main_window
        self.active_page = active_page
        self.setObjectName("sidebar")
        self.setFixedWidth(210)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setStyleSheet(self._stylesheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(0)

        # Brand
        brand_layout = QHBoxLayout()
        brand_layout.setSpacing(10)
        self.brand_icon = QLabel("G")
        self.brand_icon.setObjectName("brandIcon")
        self.brand_icon.setFixedSize(28, 28)
        self.brand_icon.setAlignment(Qt.AlignCenter)
        brand_text = QLabel("GestureBoard")
        brand_text.setObjectName("brand")
        brand_layout.addWidget(self.brand_icon)
        brand_layout.addWidget(brand_text)
        brand_layout.addStretch()
        layout.addLayout(brand_layout)

        layout.addSpacing(24)

        # Navigation section
        section_label = QLabel("NAVIGATION")
        section_label.setObjectName("section")
        layout.addWidget(section_label)

        layout.addSpacing(8)

        self.nav_buttons = {}
        for key, icon, callback_name in self.NAV_ITEMS:
            btn = QPushButton(f"{icon}  {key}")
            btn.setCursor(Qt.PointingHandCursor)
            if key == active_page:
                btn.setObjectName("active")
            callback = getattr(main_window, callback_name, None)
            if callback:
                btn.clicked.connect(callback)
            self.nav_buttons[key] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # Status section at bottom
        status_section = QFrame()
        status_section.setObjectName("statusSection")
        status_layout = QVBoxLayout(status_section)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(4)

        camera_status = QHBoxLayout()
        camera_status.setSpacing(8)
        camera_dot = QLabel("●")
        camera_dot.setObjectName("statusDot")
        camera_text = QLabel("Camera Connected")
        camera_text.setObjectName("statusLabel")
        camera_status.addWidget(camera_dot)
        camera_status.addWidget(camera_text)
        camera_status.addStretch()
        status_layout.addLayout(camera_status)

        fps_layout = QHBoxLayout()
        fps_layout.setSpacing(8)
        fps_dot = QLabel("●")
        fps_dot.setObjectName("fpsLabel")
        fps_text = QLabel("FPS: 30")
        fps_text.setObjectName("fpsLabel")
        fps_layout.addWidget(fps_dot)
        fps_layout.addWidget(fps_text)
        fps_layout.addStretch()
        status_layout.addLayout(fps_layout)

        layout.addWidget(status_section)

    def _stylesheet(self):

        from settings import theme as app_theme

        c = app_theme.colors()

        return f"""
            QFrame#sidebar {{
                background: {c['sidebar']};
                border-right: 1px solid {c['border']};
            }}
            QLabel {{ background: transparent; color: {c['sidebar_text']}; }}
            QLabel#brand {{ font-size: 16px; font-weight: 700; color: {c['sidebar_text']}; }}
            QLabel#brandIcon {{ font-size: 22px; }}
            QLabel#section {{ color: {c['muted']}; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; }}
            QLabel#statusLabel {{ color: {c['sidebar_text']}; font-size: 11px; }}
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 8px;
                color: {c['sidebar_text']};
                text-align: left;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {c['sidebar_hover']};
                color: {c['sidebar_text']};
            }}
            QPushButton#active {{
                background: {c['accent']};
                color: {c['accent_text']};
                font-weight: 700;
            }}
            QPushButton#active:hover {{
                background: {c['accent']};
                color: {c['accent_text']};
            }}
            QFrame#statusSection {{
                background: transparent;
                border-top: 1px solid {c['border']};
                padding-top: 12px;
                margin-top: 8px;
            }}
            QLabel#statusDot {{ color: {c['accent']}; font-size: 10px; }}
            QLabel#fpsLabel {{ color: {c['muted']}; font-size: 10px; margin-top: 4px; }}
        """

    def apply_theme(self):

        from settings import theme as app_theme

        c = app_theme.colors()

        self.setStyleSheet(self._stylesheet())

        if hasattr(self, "brand_icon"):
            self.brand_icon.setStyleSheet(
                f"background:{c['sidebar_text']}; color:{c['sidebar']};"
                "border-radius:14px; font-size:16px; font-weight:800;"
            )

    def setActivePage(self, page_name):
        """Update active navigation item."""
        for key, btn in self.nav_buttons.items():
            btn.setObjectName("active" if key == page_name else "")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.active_page = page_name


class TitleBar(QFrame):
    """Custom title bar with logo, status, and window controls."""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("titleBar")
        self.setFixedHeight(44)
        self.setStyleSheet(self._stylesheet())

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(12)

        # Left: Logo + Title
        title_layout = QHBoxLayout()
        title_layout.setSpacing(10)
        self.logo = QLabel("G")
        self.logo.setFixedSize(26, 26)
        self.logo.setAlignment(Qt.AlignCenter)
        title = QLabel("GestureBoard")
        title.setObjectName("titleText")
        title_layout.addWidget(self.logo)
        title_layout.addWidget(title)
        layout.addLayout(title_layout)

        layout.addStretch()

        # Right: Status + Window controls
        status_label = QLabel("●  System Ready")
        status_label.setObjectName("statusReady")
        layout.addWidget(status_label)

        layout.addSpacing(8)

        # Window controls
        btn_min = QPushButton("—")
        btn_min.setToolTip("Minimize")
        btn_min.clicked.connect(main_window.showMinimized)

        btn_max = QPushButton("□")
        btn_max.setToolTip("Maximize/Restore")
        btn_max.clicked.connect(self._toggle_maximize)

        btn_close = QPushButton("✕")
        btn_close.setObjectName("closeBtn")
        btn_close.setToolTip("Close")
        btn_close.clicked.connect(main_window.close)

        layout.addWidget(btn_min)
        layout.addWidget(btn_max)
        layout.addWidget(btn_close)

        # Track mouse for window dragging
        self._drag_pos = None

    def _stylesheet(self):

        from settings import theme as app_theme

        c = app_theme.colors()

        return f"""
            QFrame#titleBar {{
                background: {c['sidebar']};
                border-bottom: 1px solid {c['border']};
            }}
            QLabel {{ background: transparent; color: {c['sidebar_text']}; }}
            QLabel#titleText {{ font-size: 15px; font-weight: 700; color: {c['sidebar_text']}; }}
            QLabel#statusReady {{ color: {c['sidebar_text']}; font-size: 11px; font-weight: 600; }}
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
                min-width: 36px;
                min-height: 28px;
                color: {c['sidebar_text']};
            }}
            QPushButton:hover {{
                background: {c['sidebar_hover']};
                color: {c['sidebar_text']};
            }}
            QPushButton#closeBtn:hover {{
                background: #E81123;
                color: #FFFFFF;
            }}
        """

    def apply_theme(self):

        from settings import theme as app_theme

        c = app_theme.colors()

        self.setStyleSheet(self._stylesheet())

        if hasattr(self, "logo"):
            self.logo.setStyleSheet(
                f"background:{c['sidebar_text']}; border-radius:13px;"
                f"color:{c['sidebar']}; font-size:14px; font-weight:800;"
            )

    def _toggle_maximize(self):
        if self.main_window.isMaximized():
            self.main_window.showNormal()
        else:
            self.main_window.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.main_window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            self.main_window.move(event.globalPos() - self._drag_pos)
            event.accept()