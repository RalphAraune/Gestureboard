import os

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QSlider,
    QFileDialog,
    QMessageBox,
    QSizePolicy,
    QFrame,
    QScrollArea,
)
from PyQt5.QtCore import Qt, QPoint, QStandardPaths
from PyQt5.QtGui import (
    QPainter,
    QPen,
    QColor,
    QPixmap,
    QCursor,
    QPolygon,
)


# ============================================================
# CUSTOM CURSORS
# ============================================================

def create_pen_cursor():
    """
    Pencil-style cursor.
    """

    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)

    # Pencil body
    painter.setPen(
        QPen(
            QColor("#172033"),
            1
        )
    )

    painter.setBrush(
        QColor("#F4C542")
    )

    painter.drawPolygon(
        QPolygon([
            QPoint(7, 22),
            QPoint(10, 25),
            QPoint(24, 11),
            QPoint(21, 8),
        ])
    )

    # Pencil tip
    painter.setBrush(
        QColor("#E8D3B0")
    )

    painter.drawPolygon(
        QPolygon([
            QPoint(7, 22),
            QPoint(10, 25),
            QPoint(5, 27),
        ])
    )

    # Pencil eraser
    painter.setBrush(
        QColor("#F28B8B")
    )

    painter.drawPolygon(
        QPolygon([
            QPoint(21, 8),
            QPoint(24, 11),
            QPoint(27, 8),
            QPoint(24, 5),
        ])
    )

    painter.end()

    return QCursor(
        pixmap,
        5,
        27
    )


def create_highlighter_cursor():
    """
    Highlighter-style cursor.
    """

    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)

    painter.setPen(
        QPen(
            QColor("#172033"),
            1
        )
    )

    painter.setBrush(
        QColor("#FFE36E")
    )

    painter.drawRoundedRect(
        7,
        6,
        20,
        9,
        3,
        3
    )

    painter.setBrush(
        QColor("#E8D3B0")
    )

    painter.drawPolygon(
        QPolygon([
            QPoint(7, 15),
            QPoint(15, 15),
            QPoint(11, 22),
        ])
    )

    painter.end()

    return QCursor(
        pixmap,
        11,
        22
    )


def create_eraser_cursor():
    """
    Eraser-style cursor.
    """

    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)

    painter.setPen(
        QPen(
            QColor("#172033"),
            1
        )
    )

    painter.setBrush(
        QColor("#FF9AA2")
    )

    painter.drawRoundedRect(
        6,
        9,
        20,
        12,
        4,
        4
    )

    painter.setBrush(
        QColor("#F5F7FA")
    )

    painter.drawRect(
        17,
        10,
        8,
        10
    )

    painter.end()

    return QCursor(
        pixmap,
        16,
        16
    )


def create_select_cursor():
    """
    Arrow/select cursor.
    """

    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)

    painter.setPen(
        QPen(
            QColor("#172033"),
            1
        )
    )

    painter.setBrush(
        QColor("#FFFFFF")
    )

    painter.drawPolygon(
        QPolygon([
            QPoint(3, 2),
            QPoint(3, 19),
            QPoint(8, 14),
            QPoint(12, 21),
            QPoint(15, 19),
            QPoint(11, 13),
            QPoint(18, 13),
        ])
    )

    painter.end()

    return QCursor(
        pixmap,
        3,
        2
    )


def create_hand_cursor():
    """
    Cursor used while panning.
    """

    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)

    painter.setPen(
        QPen(
            QColor("#172033"),
            2
        )
    )

    painter.drawEllipse(
        5,
        5,
        14,
        14
    )

    painter.end()

    return QCursor(
        pixmap,
        12,
        12
    )


# ============================================================
# DRAWING CANVAS
# ============================================================

