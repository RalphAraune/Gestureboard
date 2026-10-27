"""Floating annotation circle shown over the slides while presenting.

A small round button floats over the slide preview, or over the full
screen view while that is open. Drag it anywhere; tap it to open the
drawing tools beside it, tap again to close them. It draws into a
shared SlideInk.

Both parts are always dark, like a presenter remote, so they read on
light and dark slides alike, and the buttons are large enough to hit
with the hand cursor (a closed fist taps, index + middle together drags).
"""

from PyQt5.QtCore import QEvent, QPoint, QPointF, QRect, QRectF, QSize, Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QToolButton,
    QWidget,
)

from gui.whiteboard import tool_pixmap


# Ink colours: bright enough to read on most slides, plus ink black
# and white for dark slides.
COLORS = [
    ("#E81123", "Red"),
    ("#FFB020", "Yellow"),
    ("#28C76F", "Green"),
    ("#2876E8", "Blue"),
    ("#172033", "Black"),
    ("#FFFFFF", "White"),
]

# Brush sizes (on-screen pixels) as three fixed choices: easier to
# pick with the hand cursor than dragging a slider.
SIZES = [
    (3, "Fine"),
    (6, "Medium"),
    (11, "Bold"),
]

BAR_BG = "rgba(12, 24, 44, 238)"
BAR_EDGE = "rgba(255, 255, 255, 30)"
TEXT = "#C9D6EA"
ICON = "#C9D6EA"
SELECTED_BG = "#F5FEFF"
SELECTED_FG = "#0E2F76"
HOVER = "rgba(255, 255, 255, 22)"
DANGER = "#FF8A80"
DANGER_FILL = "#D9483B"

# Space kept between the circle / tools and the edge of what they
# float over, and between the circle and its tools.
EDGE_GAP = 16
PANEL_GAP = 12

# Diameter of the floating circle.
CIRCLE = 60

# Movement (pixels) before a press on the circle becomes a drag.
DRAG_START = 6

# Below this parent width the tool names are hidden to save space.
COMPACT_WIDTH = 820


def _dot_icon(diameter, color, size=24):

    pixmap = QPixmap(size * 2, size * 2)
    pixmap.fill(Qt.transparent)
    pixmap.setDevicePixelRatio(2)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(color))
    painter.drawEllipse(QPointF(size / 2, size / 2), diameter / 2, diameter / 2)
    painter.end()

    return pixmap


def _shadow(widget):

    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(28)
    shadow.setOffset(0, 8)
    shadow.setColor(QColor(0, 0, 0, 120))
    widget.setGraphicsEffect(shadow)


# ============================================================
# TOOLS PANEL  (opens beside the circle)
# ============================================================

