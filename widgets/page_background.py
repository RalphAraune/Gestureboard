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