class DrawingCanvas(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        # ====================================================
        # FIXED WHITEBOARD SIZE
        # ====================================================

        self.canvas_width = 1600
        self.canvas_height = 1000

        self.canvas = QPixmap(
            self.canvas_width,
            self.canvas_height
        )

        self.canvas.fill(
            QColor("#FFFFFF")
        )

        # IMPORTANT:
        # Fixed boundary.
        # The canvas will NOT expand while drawing.
        self.setFixedSize(
            self.canvas_width,
            self.canvas_height
        )

        # ====================================================
        # DRAWING SETTINGS
        # ====================================================

        self.tool = "pen"

        self.color = QColor(
            "#172033"
        )

        self.brush_size = 4

        self.opacity = 100

        # ====================================================
        # DRAWING STATE
        # ====================================================

        self.drawing = False

        self.last_point = QPoint()

        # ====================================================
        # PANNING STATE
        # ====================================================

        self.panning = False

        self.pan_start = QPoint()

        self.horizontal_start = 0

        self.vertical_start = 0

        # ====================================================
        # UNDO / REDO
        # ====================================================

        self.undo_stack = []

        self.redo_stack = []

        # ====================================================
        # MOUSE TRACKING
        # ====================================================

        self.setMouseTracking(True)

        # ====================================================
        # CUSTOM CURSORS
        # ====================================================

        self.pen_cursor = (
            create_pen_cursor()
        )

        self.highlighter_cursor = (
            create_highlighter_cursor()
        )

        self.eraser_cursor = (
            create_eraser_cursor()
        )

        self.select_cursor = (
            create_select_cursor()
        )

        self.hand_cursor = (
            create_hand_cursor()
        )

        # ====================================================
        # DEFAULT TOOL
        # ====================================================

        self.set_tool(
            "pen"
        )

    # ========================================================
    # TOOL
    # ========================================================

    def set_tool(self, tool):

        self.tool = tool

        if tool == "pen":

            self.setCursor(
                self.pen_cursor
            )

        elif tool == "highlighter":

            self.setCursor(
                self.highlighter_cursor
            )

        elif tool == "eraser":

            self.setCursor(
                self.eraser_cursor
            )

        elif tool == "select":

            self.setCursor(
                self.select_cursor
            )

        elif tool == "pan":

            self.setCursor(
                self.hand_cursor
            )

        else:

            self.setCursor(
                Qt.ArrowCursor
            )

    # ========================================================
    # COLOR
    # ========================================================

    def set_color(self, color):

        self.color = QColor(
            color
        )

        # Selecting a color automatically
        # switches back to pen.
        if self.tool not in [
            "pen",
            "highlighter"
        ]:

            self.set_tool(
                "pen"
            )

    # ========================================================
    # BRUSH SIZE
    # ========================================================

    def set_brush_size(self, value):

        self.brush_size = value

    # ========================================================
    # OPACITY
    # ========================================================

    def set_opacity(self, value):

        self.opacity = value

    # ========================================================
    # SAVE STATE
    # ========================================================

    def save_state(self):

        self.undo_stack.append(
            self.canvas.copy()
        )

        if len(self.undo_stack) > 30:

            self.undo_stack.pop(0)

        self.redo_stack.clear()

    # ========================================================
    # UNDO
    # ========================================================

    def undo(self):

        if not self.undo_stack:

            return

        self.redo_stack.append(
            self.canvas.copy()
        )

        self.canvas = (
            self.undo_stack.pop()
        )

        self.update()

    # ========================================================
    # REDO
    # ========================================================

    def redo(self):

        if not self.redo_stack:

            return

        self.undo_stack.append(
            self.canvas.copy()
        )

        self.canvas = (
            self.redo_stack.pop()
        )

        self.update()

    # ========================================================
    # CLEAR
    # ========================================================

    def clear_canvas(self):

        self.save_state()

        self.canvas.fill(
            QColor("#FFFFFF")
        )

        self.update()

    # ========================================================
    # FIND SCROLL AREA
    # ========================================================

    def get_scroll_area(self):

        parent = self.parentWidget()

        while parent:

            if isinstance(
                parent,
                QScrollArea
            ):

                return parent

            parent = parent.parentWidget()

        return None

    # ========================================================
    # MOUSE PRESS
    # ========================================================

    def mousePressEvent(self, event):

        # ====================================================
        # MIDDLE MOUSE = PAN
        # ====================================================

        if event.button() == Qt.MiddleButton:

            # Make sure drawing is stopped.
            self.drawing = False

            self.panning = True

            self.pan_start = (
                event.pos()
            )

            scroll_area = (
                self.get_scroll_area()
            )

            if scroll_area:

                self.horizontal_start = (
                    scroll_area
                    .horizontalScrollBar()
                    .value()
                )

                self.vertical_start = (
                    scroll_area
                    .verticalScrollBar()
                    .value()
                )

            self.setCursor(
                self.hand_cursor
            )

            event.accept()

            return

        # ====================================================
        # LEFT MOUSE = DRAW
        # ====================================================

        if event.button() == Qt.LeftButton:

            # Never draw while panning.
            if self.panning:

                return

            # Only drawing tools can draw.
            if self.tool not in [
                "pen",
                "highlighter",
                "eraser"
            ]:

                return

            self.save_state()

            self.drawing = True

            # Get mouse position.
            x = event.pos().x()

            y = event.pos().y()

            # Keep drawing strictly inside
            # the whiteboard.
            x = max(
                0,
                min(
                    self.canvas.width() - 1,
                    x
                )
            )

            y = max(
                0,
                min(
                    self.canvas.height() - 1,
                    y
                )
            )

            self.last_point = QPoint(
                x,
                y
            )

            # Draw starting point.
            self.draw_point(
                self.last_point,
                self.last_point
            )

            event.accept()

            return

    # ========================================================
    # MOUSE MOVE
    # ========================================================

    def mouseMoveEvent(self, event):

        # ====================================================
        # PAN
        # ====================================================

        if self.panning:

            scroll_area = (
                self.get_scroll_area()
            )

            if scroll_area:

                dx = (
                    event.pos().x()
                    - self.pan_start.x()
                )

                dy = (
                    event.pos().y()
                    - self.pan_start.y()
                )

                new_horizontal = (
                    self.horizontal_start
                    - dx
                )

                new_vertical = (
                    self.vertical_start
                    - dy
                )

                # QScrollArea automatically prevents
                # scrolling beyond its valid range.
                scroll_area.horizontalScrollBar().setValue(
                    new_horizontal
                )

                scroll_area.verticalScrollBar().setValue(
                    new_vertical
                )

            event.accept()

            return

        # ====================================================
        # DRAW
        # ====================================================

        if not self.drawing:

            return

        if not (
            event.buttons()
            & Qt.LeftButton
        ):

            return

        # IMPORTANT:
        # We DO NOT touch the scrollbars here.
        #
        # This guarantees that drawing will NEVER
        # move the whiteboard.

        x = event.pos().x()

        y = event.pos().y()

        # Keep drawing inside the fixed boundary.
        x = max(
            0,
            min(
                self.canvas.width() - 1,
                x
            )
        )

        y = max(
            0,
            min(
                self.canvas.height() - 1,
                y
            )
        )

        current_point = QPoint(
            x,
            y
        )

        self.draw_point(
            self.last_point,
            current_point
        )

        self.last_point = (
            current_point
        )

        event.accept()

    # ========================================================
    # MOUSE RELEASE
    # ========================================================

    def mouseReleaseEvent(self, event):

        # ====================================================
        # STOP PAN
        # ====================================================

        if event.button() == Qt.MiddleButton:

            self.panning = False

            # Restore current tool cursor.
            self.set_tool(
                self.tool
            )

            event.accept()

            return

        # ====================================================
        # STOP DRAWING
        # ====================================================

        if event.button() == Qt.LeftButton:

            self.drawing = False

            event.accept()

            return

    # ========================================================
    # DRAW
    # ========================================================

    def draw_point(
        self,
        start,
        end
    ):

        painter = QPainter(
            self.canvas
        )

        painter.setRenderHint(
            QPainter.Antialiasing,
            True
        )

        # ====================================================
        # ERASER
        # ====================================================

        if self.tool == "eraser":

            pen = QPen(
                QColor("#FFFFFF"),
                max(
                    8,
                    self.brush_size * 4
                ),
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin
            )

            painter.setPen(
                pen
            )

        # ====================================================
        # HIGHLIGHTER
        # ====================================================

        elif self.tool == "highlighter":

            color = QColor(
                self.color
            )

            color.setAlpha(
                int(
                    self.opacity
                    * 255
                    / 100.0
                    * 0.35
                )
            )

            pen = QPen(
                color,
                max(
                    15,
                    self.brush_size * 3
                ),
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin
            )

            painter.setPen(
                pen
            )

        # ====================================================
        # PEN
        # ====================================================

        else:

            color = QColor(
                self.color
            )

            color.setAlpha(
                int(
                    self.opacity
                    * 255
                    / 100.0
                )
            )

            pen = QPen(
                color,
                max(
                    1,
                    self.brush_size
                ),
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin
            )

            painter.setPen(
                pen
            )

        painter.drawLine(
            start,
            end
        )

        painter.end()

        self.update()

    # ========================================================
    # PAINT EVENT
    # ========================================================

    def paintEvent(self, event):

        painter = QPainter(
            self
        )

        painter.setRenderHint(
            QPainter.Antialiasing,
            True
        )

        # ====================================================
        # WHITEBOARD BACKGROUND
        # ====================================================

        painter.fillRect(
            self.rect(),
            QColor("#FFFFFF")
        )

        # ====================================================
        # SUBTLE GRID
        # ====================================================

        grid_size = 40

        painter.setPen(
            QPen(
                QColor("#F1F3F6"),
                1
            )
        )

        # Vertical grid
        x = 0

        while x <= self.width():

            painter.drawLine(
                x,
                0,
                x,
                self.height()
            )

            x += grid_size

        # Horizontal grid
        y = 0

        while y <= self.height():

            painter.drawLine(
                0,
                y,
                self.width(),
                y
            )

            y += grid_size

        # ====================================================
        # DRAWING
        # ====================================================

        painter.drawPixmap(
            0,
            0,
            self.canvas
        )

        painter.end()


# ============================================================
# WHITEBOARD PAGE
# ============================================================

class WhiteboardPage(QWidget):

    def __init__(self, parent=None):

        super().__init__(
            parent
        )

        self.parent_window = parent

        # ====================================================
        # CAMERA COMPATIBILITY
        # ====================================================

        self.active_camera_index = None

        self.active_camera_name = (
            "No camera selected"
        )

        # ====================================================
        # CURRENT TOOL
        # ====================================================

        self.current_tool = "pen"

        self.current_color = (
            "#172033"
        )

        # ====================================================
        # BUILD UI
        # ====================================================

        self.setup_ui()

    # ========================================================
    # SETUP UI
    # ========================================================

    def setup_ui(self):

        self.setStyleSheet("""
            QWidget {
                background-color: #F5FEFF;
                color: #0E2F76;
                font-family: "Segoe UI";
            }

            QLabel {
                background: transparent;
            }

            QPushButton {
                background-color: transparent;
                border: none;
                color: #0E2F76;
            }

            QSlider::groove:horizontal {
                height: 4px;
                background: #DCE8F5;
                border-radius: 2px;
            }

            QSlider::handle:horizontal {
                width: 11px;
                height: 11px;
                margin: -4px 0;
                background: #0E2F76;
                border-radius: 6px;
            }

            QFrame#toolbar {
                background-color: #F8FDFF;
                border: 1px solid #D7E5F3;
                border-radius: 10px;
            }

            QFrame#controlBar {
                background-color: #F8FDFF;
                border: 1px solid #D7E5F3;
                border-radius: 10px;
            }

            QFrame#canvasFrame {
                background-color: #FFFFFF;
                border: 1px solid #D7E5F3;
                border-radius: 12px;
            }
        """)

        # ====================================================
        # MAIN LAYOUT
        # ====================================================

        main_layout = QVBoxLayout(
            self
        )

        main_layout.setContentsMargins(
            34,
            24,
            34,
            24
        )

        main_layout.setSpacing(
            12
        )

        # ====================================================
        # HEADER
        # ====================================================

        title = QLabel(
            "Virtual Whiteboard"
        )

        title.setStyleSheet("""
            QLabel {
                font-size: 25px;
                font-weight: 700;
                color: #0E2F76;
            }
        """)

        subtitle = QLabel(
            "Draw, write, highlight, and erase freely on your virtual whiteboard."
        )

        subtitle.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #6482B1;
            }
        """)

        main_layout.addWidget(
            title
        )

        main_layout.addWidget(
            subtitle
        )

        # ====================================================
        # TOOLBAR
        # ====================================================

        toolbar = QFrame()

        toolbar.setObjectName(
            "toolbar"
        )

        toolbar.setFixedHeight(
            52
        )

        toolbar_layout = QHBoxLayout(
            toolbar
        )

        toolbar_layout.setContentsMargins(
            10,
            6,
            10,
            6
        )

        toolbar_layout.setSpacing(
            5
        )

        # ====================================================
        # SELECT
        # ====================================================

        self.select_button = (
            self.create_tool_button(
                "↖",
                "Select"
            )
        )

        self.select_button.clicked.connect(
            lambda: self.set_tool(
                "select"
            )
        )

        toolbar_layout.addWidget(
            self.select_button
        )

        # ====================================================
        # PEN
        # ====================================================

        self.pen_button = (
            self.create_tool_button(
                "✎",
                "Pen"
            )
        )

        self.pen_button.clicked.connect(
            lambda: self.set_tool(
                "pen"
            )
        )

        toolbar_layout.addWidget(
            self.pen_button
        )

        # ====================================================
        # HIGHLIGHTER
        # ====================================================

        self.highlighter_button = (
            self.create_tool_button(
                "▰",
                "Highlighter"
            )
        )

        self.highlighter_button.clicked.connect(
            lambda: self.set_tool(
                "highlighter"
            )
        )

        toolbar_layout.addWidget(
            self.highlighter_button
        )

        # ====================================================
        # ERASER
        # ====================================================

        self.eraser_button = (
            self.create_tool_button(
                "▱",
                "Eraser"
            )
        )

        self.eraser_button.clicked.connect(
            lambda: self.set_tool(
                "eraser"
            )
        )

        toolbar_layout.addWidget(
            self.eraser_button
        )

        # ====================================================
        # SEPARATOR
        # ====================================================

        toolbar_layout.addWidget(
            self.create_separator()
        )

        # ====================================================
        # UNDO
        # ====================================================

        undo_button = (
            self.create_tool_button(
                "↶",
                "Undo"
            )
        )

        undo_button.clicked.connect(
            self.canvas_undo
        )

        toolbar_layout.addWidget(
            undo_button
        )

        # ====================================================
        # REDO
        # ====================================================

        redo_button = (
            self.create_tool_button(
                "↷",
                "Redo"
            )
        )

        redo_button.clicked.connect(
            self.canvas_redo
        )

        toolbar_layout.addWidget(
            redo_button
        )

        # ====================================================
        # CLEAR
        # ====================================================

        clear_button = (
            self.create_tool_button(
                "♲",
                "Clear Whiteboard"
            )
        )

        clear_button.clicked.connect(
            self.clear_canvas
        )

        toolbar_layout.addWidget(
            clear_button
        )

        # ====================================================
        # SEPARATOR
        # ====================================================

        toolbar_layout.addWidget(
            self.create_separator()
        )

        # ====================================================
        # COLORS
        # ====================================================

        colors = [
            "#172033",
            "#F04444",
            "#2876E8",
            "#28C76F",
            "#FFB020",
            "#FF8B32",
            "#9B51E0",
        ]

        for color in colors:

            color_button = QPushButton()

            color_button.setFixedSize(
                20,
                20
            )

            color_button.setToolTip(
                f"Color: {color}"
            )

            color_button.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {color};
                    border: 2px solid #FFFFFF;
                    border-radius: 10px;
                }}

                QPushButton:hover {{
                    border: 2px solid #8FAED5;
                }}

                QPushButton:pressed {{
                    border: 2px solid #0E2F76;
                }}
                """
            )

            color_button.clicked.connect(
                lambda checked=False,
                c=color:
                self.set_color(c)
            )

            toolbar_layout.addWidget(
                color_button
            )

        # ====================================================
        # SPACER
        # ====================================================

        spacer = QWidget()

        spacer.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred
        )

        toolbar_layout.addWidget(
            spacer
        )

        # ====================================================
        # SAVE
        # ====================================================

        save_button = (
            self.create_tool_button(
                "▣",
                "Save Whiteboard"
            )
        )

        save_button.clicked.connect(
            self.save_whiteboard
        )

        toolbar_layout.addWidget(
            save_button
        )

        main_layout.addWidget(
            toolbar
        )

        # ====================================================
        # CONTROL BAR
        # ====================================================

        control_bar = QFrame()

        control_bar.setObjectName(
            "controlBar"
        )

        control_bar.setFixedHeight(
            40
        )

        controls = QHBoxLayout(
            control_bar
        )

        controls.setContentsMargins(
            12,
            4,
            12,
            4
        )

        controls.setSpacing(
            10
        )

        # ====================================================
        # BRUSH SIZE
        # ====================================================

        brush_label = QLabel(
            "Brush Size"
        )

        brush_label.setStyleSheet("""
            QLabel {
                color: #6682AC;
                font-size: 12px;
            }
        """)

        controls.addWidget(
            brush_label
        )

        self.brush_slider = QSlider(
            Qt.Horizontal
        )

        self.brush_slider.setRange(
            1,
            20
        )

        self.brush_slider.setValue(
            4
        )

        self.brush_slider.setFixedWidth(
            120
        )

        self.brush_slider.setToolTip(
            "Brush Size"
        )

        self.brush_slider.valueChanged.connect(
            self.change_brush_size
        )

        controls.addWidget(
            self.brush_slider
        )

        # ====================================================
        # OPACITY
        # ====================================================

        opacity_label = QLabel(
            "Opacity"
        )

        opacity_label.setStyleSheet("""
            QLabel {
                color: #6682AC;
                font-size: 12px;
            }
        """)

        controls.addWidget(
            opacity_label
        )

        self.opacity_slider = QSlider(
            Qt.Horizontal
        )

        self.opacity_slider.setRange(
            10,
            100
        )

        self.opacity_slider.setValue(
            100
        )

        self.opacity_slider.setFixedWidth(
            120
        )

        self.opacity_slider.setToolTip(
            "Opacity"
        )

        self.opacity_slider.valueChanged.connect(
            self.change_opacity
        )

        controls.addWidget(
            self.opacity_slider
        )

        # ====================================================
        # SPACER
        # ====================================================

        controls_spacer = QWidget()

        controls_spacer.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred
        )

        controls.addWidget(
            controls_spacer
        )

        # ====================================================
        # PAN INFORMATION
        # ====================================================

        mode_label = QLabel(
            "●  Mouse Drawing Mode"
        )

        mode_label.setStyleSheet("""
            QLabel {
                background-color: #E5F0FA;
                color: #6D8AB5;
                border-radius: 14px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 600;
            }
        """)

        mode_label.setToolTip(
            "Middle mouse button + drag = Pan Whiteboard"
        )

        controls.addWidget(
            mode_label
        )

        main_layout.addWidget(
            control_bar
        )

        # ====================================================
        # CANVAS FRAME
        # ====================================================

        canvas_frame = QFrame()

        canvas_frame.setObjectName(
            "canvasFrame"
        )

        canvas_layout = QVBoxLayout(
            canvas_frame
        )

        canvas_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        canvas_layout.setSpacing(
            0
        )

        # ====================================================
        # SCROLLABLE WORKSPACE
        # ====================================================

        self.scroll_area = QScrollArea()

        # IMPORTANT:
        # False means the canvas keeps its real size.
        self.scroll_area.setWidgetResizable(
            False
        )

        self.scroll_area.setAlignment(
            Qt.AlignCenter
        )

        self.scroll_area.setFrameShape(
            QFrame.NoFrame
        )

        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #EDEFF2;
                border: none;
            }

            QScrollBar:horizontal {
                height: 10px;
                background: #F1F3F5;
            }

            QScrollBar:vertical {
                width: 10px;
                background: #F1F3F5;
            }

            QScrollBar::handle:horizontal,
            QScrollBar::handle:vertical {
                background: #B9C5D3;
                border-radius: 5px;
            }

            QScrollBar::handle:horizontal:hover,
            QScrollBar::handle:vertical:hover {
                background: #8FA2B8;
            }

            QScrollBar::add-line,
            QScrollBar::sub-line {
                background: none;
                border: none;
            }
        """)

        # ====================================================
        # CANVAS
        # ====================================================

        self.canvas = DrawingCanvas()

        self.scroll_area.setWidget(
            self.canvas
        )

        canvas_layout.addWidget(
            self.scroll_area
        )

        main_layout.addWidget(
            canvas_frame,
            1
        )

        # ====================================================
        # DEFAULT TOOL
        # ====================================================

        self.set_tool(
            "pen"
        )

    # ========================================================
    # CREATE TOOL BUTTON
    # ========================================================

    def create_tool_button(
        self,
        icon,
        tooltip
    ):

        button = QPushButton(
            icon
        )

        button.setFixedSize(
            40,
            38
        )

        button.setToolTip(
            tooltip
        )

        button.setMouseTracking(
            True
        )

        button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 8px;
                color: #5474A8;
                font-size: 19px;
                font-weight: 500;
            }

            QPushButton:hover {
                background-color: #E7F0FA;
                color: #0E2F76;
            }

            QPushButton:pressed {
                background-color: #D5E4F5;
            }
        """)

        return button

    # ========================================================
    # SEPARATOR
    # ========================================================

    def create_separator(self):

        separator = QFrame()

        separator.setFrameShape(
            QFrame.VLine
        )

        separator.setFrameShadow(
            QFrame.Plain
        )

        separator.setFixedHeight(
            25
        )

        separator.setStyleSheet("""
            QFrame {
                color: #D7E3F1;
                background-color: #D7E3F1;
                border: none;
            }
        """)

        return separator

    # ========================================================
    # TOOL
    # ========================================================

    def set_tool(self, tool):

        self.current_tool = tool

        self.canvas.set_tool(
            tool
        )

        buttons = {
            "pen": self.pen_button,
            "highlighter": self.highlighter_button,
            "eraser": self.eraser_button,
        }

        # ====================================================
        # RESET BUTTONS
        # ====================================================

        for button in buttons.values():

            button.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 8px;
                    color: #5474A8;
                    font-size: 19px;
                    font-weight: 500;
                }

                QPushButton:hover {
                    background-color: #E7F0FA;
                    color: #0E2F76;
                }

                QPushButton:pressed {
                    background-color: #D5E4F5;
                }
            """)

        # ====================================================
        # ACTIVE TOOL
        # ====================================================

        if tool in buttons:

            buttons[tool].setStyleSheet("""
                QPushButton {
                    background-color: #B7CCEA;
                    border: none;
                    border-radius: 8px;
                    color: #0E2F76;
                    font-size: 19px;
                    font-weight: 700;
                }

                QPushButton:hover {
                    background-color: #A9C2E7;
                }
            """)

    # ========================================================
    # COLOR
    # ========================================================

    def set_color(self, color):

        self.current_color = color

        self.canvas.set_color(
            color
        )

        # Selecting a color returns to Pen.
        self.set_tool(
            "pen"
        )

    # ========================================================
    # BRUSH SIZE
    # ========================================================

    def change_brush_size(self, value):

        self.canvas.set_brush_size(
            value
        )

    # ========================================================
    # OPACITY
    # ========================================================

    def change_opacity(self, value):

        self.canvas.set_opacity(
            value
        )

    # ========================================================
    # UNDO
    # ========================================================

    def canvas_undo(self):

        self.canvas.undo()

    # ========================================================
    # REDO
    # ========================================================

    def canvas_redo(self):

        self.canvas.redo()

    # ========================================================
    # CLEAR
    # ========================================================

    def clear_canvas(self):

        reply = QMessageBox.question(
            self,
            "Clear Whiteboard",
            "Are you sure you want to clear the whiteboard?",
            QMessageBox.Yes
            | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:

            self.canvas.clear_canvas()

    # ========================================================
    # SAVE
    # ========================================================

    def save_whiteboard(self):

        # Default to a normal computer location (the user's Pictures
        # folder) instead of the application folder, so saved whiteboards
        # are easy to find outside the app.
        default_dir = (
            QStandardPaths.writableLocation(
                QStandardPaths.PicturesLocation
            )
            or os.path.expanduser("~")
        )

        default_path = os.path.join(
            default_dir,
            "whiteboard.png"
        )

        file_path, _ = (
            QFileDialog.getSaveFileName(
                self,
                "Save Whiteboard",
                default_path,
                "PNG Image (*.png)"
            )
        )

        if not file_path:

            return

        # Make sure the file keeps a .png extension.
        if not file_path.lower().endswith(".png"):

            file_path += ".png"

        try:

            self.canvas.canvas.save(
                file_path,
                "PNG"
            )

            QMessageBox.information(
                self,
                "Whiteboard Saved",
                "Your whiteboard has been saved to:\n\n"
                + file_path
            )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Save Error",
                f"Could not save the whiteboard.\n\n{e}"
            )

    # ========================================================
    # CAMERA COMPATIBILITY
    # ========================================================

    def setActiveCamera(
        self,
        index,
        name
    ):

        self.active_camera_index = index

        self.active_camera_name = name

    # ========================================================
    # CAMERA NAME
    # ========================================================

    def updateCameraName(
        self,
        name
    ):

        self.active_camera_name = name