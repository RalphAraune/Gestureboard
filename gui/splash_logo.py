"""Animated GestureBoard logo for the splash screen.

A native QPainter port of the HTML/SVG splash animation:
  1. the cyan hand and the navy G are drawn line by line,
  2. the nodes pop in, signal ripples spread from them,
  3. the whole logo gives a small "settle" bounce,
  4. "GestureBoard" rises in letter by letter, then a shine sweeps across,
  5. the tagline fades in and rises into place under the name.

When the animation ends the final frame stays on screen.
"""

import re

from PyQt5.QtCore import Qt, QTimer, QElapsedTimer, QPointF, QRectF, QSize
from PyQt5.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetricsF,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
from PyQt5.QtWidgets import QSizePolicy, QWidget


CYAN = QColor("#22C3DE")
NAVY = QColor("#13234B")

# SVG viewBox="100 85 300 315"
VIEW_X, VIEW_Y, VIEW_W, VIEW_H = 100.0, 85.0, 300.0, 315.0

# Tagline: fades in and rises once the name has landed.
TAGLINE_COLOR = QColor("#4A5679")
TAGLINE_DELAY = 4.15
TAGLINE_DURATION = 0.8

# Total length of the animation in seconds (tagline ends at 4.15 + 0.8).
TOTAL_SECONDS = 4.95

# Vertical spacing (px)
LOGO_NAME_GAP = -14     # logo -> "GestureBoard" (negative: the logo box and the
                        # font both carry empty space of their own)
NAME_TAGLINE_GAP = 2    # "GestureBoard" -> tagline


# ==============================================================
# EASING
# ==============================================================

def cubic_bezier(x1, y1, x2, y2):
    """Return an easing function equal to CSS cubic-bezier(x1,y1,x2,y2)."""

    def bez(t, a, b):
        return 3 * a * (1 - t) ** 2 * t + 3 * b * (1 - t) * t ** 2 + t ** 3

    def ease(p):

        if p <= 0:
            return 0.0

        if p >= 1:
            return 1.0

        # Solve x(t) = p by bisection, then return y(t).
        lo, hi = 0.0, 1.0

        for _ in range(30):

            mid = (lo + hi) / 2

            if bez(mid, x1, x2) < p:
                lo = mid
            else:
                hi = mid

        return bez((lo + hi) / 2, y1, y2)

    return ease


EASE_DRAW = cubic_bezier(.65, 0, .35, 1)
EASE_POP = cubic_bezier(.34, 1.8, .64, 1)
EASE_RISE = cubic_bezier(.2, .8, .2, 1)
EASE_OUT = cubic_bezier(0, 0, .58, 1)
EASE_IN_OUT = cubic_bezier(.42, 0, .58, 1)


def progress(t, delay, duration):
    """Linear 0..1 progress of an animation that starts at `delay`."""

    if t <= delay:
        return 0.0

    return min(1.0, (t - delay) / duration)


# ==============================================================
# SVG PATH PARSER (absolute M, L, C, Q only — all the logo uses)
# ==============================================================

_TOKEN = re.compile(r"[MLCQZ]|-?\d*\.?\d+")


def svg_path(d):

    tokens = _TOKEN.findall(d)
    path = QPainterPath()

    i = 0
    cmd = None

    def num():
        nonlocal i
        value = float(tokens[i])
        i += 1
        return value

    while i < len(tokens):

        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1

        if cmd == "M":
            path.moveTo(num(), num())
            cmd = "L"   # extra pairs after M are line-tos
        elif cmd == "L":
            path.lineTo(num(), num())
        elif cmd == "C":
            path.cubicTo(num(), num(), num(), num(), num(), num())
        elif cmd == "Q":
            path.quadTo(num(), num(), num(), num())
        elif cmd == "Z":
            path.closeSubpath()
        else:
            i += 1

    return path


# ==============================================================
# LOGO DATA  (path, colour, delay, duration) — copied from the SVG
# ==============================================================

