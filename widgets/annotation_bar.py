"""Floating annotation toolbar shown over the slides while presenting.

It floats over the slide preview, or over the full screen view while
that is open, and draws into a shared SlideInk. It is always dark, like
a presenter remote, so it reads on light and dark slides alike, and its
buttons are large enough to hit with the hand cursor.
"""

from PyQt5.QtCore import QEvent, QPoint, QPointF, QRectF, QSize, Qt
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

# Space kept between the bar and the edge of what it floats over.
EDGE_GAP = 16

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


def _minus_icon(color, size=18):

    pixmap = QPixmap(size * 2, size * 2)
    pixmap.fill(Qt.transparent)
    pixmap.setDevicePixelRatio(2)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 2)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    painter.drawLine(QPointF(size * 0.28, size / 2), QPointF(size * 0.72, size / 2))
    painter.end()

    return QIcon(pixmap)


class _Grip(QWidget):
    """Drag handle: six dots in the current ink colour."""

    def __init__(self, bar):
        super().__init__(bar)
        self.bar = bar
        self.color = QColor("#E81123")
        self.setFixedWidth(20)
        self.setCursor(Qt.SizeAllCursor)
        self.setToolTip("Drag to move the toolbar")

    def set_color(self, color):
        self.color = QColor(color)
        self.update()

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # White ink would vanish on the light ring; keep an outline.
        painter.setPen(QPen(QColor(255, 255, 255, 90), 1))
        painter.setBrush(self.color)

        cx = self.width() / 2
        cy = self.height() / 2

        for dx in (-3.5, 3.5):
            for dy in (-7, 0, 7):
                painter.drawEllipse(QPointF(cx + dx, cy + dy), 2.4, 2.4)

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.bar.start_drag(event.globalPos())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.bar.drag_to(event.globalPos())

    def mouseReleaseEvent(self, event):
        self.bar.end_drag()


