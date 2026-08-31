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
        self.setStyleSheet("""
            QFrame#sidebar {
                background: #0A1628;
                border-right: 1px solid #1E3A5F;
            }
            QLabel { background: transparent; color: #E8EDF5; }
            QLabel#brand { font-size: 16px; font-weight: 700; color: #FFFFFF; }
            QLabel#brandIcon { font-size: 22px; }
            QLabel#section { color: #6A7A9A; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; }
            QLabel#statusLabel { color: #8899BB; font-size: 11px; }
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 8px;
                color: #A8B3CC;
                text-align: left;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #142A4A;
                color: #FFFFFF;
            }
            QPushButton#active {
                background: #1E3A5F;
                color: #4A9EFF;
            }
            QPushButton#active:hover {
                background: #254478;
                color: #6AB0FF;
            }
            QFrame#statusSection {
                background: transparent;
                border-top: 1px solid #1E3A5F;
                padding-top: 12px;
                margin-top: 8px;
            }
            QLabel#statusDot { color: #45D99A; font-size: 10px; }
            QLabel#fpsLabel { color: #6A7A9A; font-size: 10px; margin-top: 4px; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(0)

        # Brand
        brand_layout = QHBoxLayout()
        brand_layout.setSpacing(10)
        brand_icon = QLabel("G")
        brand_icon.setObjectName("brandIcon")
        brand_icon.setFixedSize(28, 28)
        brand_icon.setAlignment(Qt.AlignCenter)
        brand_icon.setStyleSheet(
            "background:#3E7CF7; color:white; border-radius:14px;"
            "font-size:16px; font-weight:800;"
        )
        brand_text = QLabel("GestureBoard")
        brand_text.setObjectName("brand")
        brand_layout.addWidget(brand_icon)
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
        self.setStyleSheet("""
            QFrame#titleBar {
                background: #071426;
                border-bottom: 1px solid #1E3A5F;
            }
            QLabel { background: transparent; color: #FFFFFF; }
            QLabel#titleText { font-size: 15px; font-weight: 700; }
            QLabel#statusReady { color: #45D99A; font-size: 11px; font-weight: 600; }
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
                min-width: 36px;
                min-height: 28px;
                color: #9AA8C8;
            }
            QPushButton:hover {
                background: #1A2A4A;
                color: #FFFFFF;
            }
            QPushButton#closeBtn:hover {
                background: #E81123;
                color: #FFFFFF;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(12)

        # Left: Logo + Title
        title_layout = QHBoxLayout()
        title_layout.setSpacing(10)
        logo = QLabel("G")
        logo.setFixedSize(26, 26)
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(
            "background:#3E7CF7; border-radius:13px; color:white;"
            "font-size:14px; font-weight:800;"
        )
        title = QLabel("GestureBoard")
        title.setObjectName("titleText")
        title_layout.addWidget(logo)
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