LINES = [
    # ----- Hand (cyan) -----
    # middle finger
    ("M233,234 C236,170 240,104 250,104 C258,104 256,220 250,326", CYAN, .15, .9),
    # index finger
    ("M201,247 L172,136 Q176,124 182,133 L233,234", CYAN, .30, .9),
    # outer finger
    ("M178,270 L125,190 L201,247", CYAN, .45, .9),
    # veins converging on the palm node
    ("M125,190 L250,326", CYAN, .70, .7),
    ("M201,247 L250,326", CYAN, .80, .6),
    ("M233,234 L250,326", CYAN, .85, .6),
    ("M265,229 L250,326", CYAN, .90, .6),
    ("M250,326 L250,382", CYAN, 1.20, .4),
    # thumb
    ("M265,229 C270,190 290,163 322,161 C344,160 360,170 369,181", CYAN, .60, .9),
    # palm outline
    ("M178,270 C180,325 188,352 214,368 C236,377 245,382 250,382 "
     "C290,382 330,330 352,294 C367,276 373,258 374,234", CYAN, .75, 1.1),
    # inner palm line + inner thumb arc
    ("M250,326 L278,226 C281,200 296,178 320,175 C340,173 354,180 361,190", CYAN, .95, .8),
    # G outline (outer)
    ("M322,234 L374,234", CYAN, 1.25, .5),
    # G outline (inner)
    ("M250,326 C276,318 312,304 338,289 C356,278 362,262 363,246 L331,246", CYAN, 1.10, .9),
    ("M322,234 L322,257 L346,257", CYAN, 1.45, .4),

    # ----- G (navy) -----
    ("M369,181 L352,202 C340,186 314,186 306,200 C300,215 297,250 294,277 "
     "C306,291 332,286 341,270 L347,257", NAVY, 1.75, 1.0),
]

NODES = [
    # (cx, cy, r, colour, delay)
    (250, 104, 7, CYAN, 1.35),
    (176, 128, 7, CYAN, 1.40),
    (125, 190, 7, CYAN, 1.45),
    (201, 247, 7, CYAN, 1.50),
    (233, 234, 7, CYAN, 1.55),
    (265, 229, 7, CYAN, 1.60),
    (178, 270, 7, CYAN, 1.65),
    (250, 382, 7, CYAN, 1.70),
    (250, 326, 9, CYAN, 1.75),
    (369, 181, 7, CYAN, 1.80),
    (322, 234, 7, CYAN, 1.85),
    (374, 234, 7, CYAN, 1.90),
    (352, 201, 7, NAVY, 2.50),
    (294, 277, 7, NAVY, 2.60),
]

RIPPLES = [
    # (cx, cy, r, delay)
    (250, 326, 9, 2.75),
    (250, 104, 7, 2.90),
    (176, 128, 7, 2.95),
    (125, 190, 7, 3.00),
    (369, 181, 7, 3.05),
]

NAME = "GestureBoard"
NAME_SPLIT = 7          # "Gesture" navy, "Board" cyan