class InkPanel(QFrame):

    def __init__(self, ink, circle, parent=None):
        super().__init__(parent)

        self.ink = ink
        self.circle = circle
        self._compact = None

        self.setObjectName("inkBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        _shadow(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(4)

        self._labelled = []

        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)
        self.tool_buttons = {}

        for tool, label, tip in (
            ("pen", "Pen", "Pen"),
            ("highlighter", "Marker", "Highlighter"),
            ("eraser", "Eraser", "Erase drawing, not the slide"),
        ):
            button = self._tool_button(tool, label, tip)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, t=tool: self.set_tool(t))
            self.tool_group.addButton(button)
            self.tool_buttons[tool] = button
            layout.addWidget(button)

        layout.addWidget(self._divider())

        self.color_group = QButtonGroup(self)
        self.color_group.setExclusive(True)
        self.color_buttons = {}

        for color, name in COLORS:
            swatch = QToolButton()
            swatch.setObjectName("swatch")
            swatch.setCheckable(True)
            swatch.setFixedSize(30, 30)
            swatch.setCursor(Qt.PointingHandCursor)
            swatch.setToolTip(name)
            swatch.setStyleSheet(
                f"QToolButton#swatch {{ background: {color}; }}"
                f"QToolButton#swatch:checked {{ background: {color}; }}"
            )
            swatch.clicked.connect(lambda checked=False, c=color: self.set_color(c))
            self.color_group.addButton(swatch)
            self.color_buttons[QColor(color).name()] = swatch
            layout.addWidget(swatch)

        layout.addWidget(self._divider())

        self.size_group = QButtonGroup(self)
        self.size_group.setExclusive(True)
        self.size_buttons = {}

        for size, name in SIZES:
            button = QToolButton()
            button.setObjectName("sizeButton")
            button.setCheckable(True)
            button.setFixedSize(34, 34)
            button.setCursor(Qt.PointingHandCursor)
            button.setToolTip(f"{name} line")
            # Dots grow with the line, big enough to tell apart.
            dot = 4 + size
            icon = QIcon()
            icon.addPixmap(_dot_icon(dot, ICON), QIcon.Normal, QIcon.Off)
            icon.addPixmap(_dot_icon(dot, SELECTED_FG), QIcon.Normal, QIcon.On)
            button.setIcon(icon)
            button.setIconSize(QSize(24, 24))
            button.clicked.connect(lambda checked=False, s=size: self.set_size(s))
            self.size_group.addButton(button)
            self.size_buttons[size] = button
            layout.addWidget(button)

        layout.addWidget(self._divider())

        undo = self._tool_button("undo", "Undo", "Undo the last stroke")
        undo.clicked.connect(ink.undo)
        layout.addWidget(undo)

        redo = self._tool_button("redo", "Redo", "Bring back the last undone stroke")
        redo.clicked.connect(ink.redo)
        layout.addWidget(redo)

        self.clear_button = self._tool_button(
            "clear", "Clear", "Clear this slide's drawing\n"
            "Gesture: wave your open hand ✋ side to side",
            danger=True,
        )
        self.clear_button.clicked.connect(ink.clear_slide)
        layout.addWidget(self.clear_button)

        # Every button rule is scoped under #inkBar so it outranks the
        # transparent background given to the panel's plain containers.
        self.setStyleSheet(f"""
            QFrame#inkBar {{
                background: {BAR_BG};
                border: 1px solid {BAR_EDGE};
                border-radius: 18px;
            }}

            QFrame#inkBar QWidget {{
                background: transparent;
                font-family: "Segoe UI";
            }}

            QFrame#inkBar QToolButton {{
                border: none;
                border-radius: 11px;
                color: {TEXT};
                font-size: 11px;
                font-weight: 600;
            }}

            QFrame#inkBar QToolButton:hover {{
                background: {HOVER};
            }}

            QFrame#inkBar QToolButton:checked {{
                background: {SELECTED_BG};
                color: {SELECTED_FG};
            }}

            QFrame#inkBar QToolButton:focus {{
                outline: none;
            }}

            QFrame#inkBar QToolButton#danger {{
                color: {DANGER};
            }}

            QFrame#inkBar QToolButton#danger:hover {{
                background: rgba(255, 138, 128, 40);
            }}

            QFrame#inkBar QToolButton#swatch {{
                border: 2px solid rgba(255, 255, 255, 50);
                border-radius: 15px;
            }}

            QFrame#inkBar QToolButton#swatch:hover {{
                border: 2px solid rgba(255, 255, 255, 150);
            }}

            QFrame#inkBar QToolButton#swatch:checked {{
                border: 3px solid {SELECTED_BG};
            }}

            QFrame#inkBar QToolButton#sizeButton {{
                border-radius: 17px;
            }}

            QFrame#inkBar QFrame#barDivider {{
                background: rgba(255, 255, 255, 30);
            }}
        """)

        self._clear_style = self.clear_button.styleSheet()

        # Show what the ink is already set to.
        self.tool_buttons[ink.tool].setChecked(True)
        self._pick_color_button(ink.color.name())
        closest = min(SIZES, key=lambda s: abs(s[0] - ink.brush_size))[0]
        self.size_buttons[closest].setChecked(True)
        self.set_size(closest)

        self.hide()

    # --------------------------------------------------------

    def _tool_button(self, icon, label, tip, danger=False):

        button = QToolButton()
        button.setObjectName("danger" if danger else "tool")
        button.setText(label)
        button.setToolTip(tip)
        button.setCursor(Qt.PointingHandCursor)
        button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        button.setFixedSize(54, 52)
        button.setIconSize(QSize(24, 24))

        idle = DANGER if danger else ICON
        qicon = QIcon()
        qicon.addPixmap(tool_pixmap(icon, idle, 24), QIcon.Normal, QIcon.Off)
        qicon.addPixmap(tool_pixmap(icon, SELECTED_FG, 24), QIcon.Normal, QIcon.On)
        button.setIcon(qicon)

        self._labelled.append(button)
        return button

    def _divider(self):

        line = QFrame()
        line.setObjectName("barDivider")
        line.setFixedSize(1, 30)

        holder = QWidget()
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.addWidget(line, 0, Qt.AlignVCenter)
        return holder

    def apply_compact(self, compact):
        """Hide the tool names when there is little room."""

        if compact == self._compact:
            return

        self._compact = compact

        for button in self._labelled:
            button.setToolButtonStyle(
                Qt.ToolButtonIconOnly if compact else Qt.ToolButtonTextUnderIcon
            )
            button.setFixedSize(QSize(40, 40) if compact else QSize(54, 52))

        self.adjustSize()

    # --------------------------------------------------------
    # CHOICES
    # --------------------------------------------------------

    def set_tool(self, tool):

        self.ink.end_stroke()
        self.ink.tool = tool
        self.tool_buttons[tool].setChecked(True)
        self.circle.update()

    def set_color(self, color):

        self.ink.color = QColor(color)
        self._pick_color_button(color)

        # Picking a colour while erasing means "draw with this".
        if self.ink.tool == "eraser":
            self.set_tool("pen")

        self.circle.update()

    def set_size(self, size):

        self.ink.brush_size = size

    def _pick_color_button(self, color):

        button = self.color_buttons.get(QColor(color).name())
        if button is not None:
            button.setChecked(True)

    # --------------------------------------------------------

    def set_clear_progress(self, fraction):
        """Fill the Clear button while the open hand is being waved."""

        if fraction <= 0:
            self.clear_button.setText("Clear")
            self.clear_button.setStyleSheet(self._clear_style)
            return

        f = min(1.0, fraction)
        self.clear_button.setText("Hold" if f < 1 else "Cleared")
        self.clear_button.setStyleSheet(
            "QToolButton#danger, QToolButton#danger:hover {"
            " color: #FFFFFF;"
            " background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            f" stop:0 {DANGER_FILL}, stop:{f:.3f} {DANGER_FILL},"
            f" stop:{min(1.0, f + 0.001):.3f} rgba(255, 138, 128, 40),"
            " stop:1 rgba(255, 138, 128, 40)); }"
        )


