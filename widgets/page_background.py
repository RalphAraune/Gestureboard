"""Shared page background: soft blue surface, dot grid and hand outline.

Saved Files introduced this look; every main page now paints it so the
app reads as one surface. A page calls `paint_page_background(self)` from
its paintEvent and `clear_layers(self)` once its widgets exist, so plain
container widgets let the background show through.
"""

from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import QScrollArea, QSplitter, QStackedWidget, QWidget

from settings import theme as app_theme
from widgets.sidebar import draw_constellation


# Soft blue page instead of near-white, with cards one step lighter.
LIGHT_SURFACES = {
    "bg": "#D9E6F4",
    "card": "#EAF2FB",
    "card_border": "#BED2E9",
    "input_bg": "#EAF2FB",
    "input_border": "#AAC0E1",
    "button_hover": "#C9DAEE",
    "decor": "#0E2F76",
    "grid_alpha": 34,
}

DARK_SURFACES = {
    "card_border": "#27496E",
    "decor": "#3E7CF7",
    "grid_alpha": 40,
}

# Stylesheet rule a page adds so `clear_layers` containers stay see-through.
LAYER_RULE = """
    [pageLayer="true"] {
        background: transparent;
        border: none;
    }
"""


def page_colors():
    """App theme colours with the shared page surfaces applied."""

    c = dict(app_theme.colors())
    c.update(DARK_SURFACES if app_theme.is_dark() else LIGHT_SURFACES)
    return c


def paint_page_background(widget, colors=None, hand=True):
    """Fill `widget` with the page colour, dot grid and hand outline."""

    c = colors or page_colors()

    painter = QPainter(widget)
    painter.setRenderHint(QPainter.Antialiasing)

    painter.fillRect(widget.rect(), QColor(c["bg"]))

    # Dot grid
    dot = QColor(c["decor"])
    dot.setAlpha(c["grid_alpha"])
    painter.setPen(Qt.NoPen)
    painter.setBrush(dot)

    spacing = 24
    for x in range(spacing // 2, widget.width(), spacing):
        for y in range(spacing // 2, widget.height(), spacing):
            painter.drawEllipse(QPointF(x, y), 1.1, 1.1)

    # Hand constellation, partly tucked past the bottom-right corner
    if hand:
        size = max(260, min(widget.width(), widget.height()) * 0.62)
        area = QRectF(
            widget.width() - size * 0.78,
            widget.height() - size * 0.82,
            size,
            size,
        )

        painter.save()
        painter.setOpacity(0.55)
        painter.translate(area.center())
        painter.rotate(-14)
        painter.translate(-area.center())
        draw_constellation(painter, area, c["decor"])
        painter.restore()

    painter.end()


def clear_layers(root):
    """Mark plain containers under `root` so they don't hide the background.

    Only bare QWidgets, scroll areas (and their viewports), splitters and
    stacks are touched; styled frames, buttons and inputs keep their look.
    """

    for widget in [root] + root.findChildren(QWidget):

        if widget is root or widget.isWindow():
            continue

        if type(widget) is QWidget or isinstance(
            widget, (QScrollArea, QSplitter, QStackedWidget)
        ):
            widget.setProperty("pageLayer", True)
            widget.setAutoFillBackground(False)

        if isinstance(widget, QScrollArea):
            viewport = widget.viewport()
            viewport.setProperty("pageLayer", True)
            viewport.setAutoFillBackground(False)


_arrow_cache = {}


def combo_arrow_url(color):
    """Path to a small down-chevron PNG in `color`, for QComboBox::down-arrow.

    Qt stylesheets can only draw arrows from image files, so the chevron is
    rendered once per colour into the temp folder.
    """

    if color in _arrow_cache:
        return _arrow_cache[color]

    import tempfile
    from pathlib import Path

    from PyQt5.QtGui import QImage, QPainterPath, QPen

    image = QImage(24, 24, QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 2.4)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)

    path = QPainterPath()
    path.moveTo(6, 9)
    path.lineTo(12, 15)
    path.lineTo(18, 9)
    painter.drawPath(path)
    painter.end()

    name = "gestureboard_arrow_" + color.lstrip("#") + ".png"
    target = Path(tempfile.gettempdir()) / name
    image.save(str(target))

    url = target.as_posix()
    _arrow_cache[color] = url

    return url


def combo_rules(c, field=None):
    """Shared QComboBox styling: rounded field and a themed chevron."""

    field = field or c["input_bg"]

    return f"""
        QComboBox {{
            background: {field};
            color: {c['text']};
            border: 1px solid {c['input_border']};
            border-radius: 9px;
            padding: 7px 12px;
            font-size: 13px;
            min-height: 22px;
        }}

        QComboBox:hover,
        QComboBox:focus {{
            border: 1px solid {c['primary']};
        }}

        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: center right;
            border: none;
            width: 28px;
        }}

        QComboBox::down-arrow {{
            image: url("{combo_arrow_url(c['text_secondary'])}");
            width: 14px;
            height: 14px;
        }}

        QComboBox QAbstractItemView {{
            background: {field};
            color: {c['text']};
            border: 1px solid {c['input_border']};
            selection-background-color: {c['button_hover']};
            selection-color: {c['text']};
            outline: none;
            padding: 4px;
        }}
    """
