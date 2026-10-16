"""Custom title bar: logo, status, light / dark switch and window controls."""

from PyQt5.QtCore import Qt, QPointF, QRectF, QSize, QVariantAnimation
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QAbstractButton, QFrame, QHBoxLayout, QLabel, QPushButton

from settings import theme as app_theme
from widgets.sidebar import sidebar_logo


def _mix(a, b, t):
    return QColor(
        int(a.red() + (b.red() - a.red()) * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue() + (b.blue() - a.blue()) * t),
    )


# ==============================================================
# THEME SWITCH
#
# Pill switch: light mode shows a sun on the left of a pale track,
# dark mode slides the knob right and turns it into a moon, with a
# few stars on the dark track behind it.
# ==============================================================

class ThemeSwitch(QAbstractButton):

    LIGHT_TRACK = QColor("#C9D3E3")
    DARK_TRACK = QColor("#56607A")
    KNOB = QColor("#FFFFFF")
    GLYPH = QColor("#56607A")

    # Star positions on the left of the track (0..1 of width / height)
    # and radius; the moon knob sits on the right in dark mode.
    STARS = [
        (0.40, 0.26, 1.3), (0.24, 0.40, 1.6), (0.12, 0.24, 1.2),
        (0.32, 0.66, 1.2), (0.15, 0.70, 1.5), (0.44, 0.80, 1.0),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(62, 30)
        self.setFocusPolicy(Qt.TabFocus)

        # 0 = light (knob left), 1 = dark (knob right).
        self._t = 0.0

        # Focus ring only for keyboard focus, not focus given on show.
        self._keyboard_focus = False

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(220)
        self._anim.valueChanged.connect(self._set_t)

        self.toggled.connect(self._animate)
        self._update_tooltip()

    def sizeHint(self):
        return QSize(62, 30)

    def focusInEvent(self, event):
        self._keyboard_focus = event.reason() in (Qt.TabFocusReason, Qt.BacktabFocusReason)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self._keyboard_focus = False
        super().focusOutEvent(event)

    def set_dark(self, dark):
        """Set the state without animating or emitting signals."""

        # Already there (e.g. the user just clicked): let the slide finish.
        if self.isChecked() == bool(dark) and self._anim.state() == QVariantAnimation.Running:
            return

        self.blockSignals(True)
        self.setChecked(dark)
        self.blockSignals(False)

        self._anim.stop()
        self._set_t(1.0 if dark else 0.0)
        self._update_tooltip()

    def _set_t(self, value):
        self._t = value
        self.update()

    def _animate(self, checked):
        self._anim.stop()
        self._anim.setStartValue(self._t)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()
        self._update_tooltip()

    def _update_tooltip(self):
        self.setToolTip(
            "Switch to light mode" if self.isChecked() else "Switch to dark mode"
        )

    def paintEvent(self, event):

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        t = self._t
        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
        radius = rect.height() / 2

        # Track
        p.setPen(QPen(QColor(255, 255, 255, 140), 2) if self._keyboard_focus else Qt.NoPen)
        p.setBrush(_mix(self.LIGHT_TRACK, self.DARK_TRACK, t))
        p.drawRoundedRect(rect, radius, radius)

        # Stars fade in with dark mode
        if t > 0:
            star = QColor(255, 255, 255, int(230 * t))
            p.setPen(Qt.NoPen)
            p.setBrush(star)
            for sx, sy, sr in self.STARS:
                p.drawEllipse(
                    QPointF(rect.left() + rect.width() * sx,
                            rect.top() + rect.height() * sy),
                    sr, sr,
                )

        # Knob
        knob_r = radius - 3
        left = rect.left() + 3 + knob_r
        right = rect.right() - 3 - knob_r
        center = QPointF(left + (right - left) * t, rect.center().y())

        p.setPen(Qt.NoPen)
        p.setBrush(self.KNOB)
        p.drawEllipse(center, knob_r, knob_r)

        if t >= 0.5:
            # Moon: a disc with a knob-coloured disc cut out of it.
            p.setBrush(self.GLYPH)
            p.drawEllipse(center, knob_r * 0.62, knob_r * 0.62)
            p.setBrush(self.KNOB)
            p.drawEllipse(
                QPointF(center.x() - knob_r * 0.30, center.y() - knob_r * 0.22),
                knob_r * 0.50, knob_r * 0.50,
            )
        else:
            # Sun: a disc with eight short rays.
            import math

            p.setBrush(self.GLYPH)
            p.drawEllipse(center, knob_r * 0.36, knob_r * 0.36)

            pen = QPen(self.GLYPH, 1.6)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)

            for k in range(8):
                a = math.radians(k * 45)
                p.drawLine(
                    QPointF(center.x() + math.cos(a) * knob_r * 0.56,
                            center.y() + math.sin(a) * knob_r * 0.56),
                    QPointF(center.x() + math.cos(a) * knob_r * 0.76,
                            center.y() + math.sin(a) * knob_r * 0.76),
                )

        p.end()


# ==============================================================
# TITLE BAR
# ==============================================================

class TitleBar(QFrame):
    """Custom title bar with logo, status, theme switch and window controls."""

    HEIGHT = 52

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("titleBar")
        self.setFixedHeight(self.HEIGHT)
        self.setStyleSheet(self._stylesheet())

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(12)

        # Left: Logo + Title
        title_layout = QHBoxLayout()
        title_layout.setSpacing(10)

        self.logo = QLabel()
        self.logo.setFixedHeight(self.HEIGHT - 12)
        self.logo.setAlignment(Qt.AlignCenter)
        title = QLabel("GestureBoard")
        title.setObjectName("titleText")
        title_layout.addWidget(self.logo)
        title_layout.addWidget(title)
        layout.addLayout(title_layout)

        layout.addStretch()

        # Right: Status, theme switch, window controls
        status_label = QLabel("●  System Ready")
        status_label.setObjectName("statusReady")
        layout.addWidget(status_label)

        layout.addSpacing(4)

        self.theme_switch = ThemeSwitch()
        self.theme_switch.toggled.connect(self._on_theme_toggled)
        layout.addWidget(self.theme_switch)

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

        self.apply_theme()

    def _stylesheet(self):

        c = app_theme.colors()

        return f"""
            QFrame#titleBar {{
                background: {c['sidebar']};
                border-bottom: 1px solid {c['border']};
            }}
            QLabel {{ background: transparent; color: {c['sidebar_text']}; }}
            QLabel#titleText {{ font-size: 17px; font-weight: 700; color: {c['sidebar_text']}; }}
            QLabel#statusReady {{ color: {c['sidebar_text']}; font-size: 12px; font-weight: 600; }}
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
                min-width: 40px;
                min-height: 32px;
                font-size: 14px;
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

        c = app_theme.colors()

        self.setStyleSheet(self._stylesheet())

        # logo2's navy "G" is redrawn in the title text colour so it
        # stays visible on the navy bar.
        self.logo.setPixmap(sidebar_logo(self.HEIGHT - 14, c["sidebar_text"]))

        self.theme_switch.set_dark(app_theme.is_dark())

    def _on_theme_toggled(self, dark):

        app_theme.set_theme("Dark" if dark else "Light")

        if hasattr(self.main_window, "apply_theme"):
            self.main_window.apply_theme()

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