# ============================================================
# FLOATING CIRCLE
# ============================================================

class FloatingAnnotationBar(QWidget):
    """The floating circle; owns the tools panel that opens beside it.

    Kept under its old name: Presentation Control attaches it to the
    preview or the full screen view and shows or hides it.
    """

    def __init__(self, ink, parent=None):
        super().__init__(parent)

        self.ink = ink

        self.setFixedSize(CIRCLE + 8, CIRCLE + 8)
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip("Tap for drawing tools, drag to move")
        _shadow(self)

        self.panel = InkPanel(ink, self, parent)

        # Where the circle sits, as a fraction of the free space in the
        # parent: (1.0, 1.0) is the bottom right corner. Kept while
        # dragging and across the move between preview and full screen.
        self._anchor = (1.0, 1.0)
        self._press = None
        self._dragging = False
        self._clear_progress = 0.0
        self._watched = None
        self._hover = False

        ink.changed.connect(self.update)

        self.hide()

    # --------------------------------------------------------
    # PROXIES  (the tools live on the panel)
    # --------------------------------------------------------

    @property
    def clear_button(self):
        return self.panel.clear_button

    def set_tool(self, tool):
        self.panel.set_tool(tool)

    def set_color(self, color):
        self.panel.set_color(color)

    def set_size(self, size):
        self.panel.set_size(size)

    def panel_open(self):
        return self.panel.isVisible()

    def set_panel_open(self, open_):

        self.panel.setVisible(bool(open_) and self.isVisible())
        self.place()
        self.update()

    # Older name: "collapsed" now means the tools are closed.
    def set_collapsed(self, collapsed):
        self.set_panel_open(not collapsed)

    def setVisible(self, visible):

        super().setVisible(visible)

        if not visible:
            self.panel.hide()

    def raise_(self):

        super().raise_()
        self.panel.raise_()

    # --------------------------------------------------------
    # HOLD-TO-CLEAR FEEDBACK
    # --------------------------------------------------------

    def set_clear_progress(self, fraction):
        """Shown as a red ring filling around the circle, and on the
        panel's Clear button when the tools are open."""

        self._clear_progress = max(0.0, min(1.0, fraction))
        self.panel.set_clear_progress(fraction)
        self.update()

    # --------------------------------------------------------
    # PAINT
    # --------------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(4, 4, CIRCLE, CIRCLE)
        ink = QColor(self.ink.color)

        # Dark disc
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.setBrush(QColor(12, 24, 44, 245 if self._hover else 235))
        painter.drawEllipse(rect)

        # Ring in the current ink colour (light outline keeps black
        # ink visible on the dark disc).
        ring = rect.adjusted(3, 3, -3, -3)
        if ink.lightness() < 60:
            painter.setPen(QPen(QColor(255, 255, 255, 90), 4))
            painter.drawEllipse(ring)
        painter.setPen(QPen(ink, 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(ring)

        # Open: the inner disc turns white, like a selected tool.
        if self.panel_open():
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(SELECTED_BG))
            painter.drawEllipse(rect.adjusted(9, 9, -9, -9))

        # Tool icon in the middle.
        icon_color = SELECTED_FG if self.panel_open() else SELECTED_BG
        size = 26
        pixmap = tool_pixmap(self.ink.tool, icon_color, size)
        painter.drawPixmap(
            QRect(
                int(rect.center().x() - size / 2),
                int(rect.center().y() - size / 2),
                size,
                size,
            ),
            pixmap,
        )

        # Wave to clear: the inside fills red clockwise from the top
        # (a filled pie reads even when the ink ring is red too).
        if self._clear_progress > 0:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(DANGER_FILL))
            painter.drawPie(
                rect.adjusted(9, 9, -9, -9),
                90 * 16,
                -int(360 * 16 * self._clear_progress),
            )
            painter.drawPixmap(
                QRect(
                    int(rect.center().x() - size / 2),
                    int(rect.center().y() - size / 2),
                    size,
                    size,
                ),
                tool_pixmap("clear", "#FFFFFF", size),
            )

        painter.end()

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    # --------------------------------------------------------
    # TAP AND DRAG
    # --------------------------------------------------------

    def mousePressEvent(self, event):

        if event.button() != Qt.LeftButton:
            return

        self._press = (event.globalPos(), self.pos())
        self._dragging = False

    def mouseMoveEvent(self, event):

        if self._press is None or not (event.buttons() & Qt.LeftButton):
            return

        start_global, start_pos = self._press
        delta = event.globalPos() - start_global

        if not self._dragging and delta.manhattanLength() < DRAG_START:
            return

        if not self._dragging:
            self._dragging = True
            self.setCursor(Qt.ClosedHandCursor)

        self._move_to(start_pos + delta)

    def mouseReleaseEvent(self, event):

        if event.button() != Qt.LeftButton or self._press is None:
            return

        if not self._dragging:
            self.set_panel_open(not self.panel_open())

        self._press = None
        self._dragging = False
        self.setCursor(Qt.OpenHandCursor)

    def _move_to(self, top_left):

        parent = self.parentWidget()

        if parent is None:
            return

        free_w = max(1, parent.width() - self.width() - 2 * EDGE_GAP)
        free_h = max(1, parent.height() - self.height() - 2 * EDGE_GAP)

        self._anchor = (
            min(1.0, max(0.0, (top_left.x() - EDGE_GAP) / free_w)),
            min(1.0, max(0.0, (top_left.y() - EDGE_GAP) / free_h)),
        )
        self.place()

    # --------------------------------------------------------
    # PLACEMENT
    # --------------------------------------------------------

    def attach(self, parent):
        """Float over `parent` (the preview or the full screen view)."""

        if self._watched is not None:
            try:
                self._watched.removeEventFilter(self)
            except RuntimeError:
                pass

        visible = self.isVisible()
        open_ = self.panel.isVisible()

        self.setParent(parent)
        self.panel.setParent(parent)
        self._watched = parent
        parent.installEventFilter(self)

        self.setVisible(visible)
        self.panel.setVisible(visible and open_)
        self.place()
        self.raise_()

    def eventFilter(self, watched, event):

        if watched is self._watched and event.type() == QEvent.Resize:
            self.place()

        return super().eventFilter(watched, event)

    def place(self):

        parent = self.parentWidget()

        if parent is None:
            return

        free_w = max(0, parent.width() - self.width() - 2 * EDGE_GAP)
        free_h = max(0, parent.height() - self.height() - 2 * EDGE_GAP)

        fx, fy = self._anchor
        self.move(int(EDGE_GAP + free_w * fx), int(EDGE_GAP + free_h * fy))

        self._place_panel()

    def _place_panel(self):
        """Open the tools beside the circle, on the side with room;
        above or below it when neither side is wide enough."""

        parent = self.parentWidget()
        panel = self.panel

        if parent is None or not panel.isVisible():
            return

        panel.apply_compact(parent.width() < COMPACT_WIDTH)
        panel.adjustSize()

        circle = self.geometry()
        pw, ph = panel.width(), panel.height()

        left_room = circle.left() - PANEL_GAP - EDGE_GAP
        right_room = parent.width() - circle.right() - PANEL_GAP - EDGE_GAP

        y = circle.center().y() - ph // 2

        if right_room >= pw and right_room >= left_room:
            x = circle.right() + PANEL_GAP
        elif left_room >= pw:
            x = circle.left() - PANEL_GAP - pw
        else:
            # Not enough room either side: above the circle, or below
            # it near the top edge.
            x = circle.center().x() - pw // 2
            if circle.top() - PANEL_GAP - ph >= EDGE_GAP:
                y = circle.top() - PANEL_GAP - ph
            else:
                y = circle.bottom() + PANEL_GAP

        x = max(EDGE_GAP, min(x, parent.width() - pw - EDGE_GAP))
        y = max(EDGE_GAP, min(y, parent.height() - ph - EDGE_GAP))

        panel.move(int(x), int(y))
        panel.raise_()
