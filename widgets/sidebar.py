from pathlib import Path

from PyQt5.QtCore import Qt, QSize, QTimer, QPointF, QRectF
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QImage, QPen, QPainterPath
from PyQt5.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy


LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo" / "logo2.png"


# ==============================================================
# LOGO
#
# logo2.png has a navy "G" that would vanish on the navy sidebar,
# so its dark strokes are redrawn in the sidebar text colour while
# the cyan hand keeps its own colour. The empty margin around the
# artwork is cropped so the logo fills its space.
# ==============================================================

_logo_cache = {}


def sidebar_logo(height, dark_color=None):
    """Return the cropped logo as a QPixmap `height` px tall.

    When `dark_color` is given, the logo's navy strokes are recoloured
    to it (for use on dark backgrounds).
    """

    key = (height, dark_color)

    if key in _logo_cache:
        return _logo_cache[key]

    image = QImage(str(LOGO_PATH))

    if image.isNull():
        return QPixmap()

    image = image.convertToFormat(QImage.Format_ARGB32)

    # Crop to the visible artwork.
    w, h = image.width(), image.height()
    xs, ys = [], []

    for y in range(0, h, 2):
        for x in range(0, w, 2):
            if (image.pixel(x, y) >> 24) & 0xFF > 20:
                xs.append(x)
                ys.append(y)

    if xs:
        pad = 6
        left = max(0, min(xs) - pad)
        top = max(0, min(ys) - pad)
        right = min(w - 1, max(xs) + pad)
        bottom = min(h - 1, max(ys) + pad)
        image = image.copy(left, top, right - left + 1, bottom - top + 1)

    # Recolour the dark (navy) strokes.
    if dark_color:

        target = QColor(dark_color)
        rgb = (target.red() << 16) | (target.green() << 8) | target.blue()

        for y in range(image.height()):
            for x in range(image.width()):

                argb = image.pixel(x, y)
                alpha = (argb >> 24) & 0xFF

                if alpha == 0:
                    continue

                r = (argb >> 16) & 0xFF
                g = (argb >> 8) & 0xFF

                # Navy is dark; the cyan hand has a high green channel.
                if g < 110 and r < 90:
                    image.setPixel(x, y, (alpha << 24) | rgb)

    pixmap = QPixmap.fromImage(image).scaledToHeight(
        height, Qt.SmoothTransformation
    )

    _logo_cache[key] = pixmap

    return pixmap


def chevron_icon(direction, color, size=18):
    """A double chevron (pointing left or right) drawn as a crisp icon."""

    pixmap = QPixmap(size * 2, size * 2)
    pixmap.fill(Qt.transparent)
    pixmap.setDevicePixelRatio(2)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    pen = QPen(QColor(color), 1.8)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)

    s = float(size)
    sign = -1 if direction == "left" else 1

    for offset in (-0.14, 0.14):

        cx = s / 2 + offset * s
        tip = cx + sign * s * 0.13
        back = cx - sign * s * 0.13

        path = QPainterPath()
        path.moveTo(back, s * 0.28)
        path.lineTo(tip, s * 0.5)
        path.lineTo(back, s * 0.72)

        painter.drawPath(path)

    painter.end()

    return QIcon(pixmap)


# ==============================================================
# NAV ICONS
#
# One consistent set of line icons (24 x 24 grid, rounded strokes)
# instead of mixed emoji, drawn in the sidebar's own colours.
# ==============================================================