class FloatingAnnotationBar(QFrame):

    def __init__(self, ink, parent=None):
        super().__init__(parent)

        self.ink = ink
        self.setObjectName("inkBar")
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Where the bar sits, as a fraction of the free space in the
        # parent: (0.5, 1.0) is bottom centre. Kept while dragging and
        # across the move between the preview and full screen.
        self._anchor = (0.5, 1.0)
        self._drag_offset = None
        self._compact = None
        self._collapsed = False
        self._watched = None

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.setSpacing(4)

        self.grip = _Grip(self)
        layout.addWidget(self.grip)

        # ---------- full bar ----------

        self.full = QWidget(self)
        full = QHBoxLayout(self.full)
        full.setContentsMargins(0, 0, 0, 0)
        full.setSpacing(4)

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
            full.addWidget(button)

        full.addWidget(self._divider())

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
            full.addWidget(swatch)

        full.addWidget(self._divider())

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
            icon = QIcon()
            # Dots grow with the line, big enough to tell apart.
            dot = 4 + size
            icon.addPixmap(_dot_icon(dot, ICON), QIcon.Normal, QIcon.Off)
            icon.addPixmap(_dot_icon(dot, SELECTED_FG), QIcon.Normal, QIcon.On)
            button.setIcon(icon)
            button.setIconSize(QSize(24, 24))
            button.clicked.connect(lambda checked=False, s=size: self.set_size(s))
            self.size_group.addButton(button)
            self.size_buttons[size] = button
            full.addWidget(button)

        full.addWidget(self._divider())

        undo = self._tool_button("undo", "Undo", "Undo the last stroke")
        undo.clicked.connect(ink.undo)
        full.addWidget(undo)

        redo = self._tool_button("redo", "Redo", "Bring back the last undone stroke")
        redo.clicked.connect(ink.redo)
        full.addWidget(redo)

        self.clear_button = self._tool_button(
            "clear", "Clear", "Clear this slide's drawing\n"
            "Gesture: hold thumbs down 👎 for a second",
            danger=True,
        )
        self.clear_button.clicked.connect(ink.clear_slide)
        full.addWidget(self.clear_button)

        self.collapse_button = QToolButton()
        self.collapse_button.setObjectName("collapse")
        self.collapse_button.setFixedSize(28, 28)
        self.collapse_button.setCursor(Qt.PointingHandCursor)
        self.collapse_button.setToolTip("Shrink the toolbar")
        self.collapse_button.setIcon(_minus_icon(TEXT))
        self.collapse_button.setIconSize(QSize(18, 18))
        self.collapse_button.clicked.connect(lambda: self.set_collapsed(True))
        full.addWidget(self.collapse_button, 0, Qt.AlignTop)

        layout.addWidget(self.full)

        # ---------- collapsed pill ----------

        self.mini = QToolButton(self)
        self.mini.setObjectName("mini")
        self.mini.setText("Draw")
        self.mini.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.mini.setCursor(Qt.PointingHandCursor)
        self.mini.setToolTip("Open the annotation toolbar")
        self.mini.setIconSize(QSize(22, 22))
        self.mini.setFixedHeight(40)
        self.mini.clicked.connect(lambda: self.set_collapsed(False))
        self.mini.hide()
        layout.addWidget(self.mini)

        # Every button rule is scoped under #inkBar so it outranks the
        # transparent background given to the bar's plain containers.
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

            QFrame#inkBar QToolButton#mini {{
                color: {SELECTED_BG};
                font-size: 14px;
                font-weight: 700;
                padding: 0 14px 0 8px;
                border-radius: 14px;
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
        self._sync_color_marks()

        self.hide()

    # --------------------------------------------------------
    # PARTS
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

    # --------------------------------------------------------
    # CHOICES
    # --------------------------------------------------------

    def set_tool(self, tool):

        self.ink.end_stroke()
        self.ink.tool = tool
        self.tool_buttons[tool].setChecked(True)

    def set_color(self, color):

        self.ink.color = QColor(color)
        self._pick_color_button(color)

        # Picking a colour while erasing means "draw with this".
        if self.ink.tool == "eraser":
            self.set_tool("pen")

        self._sync_color_marks()

    def set_size(self, size):

        self.ink.brush_size = size

    def _pick_color_button(self, color):

        button = self.color_buttons.get(QColor(color).name())
        if button is not None:
            button.setChecked(True)

    def _sync_color_marks(self):

        color = self.ink.color.name()
        self.grip.set_color(color)
        # Black ink would vanish on the dark pill: show the pen in white.
        shown = SELECTED_BG if color == "#172033" else color
        self.mini.setIcon(QIcon(tool_pixmap("pen", shown, 22)))

    # --------------------------------------------------------
    # HOLD-TO-CLEAR FEEDBACK
    # --------------------------------------------------------

    def set_clear_progress(self, fraction):
        """Fill the Clear button while the thumbs-down is being held."""

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
            f" stop:0 #D9483B, stop:{f:.3f} #D9483B,"
            f" stop:{min(1.0, f + 0.001):.3f} rgba(255, 138, 128, 40),"
            " stop:1 rgba(255, 138, 128, 40)); }"
        )

        if self._collapsed and f >= 1:
            self.set_collapsed(False)

    # --------------------------------------------------------
    # COLLAPSE
    # --------------------------------------------------------

    def set_collapsed(self, collapsed):

        self._collapsed = bool(collapsed)
        self.full.setVisible(not self._collapsed)
        self.mini.setVisible(self._collapsed)
        self.adjustSize()
        self.place()

    # --------------------------------------------------------
    # PLACEMENT AND DRAGGING
    # --------------------------------------------------------

    def attach(self, parent):
        """Float over `parent` (the preview or the full screen view)."""

        if self._watched is not None:
            try:
                self._watched.removeEventFilter(self)
            except RuntimeError:
                pass

        visible = self.isVisible()
        self.setParent(parent)
        self._watched = parent
        parent.installEventFilter(self)
        self._compact = None
        self.place()
        self.setVisible(visible)
        self.raise_()

    def eventFilter(self, watched, event):

        if watched is self._watched and event.type() == QEvent.Resize:
            self.place()

        return super().eventFilter(watched, event)

    def _apply_compact(self):

        parent = self.parentWidget()
        compact = parent is not None and parent.width() < COMPACT_WIDTH

        if compact == self._compact:
            return

        self._compact = compact

        for button in self._labelled:
            button.setToolButtonStyle(
                Qt.ToolButtonIconOnly if compact else Qt.ToolButtonTextUnderIcon
            )
            button.setFixedSize(QSize(40, 40) if compact else QSize(54, 52))

        self.adjustSize()

    def place(self):

        parent = self.parentWidget()

        if parent is None:
            return

        self._apply_compact()
        self.adjustSize()

        free_w = max(0, parent.width() - self.width() - 2 * EDGE_GAP)
        free_h = max(0, parent.height() - self.height() - 2 * EDGE_GAP)

        fx, fy = self._anchor
        self.move(
            int(EDGE_GAP + free_w * fx),
            int(EDGE_GAP + free_h * fy),
        )

    def start_drag(self, global_pos):
        self._drag_offset = global_pos - self.mapToGlobal(QPoint(0, 0))

    def drag_to(self, global_pos):

        parent = self.parentWidget()

        if self._drag_offset is None or parent is None:
            return

        top_left = parent.mapFromGlobal(global_pos - self._drag_offset)

        free_w = max(1, parent.width() - self.width() - 2 * EDGE_GAP)
        free_h = max(1, parent.height() - self.height() - 2 * EDGE_GAP)

        self._anchor = (
            min(1.0, max(0.0, (top_left.x() - EDGE_GAP) / free_w)),
            min(1.0, max(0.0, (top_left.y() - EDGE_GAP) / free_h)),
        )
        self.place()

    def end_drag(self):
        self._drag_offset = None