class AnimatedLogo(QWidget):

    def __init__(self, parent=None, background="#EEF2F7", tagline=""):

        super().__init__(parent)

        self.background = QColor(background)
        self.tagline = tagline

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Pre-build each stroke as a polyline sampled by arc length, so a
        # partially drawn stroke is just the first N points.
        self.strokes = []

        for d, color, delay, duration in LINES:

            path = svg_path(d)
            length = path.length()
            steps = max(12, int(length / 2))

            points = [
                path.pointAtPercent(path.percentAtLength(length * k / steps))
                for k in range(steps + 1)
            ]

            self.strokes.append((points, color, delay, duration))

        families = QFontDatabase().families()

        self.font_family = "Outfit" if "Outfit" in families else "Segoe UI"

        self.clock = QElapsedTimer()
        self.t = 0.0
        self.started = False

        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._tick)

        self.logo_width = 260

    # ----------------------------------------------------------
    # PUBLIC
    # ----------------------------------------------------------

    def start(self):
        """Play the animation from the beginning."""

        self.t = 0.0
        self.started = True
        self.clock.start()
        self.timer.start()
        self.update()

    def finish(self):
        """Jump to the final frame (logo fully drawn)."""

        self.timer.stop()
        self.started = True
        self.t = TOTAL_SECONDS
        self.update()

    def set_logo_width(self, width):

        self.logo_width = max(120, int(width))
        self.updateGeometry()
        self.setMinimumHeight(self.sizeHint().height())
        self.update()

    # ----------------------------------------------------------
    # SIZE
    # ----------------------------------------------------------

    def _name_px(self):

        return max(32, min(100, int(self.logo_width * 0.22)))

    def _tagline_px(self):

        return max(16, min(28, int(self.logo_width * 0.06)))

    def _tagline_block(self):
        """Height reserved for the tagline (gap + line)."""

        if not self.tagline:
            return 0

        return int(NAME_TAGLINE_GAP + self._tagline_px() * 1.5)

    def sizeHint(self):

        logo_h = self.logo_width * VIEW_H / VIEW_W

        return QSize(
            int(self.logo_width * 1.9),
            int(
                logo_h + LOGO_NAME_GAP + self._name_px() * 1.4 + 6
                + self._tagline_block()
            )
        )

    def minimumSizeHint(self):

        return self.sizeHint()

    # ----------------------------------------------------------
    # TIMER
    # ----------------------------------------------------------

    def _tick(self):

        self.t = self.clock.elapsed() / 1000.0

        if self.t >= TOTAL_SECONDS:

            self.t = TOTAL_SECONDS
            self.timer.stop()

        self.update()

    # ----------------------------------------------------------
    # PAINT
    # ----------------------------------------------------------

    def paintEvent(self, event):

        if not self.started:
            return

        t = self.t

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        logo_w = float(self.logo_width)
        logo_h = logo_w * VIEW_H / VIEW_W

        left = (self.width() - logo_w) / 2.0
        top = 6.0

        self._paint_logo(painter, t, QRectF(left, top, logo_w, logo_h))
        name_bottom = self._paint_name(
            painter, t, top + logo_h + LOGO_NAME_GAP
        )

        if self.tagline:
            self._paint_tagline(painter, t, name_bottom + NAME_TAGLINE_GAP)

        painter.end()

    def _paint_logo(self, painter, t, box):

        scale = box.width() / VIEW_W

        painter.save()

        # Whole-logo settle: 1 -> 1.04 (at 40%) -> 1, from 2.75 s for 0.7 s
        p = progress(t, 2.75, 0.7)

        if 0 < p < 1:

            if p < 0.4:
                s = 1 + 0.04 * EASE_OUT(p / 0.4)
            else:
                s = 1.04 - 0.04 * EASE_OUT((p - 0.4) / 0.6)

            c = box.center()
            painter.translate(c)
            painter.scale(s, s)
            painter.translate(-c)

        # Map SVG viewBox coordinates into the box.
        painter.translate(box.left(), box.top())
        painter.scale(scale, scale)
        painter.translate(-VIEW_X, -VIEW_Y)

        # ----- strokes -----
        for points, color, delay, duration in self.strokes:

            amount = EASE_DRAW(progress(t, delay, duration))

            if amount <= 0:
                continue

            count = max(2, int(round(amount * (len(points) - 1))) + 1)

            pen = QPen(color, 5)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)

            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawPolyline(QPolygonF(points[:count]))

        # ----- nodes -----
        painter.setPen(Qt.NoPen)

        for cx, cy, r, color, delay in NODES:

            s = EASE_POP(progress(t, delay, 0.4))

            if s <= 0:
                continue

            painter.setBrush(color)
            painter.drawEllipse(QPointF(cx, cy), r * s, r * s)

        # ----- ripples -----
        painter.setBrush(Qt.NoBrush)

        for cx, cy, r, delay in RIPPLES:

            p = progress(t, delay, 1.0)

            if p <= 0 or p >= 1:
                continue

            e = EASE_OUT(p)

            ripple = QColor(CYAN)
            ripple.setAlphaF(0.8 * (1 - e))

            grow = 1 + 2.2 * e

            # The SVG scales the stroke with the circle.
            painter.setPen(QPen(ripple, 2 * grow))
            painter.drawEllipse(QPointF(cx, cy), r * grow, r * grow)

        painter.restore()

    def _paint_name(self, painter, t, top):

        font = QFont(self.font_family)
        font.setPixelSize(self._name_px())
        font.setWeight(QFont.Bold)
        font.setLetterSpacing(QFont.PercentageSpacing, 99)

        metrics = QFontMetricsF(font)

        line_h = metrics.height()
        total_w = metrics.horizontalAdvance(NAME)

        clip = QRectF(
            (self.width() - total_w) / 2.0 - 4,
            top,
            total_w + 8,
            line_h + 6
        )

        # The name is drawn into its own transparent layer, so the shine
        # can be applied to the letters only (not the background).
        dpr = self.devicePixelRatioF()

        layer = QImage(
            int(clip.width() * dpr) + 1,
            int(clip.height() * dpr) + 1,
            QImage.Format_ARGB32_Premultiplied
        )
        layer.setDevicePixelRatio(dpr)
        layer.fill(Qt.transparent)

        lp = QPainter(layer)
        lp.setRenderHint(QPainter.Antialiasing)
        lp.setRenderHint(QPainter.TextAntialiasing)
        lp.setFont(font)

        x = 4.0
        baseline = metrics.ascent()

        for i, ch in enumerate(NAME):

            p = EASE_RISE(progress(t, 3.0 + i * 0.045, 0.6))

            advance = metrics.horizontalAdvance(ch)

            if p > 0:

                color = QColor(NAVY if i < NAME_SPLIT else CYAN)
                color.setAlphaF(min(1.0, p))

                offset = (1 - p) * line_h * 1.1

                lp.setPen(color)
                lp.drawText(QPointF(x, baseline + offset), ch)

            x += advance

        # ----- shine sweep (only where the letters are) -----
        p = progress(t, 4.05, 0.7)

        if 0 < p < 1:

            e = EASE_IN_OUT(p)

            width = clip.width()

            band_w = width * 0.30
            band_x = width * (-0.40 + 1.60 * e)

            grad = QLinearGradient(band_x, 0, band_x + band_w, 0)

            shine = QColor(255, 255, 255, 0)
            grad.setColorAt(0.0, shine)
            shine.setAlpha(int(255 * 0.85))
            grad.setColorAt(0.5, shine)
            shine.setAlpha(0)
            grad.setColorAt(1.0, shine)

            lp.setCompositionMode(QPainter.CompositionMode_SourceAtop)
            lp.fillRect(
                QRectF(band_x, 0, band_w, clip.height()),
                grad
            )

        lp.end()

        painter.drawImage(clip.topLeft(), layer)

        return clip.bottom()

    def _paint_tagline(self, painter, t, top):

        p = progress(t, TAGLINE_DELAY, TAGLINE_DURATION)

        if p <= 0:
            return

        e = EASE_RISE(p)

        font = QFont("Segoe UI")
        font.setPixelSize(self._tagline_px())
        font.setLetterSpacing(QFont.PercentageSpacing, 101)

        painter.save()
        painter.setFont(font)

        metrics = QFontMetricsF(font)

        color = QColor(TAGLINE_COLOR)
        color.setAlphaF(min(1.0, e))
        painter.setPen(color)

        # Rises 14 px into place while fading in.
        offset = (1 - e) * 14

        rect = QRectF(0, top + offset, self.width(), metrics.height() * 1.4)

        painter.drawText(rect, Qt.AlignHCenter | Qt.AlignTop, self.tagline)

        painter.restore()