def _icon_path(name):

    path = QPainterPath()

    if name == "home":
        path.moveTo(4, 11.5); path.lineTo(12, 4.5); path.lineTo(20, 11.5)
        path.moveTo(6.5, 10); path.lineTo(6.5, 19.5); path.lineTo(17.5, 19.5); path.lineTo(17.5, 10)
        path.moveTo(10.5, 19.5); path.lineTo(10.5, 14.5); path.lineTo(13.5, 14.5); path.lineTo(13.5, 19.5)

    elif name == "camera":
        path.addRoundedRect(QRectF(3, 7.5, 18, 12), 3, 3)
        path.moveTo(8.5, 7.5); path.lineTo(10, 5); path.lineTo(14, 5); path.lineTo(15.5, 7.5)
        path.addEllipse(QPointF(12, 13.5), 3.3, 3.3)

    elif name == "presentation":
        path.addRoundedRect(QRectF(3, 4, 18, 12), 2, 2)
        path.moveTo(12, 16); path.lineTo(12, 20)
        path.moveTo(8, 20); path.lineTo(16, 20)
        path.moveTo(10.5, 7.5); path.lineTo(14.5, 10); path.lineTo(10.5, 12.5); path.closeSubpath()

    elif name == "mouse":
        path.addRoundedRect(QRectF(6.5, 3, 11, 18), 5.5, 5.5)
        path.moveTo(12, 3.5); path.lineTo(12, 9)

    elif name == "whiteboard":
        path.addRoundedRect(QRectF(3, 4, 18, 13), 2, 2)
        path.moveTo(8, 17); path.lineTo(6.5, 21)
        path.moveTo(16, 17); path.lineTo(17.5, 21)
        path.moveTo(6.5, 13); path.quadTo(8.5, 7, 11, 10.5); path.quadTo(13.5, 14, 17, 8)

    elif name == "folder":
        path.moveTo(3, 7.5); path.lineTo(3, 18.5)
        path.quadTo(3, 19.5, 4, 19.5); path.lineTo(20, 19.5)
        path.quadTo(21, 19.5, 21, 18.5); path.lineTo(21, 10)
        path.quadTo(21, 9, 20, 9); path.lineTo(12, 9)
        path.lineTo(10, 6.5); path.lineTo(4, 6.5)
        path.quadTo(3, 6.5, 3, 7.5)

    elif name == "settings":
        import math

        def polar(r, deg):
            a = math.radians(deg)
            return 12 + r * math.cos(a), 12 + r * math.sin(a)

        # Gear outline: 8 teeth alternating between two radii.
        points = []
        for k in range(8):
            base = k * 45
            points += [
                polar(6.6, base - 16),
                polar(9.2, base - 9),
                polar(9.2, base + 9),
                polar(6.6, base + 16),
            ]

        path.moveTo(*points[0])
        for point in points[1:]:
            path.lineTo(*point)
        path.closeSubpath()

        path.addEllipse(QPointF(12, 12), 2.8, 2.8)

    elif name == "hand":
        # Four fingers, then the palm and thumb in one stroke.
        path.moveTo(8.5, 12.5); path.lineTo(8.5, 6)
        path.moveTo(11.5, 11); path.lineTo(11.5, 4)
        path.moveTo(14.5, 11); path.lineTo(14.5, 5)
        path.moveTo(17.5, 12); path.lineTo(17.5, 7.5)
        path.lineTo(17.5, 15); path.quadTo(17.5, 20.5, 12.5, 20.5)
        path.lineTo(11.8, 20.5); path.quadTo(9.2, 20.5, 7.6, 18.4)
        path.lineTo(4.9, 14.8); path.quadTo(4.3, 13.6, 5.4, 13.1)
        path.quadTo(6.5, 12.7, 7.4, 13.8); path.lineTo(8.5, 15)
        path.lineTo(8.5, 12.5)

    elif name == "info":
        path.addEllipse(QPointF(12, 12), 8.6, 8.6)
        path.moveTo(12, 11); path.lineTo(12, 16.5)
        path.addEllipse(QPointF(12, 7.9), 0.35, 0.35)

    return path


def nav_icon(name, color, size=22):

    return QIcon(nav_pixmap(name, color, size))


def nav_pixmap(name, color, size=22):

    scale = 2
    pixmap = QPixmap(size * scale, size * scale)
    pixmap.fill(Qt.transparent)
    pixmap.setDevicePixelRatio(scale)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.scale(size / 24.0, size / 24.0)

    pen = QPen(QColor(color), 1.8)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawPath(_icon_path(name))
    painter.end()

    return pixmap


# One open hand in a 0..1 box (wrist, then each finger base -> tip),
# used for the faint constellation under the navigation.
_HAND = {
    "wrist": (0.50, 0.98),
    "thumb": [(0.30, 0.80), (0.16, 0.66), (0.06, 0.55)],
    "index": [(0.36, 0.52), (0.33, 0.30), (0.31, 0.10)],
    "middle": [(0.50, 0.48), (0.50, 0.24), (0.50, 0.00)],
    "ring": [(0.63, 0.51), (0.66, 0.30), (0.68, 0.12)],
    "pinky": [(0.75, 0.58), (0.81, 0.42), (0.86, 0.28)],
}


def draw_constellation(painter, rect, color):
    """Draw a faint hand-landmark constellation centred in `rect`."""

    size = min(rect.width(), rect.height())

    if size < 60:
        return

    ox = rect.center().x() - size / 2
    oy = rect.center().y() - size / 2

    def pt(p):
        return QPointF(ox + p[0] * size, oy + p[1] * size)

    line = QColor(color)
    line.setAlpha(55)
    dot = QColor(color)
    dot.setAlpha(120)

    pen = QPen(line, 1.4)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    wrist = pt(_HAND["wrist"])
    bases = []

    for finger in ("thumb", "index", "middle", "ring", "pinky"):
        points = [pt(q) for q in _HAND[finger]]
        painter.drawLine(wrist, points[0])
        for a, b in zip(points, points[1:]):
            painter.drawLine(a, b)
        bases.append(points[0])

    for a, b in zip(bases[1:], bases[2:]):
        painter.drawLine(a, b)

    painter.setPen(Qt.NoPen)
    painter.setBrush(dot)

    r = max(2.2, size / 60)
    painter.drawEllipse(wrist, r * 1.4, r * 1.4)

    for finger in ("thumb", "index", "middle", "ring", "pinky"):
        for q in _HAND[finger]:
            painter.drawEllipse(pt(q), r, r)


# Rotating tips shown in the card under the navigation.
TIPS = [
    "Close your hand to left click with the virtual mouse.",
    "Touch your thumb and index finger to right click.",
    "Hold the cursor at the top or bottom centre to scroll.",
    "Point right or left to change slides in a presentation.",
    "Keep your palm facing the camera, about an arm's length away.",
]


class BrandArea(QWidget):
    """Logo + collapse button.

    Expanded: logo on the left, collapse button on the right.
    Collapsed: only the logo; hovering over it swaps in an expand
    button to open the sidebar again.
    """

    def __init__(self, sidebar):

        super().__init__(sidebar)

        self.sidebar = sidebar
        self.setFixedHeight(60)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.logo = QLabel()
        self.logo.setObjectName("brandLogo")
        self.logo.setAlignment(Qt.AlignCenter)
        self.logo.setToolTip("GestureBoard")

        self.collapse_button = QPushButton()
        self.collapse_button.setObjectName("sidebarToggle")
        self.collapse_button.setToolTip("Collapse sidebar")
        self.collapse_button.setCursor(Qt.PointingHandCursor)
        self.collapse_button.setFixedSize(34, 34)
        self.collapse_button.setIconSize(QSize(18, 18))
        self.collapse_button.clicked.connect(sidebar.toggle_collapsed)

        self.expand_button = QPushButton()
        self.expand_button.setObjectName("sidebarToggle")
        self.expand_button.setToolTip("Expand sidebar")
        self.expand_button.setCursor(Qt.PointingHandCursor)
        self.expand_button.setFixedSize(44, 44)
        self.expand_button.setIconSize(QSize(20, 20))
        self.expand_button.clicked.connect(sidebar.toggle_collapsed)
        self.expand_button.hide()

        self.layout_ = layout

        layout.addWidget(self.logo)
        layout.addStretch()
        layout.addWidget(self.collapse_button)
        layout.addWidget(self.expand_button)

    def refresh(self, colors):

        collapsed = self.sidebar.collapsed

        self.logo.setPixmap(
            sidebar_logo(42 if collapsed else 56, colors["sidebar_text"])
        )

        self.collapse_button.setIcon(chevron_icon("left", colors["sidebar_text"]))
        self.expand_button.setIcon(chevron_icon("right", colors["sidebar_text"]))

        self.collapse_button.setVisible(not collapsed)
        self.expand_button.hide()
        self.logo.show()

        # Centre the logo in the narrow collapsed bar.
        self.layout_.setAlignment(
            Qt.AlignCenter if collapsed else Qt.AlignLeft | Qt.AlignVCenter
        )

    def enterEvent(self, event):

        if self.sidebar.collapsed:
            self.logo.hide()
            self.expand_button.show()

        super().enterEvent(event)

    def leaveEvent(self, event):

        if self.sidebar.collapsed:
            self.expand_button.hide()
            self.logo.show()

        super().leaveEvent(event)


class Sidebar(QFrame):
    """Left navigation sidebar for GestureBoard dashboard."""

    NAV_ITEMS = [
        ("Home", "home", "showDashboard"),
        ("Camera Setup", "camera", "showCameraSetup"),
        ("Presentation Control", "presentation", "showPresentation"),
        ("Virtual Mouse", "mouse", "showVirtualMouse"),
        ("Whiteboard", "whiteboard", "showWhiteboard"),
        ("Saved Files", "folder", "showSavedFiles"),
        ("Settings", "settings", "showSettings"),
    ]

    # Shorter text for items whose full name does not fit the sidebar.
    SHORT_LABELS = {
        "Presentation Control": "Presentation",
    }

    def __init__(self, main_window, active_page="Home"):
        super().__init__()
        self.main_window = main_window
        self.active_page = active_page
        self.setObjectName("sidebar")
        self._expanded_width = 248
        self._collapsed_width = 72
        self.collapsed = False
        self.setFixedWidth(self._expanded_width)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 16, 18)
        layout.setSpacing(6)
        self._main_layout = layout

        # Brand: logo + collapse / expand button
        self.brand = BrandArea(self)
        layout.addWidget(self.brand)

        layout.addSpacing(26)

        self.nav_buttons = {}
        self._nav_icons = {}
        for key, icon, callback_name in self.NAV_ITEMS:
            btn = QPushButton(self._label(key, icon))
            btn.setToolTip(key)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(46)
            btn.setIconSize(QSize(22, 22))
            if key == active_page:
                btn.setObjectName("active")
            callback = getattr(main_window, callback_name, None)
            if callback:
                btn.clicked.connect(callback)
            self.nav_buttons[key] = btn
            self._nav_icons[key] = icon
            layout.addWidget(btn)

        # Empty space under the navigation: a faint hand constellation is
        # painted here (see paintEvent), with a rotating tip card below it.
        self.decor_space = QWidget()
        self.decor_space.setObjectName("decorSpace")
        self.decor_space.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.decor_space.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.decor_space, 1)

        self.tip_card = QFrame()
        self.tip_card.setObjectName("tipCard")
        tip_layout = QVBoxLayout(self.tip_card)
        tip_layout.setContentsMargins(14, 12, 14, 12)
        tip_layout.setSpacing(4)

        tip_title = QLabel("Gesture tip")
        tip_title.setObjectName("tipTitle")

        self.tip_text = QLabel(TIPS[0])
        self.tip_text.setObjectName("tipText")
        self.tip_text.setWordWrap(True)

        tip_layout.addWidget(tip_title)
        tip_layout.addWidget(self.tip_text)

        layout.addWidget(self.tip_card)
        layout.addSpacing(10)

        self._tip_index = 0
        self._tip_timer = QTimer(self)
        self._tip_timer.timeout.connect(self._next_tip)
        self._tip_timer.start(9000)

        # Status section at bottom
        status_section = QFrame()
        status_section.setObjectName("statusSection")
        status_layout = QVBoxLayout(status_section)
        status_layout.setContentsMargins(4, 12, 0, 0)
        status_layout.setSpacing(6)

        camera_status = QHBoxLayout()
        camera_status.setSpacing(8)
        camera_dot = QLabel("●")
        camera_dot.setObjectName("statusDot")
        self.camera_text = QLabel("No camera selected")
        self.camera_text.setObjectName("statusLabel")
        camera_status.addWidget(camera_dot)
        camera_status.addWidget(self.camera_text)
        camera_status.addStretch()
        status_layout.addLayout(camera_status)

        fps_layout = QHBoxLayout()
        fps_layout.setSpacing(8)
        fps_dot = QLabel("●")
        fps_dot.setObjectName("fpsLabel")
        self.fps_text = QLabel("Virtual Mouse: Off")
        self.fps_text.setObjectName("fpsLabel")
        fps_layout.addWidget(fps_dot)
        fps_layout.addWidget(self.fps_text)
        fps_layout.addStretch()
        status_layout.addLayout(fps_layout)

        layout.addWidget(status_section)

        self.apply_theme()

        # Footer shows the real camera / Virtual Mouse state.
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self.refresh_status)
        self._status_timer.start(1000)
        QTimer.singleShot(0, self.refresh_status)

    def _label(self, key, icon=None):
        return f"  {self.SHORT_LABELS.get(key, key)}"

    def _next_tip(self):
        self._tip_index = (self._tip_index + 1) % len(TIPS)
        self.tip_text.setText(TIPS[self._tip_index])

    def paintEvent(self, event):

        super().paintEvent(event)

        if self.collapsed or not self.decor_space.isVisible():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        area = QRectF(self.decor_space.geometry()).adjusted(14, 10, -14, -6)
        draw_constellation(painter, area, "#22C3DE")

        painter.end()

    def _apply_icons(self):

        from settings import theme as app_theme

        c = app_theme.colors()

        for key, btn in self.nav_buttons.items():
            color = c["accent_text"] if key == self.active_page else c["sidebar_text"]
            btn.setIcon(nav_icon(self._nav_icons[key], color))

    def refresh_status(self):

        win = self.main_window

        name = getattr(win, "active_camera_name", None)

        if getattr(win, "active_camera_index", None) is None:
            name = "No camera selected"

        if self.camera_text.text() != name:
            self.camera_text.setText(name)
            self.camera_text.setToolTip(name)

        vmouse = getattr(win, "virtual_mouse", None)

        if vmouse is not None and getattr(vmouse, "camera_running", False):
            state = "Paused" if getattr(vmouse, "camera_paused", False) else "On"
        else:
            state = "Off"

        text = f"Virtual Mouse: {state}"

        if self.fps_text.text() != text:
            self.fps_text.setText(text)

    # ==========================================================
    # COLLAPSE / EXPAND (responsive)
    # ==========================================================

    def set_collapsed(self, collapsed):
        """Collapse the sidebar to icon-only, or expand it back."""

        collapsed = bool(collapsed)

        if collapsed == self.collapsed:
            return

        self.collapsed = collapsed

        self.setFixedWidth(
            self._collapsed_width
            if collapsed
            else self._expanded_width
        )

        # Tighter margins when collapsed.
        if collapsed:
            self._main_layout.setContentsMargins(10, 18, 10, 14)
        else:
            self._main_layout.setContentsMargins(18, 18, 16, 18)

        # Show/hide the text parts.
        self.camera_text.setVisible(not collapsed)
        self.fps_text.setVisible(not collapsed)
        self.tip_card.setVisible(not collapsed)

        # Show icon-only buttons (with tooltips) when collapsed.
        for key, btn in self.nav_buttons.items():
            icon = self._nav_icons.get(key, "")
            btn.setText("" if collapsed else self._label(key, icon))
            btn.setToolTip(key)

        # Re-apply the stylesheet so alignment/padding update.
        self.apply_theme()

    def toggle_collapsed(self):
        self.set_collapsed(not self.collapsed)

    def _stylesheet(self):

        from settings import theme as app_theme

        c = app_theme.colors()

        align = "center" if self.collapsed else "left"
        pad = "0" if self.collapsed else "0 14px"
        btn_font = "15px"

        return f"""
            QFrame#sidebar {{
                background: {c['sidebar']};
                border-right: 1px solid {c['border']};
            }}
            QLabel {{ background: transparent; color: {c['sidebar_text']}; }}
            QLabel#statusLabel {{ color: {c['sidebar_text']}; font-size: 12px; }}
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 12px;
                color: {c['sidebar_text']};
                text-align: {align};
                padding: {pad};
                font-size: {btn_font};
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
            QPushButton#sidebarToggle {{
                background: transparent;
                text-align: center;
                padding: 0;
                border-radius: 8px;
            }}
            QPushButton#sidebarToggle:hover {{
                background: {c['sidebar_hover']};
            }}
            QFrame#statusSection {{
                background: transparent;
                border: none;
                border-top: 1px solid {c['sidebar_hover']};
                margin-top: 8px;
            }}
            QWidget#decorSpace {{ background: transparent; }}
            QFrame#tipCard {{
                background: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 12px;
            }}
            QLabel#tipTitle {{ color: #22C3DE; font-size: 12px; font-weight: 700; }}
            QLabel#tipText {{ color: {c['sidebar_text']}; font-size: 12px; }}
            QLabel#statusDot {{ color: #22C3DE; font-size: 10px; }}
            QLabel#fpsLabel {{ color: {c['muted']}; font-size: 11px; }}
        """

    def apply_theme(self):

        from settings import theme as app_theme

        self.setStyleSheet(self._stylesheet())

        if hasattr(self, "brand"):
            self.brand.refresh(app_theme.colors())

        if hasattr(self, "nav_buttons"):
            self._apply_icons()

    def setActivePage(self, page_name):
        """Update active navigation item."""
        for key, btn in self.nav_buttons.items():
            btn.setObjectName("active" if key == page_name else "")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.active_page = page_name
        self._apply_icons()


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