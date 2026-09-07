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
)

from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtGui import (
    QPainter,
    QPen,
    QColor,
    QPixmap,
    QImage,
    QCursor,
)


# ============================================================
# DRAWING CANVAS
# ============================================================

class DrawingCanvas(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMinimumSize(500, 400)
        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

        # ----------------------------------------------------
        # Drawing settings
        # ----------------------------------------------------

        self.tool = "pen"
        self.color = QColor("#0E2F76")
        self.brush_size = 4
        self.opacity = 100

        # ----------------------------------------------------
        # Canvas - sized to fill the widget (like the Annotation
        # canvas), so there is no fixed "limit" / letterboxing.
        # ----------------------------------------------------

        self.canvas = QPixmap(
            max(1, self.width()),
            max(1, self.height())
        )

        self.canvas.fill(QColor("#F8FDFF"))

        # ----------------------------------------------------
        # Drawing state
        # ----------------------------------------------------

        self.drawing = False
        self.last_point = QPoint()

        # ----------------------------------------------------
        # Undo / Redo
        # ----------------------------------------------------

        self.undo_stack = []
        self.redo_stack = []

        self.setMouseTracking(True)

        self.setStyleSheet("""
            QWidget {
                background-color: #F8FDFF;
                border: none;
            }
        """)

    # ========================================================
    # TOOL
    # ========================================================

    def set_tool(self, tool):
        self.tool = tool

        if tool == "pen":
            self.setCursor(Qt.CrossCursor)

        elif tool == "highlighter":
            self.setCursor(Qt.CrossCursor)

        elif tool == "eraser":
            self.setCursor(Qt.CrossCursor)

        else:
            self.setCursor(Qt.ArrowCursor)

    # ========================================================
    # COLOR
    # ========================================================

    def set_color(self, color):
        self.color = QColor(color)

        # Automatically return to pen when selecting color
        if self.tool not in ["pen", "highlighter"]:
            self.set_tool("pen")

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

        # Limit undo history
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

        self.canvas = self.undo_stack.pop()

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

        self.canvas = self.redo_stack.pop()

        self.update()

    # ========================================================
    # CLEAR
    # ========================================================

    def clear_canvas(self):

        self.save_state()

        self.canvas.fill(
            QColor("#F8FDFF")
        )

        self.update()

    # ========================================================
    # MOUSE PRESS
    # ========================================================

    def mousePressEvent(self, event):

        if event.button() != Qt.LeftButton:
            return

        if self.tool not in [
            "pen",
            "highlighter",
            "eraser"
        ]:
            return

        self.save_state()

        self.drawing = True

        self.last_point = self.map_to_canvas(
            event.pos()
        )

        self.draw_point(
            self.last_point,
            self.last_point
        )

    # ========================================================
    # MOUSE MOVE
    # ========================================================

    def mouseMoveEvent(self, event):

        if not self.drawing:
            return

        if not (
            event.buttons()
            & Qt.LeftButton
        ):
            return

        current_point = self.map_to_canvas(
            event.pos()
        )

        self.draw_point(
            self.last_point,
            current_point
        )

        self.last_point = current_point

    # ========================================================
    # MOUSE RELEASE
    # ========================================================

    def mouseReleaseEvent(self, event):

        if event.button() == Qt.LeftButton:
            self.drawing = False

    # ========================================================
    # MAP DISPLAY COORDINATES TO PIXMAP
    #
    # Must mirror paintEvent() exactly: the canvas is scaled with
    # KeepAspectRatio and centered, so we first remove the centering
    # offsets, then map from the scaled area back into canvas pixels.
    # ========================================================

    def map_to_canvas(self, point):

        scaled = self.canvas.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        # Centering offsets used in paintEvent()
        scaled_w = scaled.width()
        scaled_h = scaled.height()

        offset_x = (
            self.width()
            - scaled_w
        ) // 2

        offset_y = (
            self.height()
            - scaled_h
        ) // 2

        # Remove the offsets -> coordinates inside the scaled image
        local_x = point.x() - offset_x
        local_y = point.y() - offset_y

        # Map scaled-image coordinates back into canvas (device) pixels
        x_ratio = (
            self.canvas.width()
            / max(1, scaled_w)
        )

        y_ratio = (
            self.canvas.height()
            / max(1, scaled_h)
        )

        x = int(local_x * x_ratio)
        y = int(local_y * y_ratio)

        x = max(
            0,
            min(self.canvas.width() - 1, x)
        )

        y = max(
            0,
            min(self.canvas.height() - 1, y)
        )

        return QPoint(x, y)

    # ========================================================
    # BRUSH SCALE
    #
    # The pen draws in canvas (device) pixels, but is displayed
    # scaled down. Multiply by the inverse scale so the stroke
    # thickness the user selects is the thickness they see.
    # ========================================================

    def scaled_brush(self, value):

        scaled = self.canvas.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        scale = max(1, self.canvas.width()) / max(
            1,
            scaled.width()
        )

        return max(1, int(value * scale))

    # ========================================================
    # DRAW
    # ========================================================

    def draw_point(self, start, end):

        painter = QPainter(self.canvas)

        painter.setRenderHint(
            QPainter.Antialiasing,
            True
        )

        # ----------------------------------------------------
        # Eraser
        # ----------------------------------------------------

        if self.tool == "eraser":

            pen = QPen(
                QColor("#F8FDFF"),
                self.scaled_brush(self.brush_size) * 4,
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin
            )

            painter.setPen(pen)

        # ----------------------------------------------------
        # Highlighter
        # ----------------------------------------------------

        elif self.tool == "highlighter":

            color = QColor(self.color)

            color.setAlpha(
                int(self.opacity * 255 / 100.0 * 0.35)
            )

            pen = QPen(
                color,
                max(10, self.scaled_brush(self.brush_size) * 3),
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin
            )

            painter.setPen(pen)

        # ----------------------------------------------------
        # Pen
        # ----------------------------------------------------

        else:

            color = QColor(self.color)

            # Map opacity slider (10-100) to a proper 0-255 alpha.
            color.setAlpha(
                int(self.opacity * 255 / 100.0)
            )

            pen = QPen(
                color,
                self.scaled_brush(self.brush_size),
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin
            )

            painter.setPen(pen)

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

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing,
            True
        )

        # ----------------------------------------------------
        # Background
        # ----------------------------------------------------

        painter.fillRect(
            self.rect(),
            QColor("#F8FDFF")
        )

        # ----------------------------------------------------
        # Scale canvas to widget
        # ----------------------------------------------------

        scaled = self.canvas.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        x = (
            self.width()
            - scaled.width()
        ) // 2

        y = (
            self.height()
            - scaled.height()
        ) // 2

        painter.drawPixmap(
            x,
            y,
            scaled
        )

        painter.end()


# ============================================================
# WHITEBOARD PAGE
# ============================================================

class WhiteboardPage(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.parent_window = parent

        self.active_camera_index = None
        self.active_camera_name = "No camera selected"

        self.current_tool = "pen"
        self.current_color = "#0E2F76"

        self.setup_ui()

    # ========================================================
    # UI
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
                width: 10px;
                height: 10px;
                margin: -3px 0;
                background: #0E2F76;
                border-radius: 5px;
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
                background-color: #F8FDFF;
                border: 1px solid #D7E5F3;
                border-radius: 12px;
            }
        """)

        # ====================================================
        # MAIN LAYOUT
        # ====================================================

        main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(
            40,
            28,
            40,
            28
        )

        main_layout.setSpacing(14)

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
            "Draw and write using your mouse — gestures are not used here."
        )

        subtitle.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #6482B1;
            }
        """)

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # ====================================================
        # TOOLBAR
        # ====================================================

        toolbar = QFrame()
        toolbar.setObjectName("toolbar")

        toolbar.setFixedHeight(50)

        toolbar_layout = QHBoxLayout(
            toolbar
        )

        toolbar_layout.setContentsMargins(
            12,
            6,
            12,
            6
        )

        toolbar_layout.setSpacing(4)

        # ----------------------------------------------------
        # Select
        # ----------------------------------------------------

        self.select_button = self.create_tool_button(
            "↖",
            "Select"
        )

        toolbar_layout.addWidget(
            self.select_button
        )

        # ----------------------------------------------------
        # Pen
        # ----------------------------------------------------

        self.pen_button = self.create_tool_button(
            "✎",
            "Pen"
        )

        self.pen_button.clicked.connect(
            lambda: self.set_tool("pen")
        )

        toolbar_layout.addWidget(
            self.pen_button
        )

        # ----------------------------------------------------
        # Highlighter
        # ----------------------------------------------------

        self.highlighter_button = self.create_tool_button(
            "🖌",
            "Highlighter"
        )

        self.highlighter_button.clicked.connect(
            lambda: self.set_tool("highlighter")
        )

        toolbar_layout.addWidget(
            self.highlighter_button
        )

        # ----------------------------------------------------
        # Eraser
        # ----------------------------------------------------

        self.eraser_button = self.create_tool_button(
            "▱",
            "Eraser"
        )

        self.eraser_button.clicked.connect(
            lambda: self.set_tool("eraser")
        )

        toolbar_layout.addWidget(
            self.eraser_button
        )

        # Separator
        separator1 = self.create_separator()
        toolbar_layout.addWidget(separator1)

        # ----------------------------------------------------
        # Undo
        # ----------------------------------------------------

        undo_button = self.create_tool_button(
            "↶",
            "Undo"
        )

        undo_button.clicked.connect(
            self.canvas_undo
        )

        toolbar_layout.addWidget(
            undo_button
        )

        # ----------------------------------------------------
        # Redo
        # ----------------------------------------------------

        redo_button = self.create_tool_button(
            "↷",
            "Redo"
        )

        redo_button.clicked.connect(
            self.canvas_redo
        )

        toolbar_layout.addWidget(
            redo_button
        )

        # ----------------------------------------------------
        # Clear
        # ----------------------------------------------------

        clear_button = self.create_tool_button(
            "♲",
            "Clear"
        )

        clear_button.clicked.connect(
            self.clear_canvas
        )

        toolbar_layout.addWidget(
            clear_button
        )

        # Separator
        separator2 = self.create_separator()
        toolbar_layout.addWidget(separator2)

        # ----------------------------------------------------
        # Colors
        # ----------------------------------------------------

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
                19,
                19
            )

            color_button.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {color};
                    border: 2px solid #FFFFFF;
                    border-radius: 9px;
                }}

                QPushButton:hover {{
                    border: 2px solid #8FAED5;
                }}
                """
            )

            color_button.clicked.connect(
                lambda checked=False,
                c=color: self.set_color(c)
            )

            toolbar_layout.addWidget(
                color_button
            )

        # ----------------------------------------------------
        # Spacer
        # ----------------------------------------------------

        spacer = QWidget()

        spacer.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred
        )

        toolbar_layout.addWidget(
            spacer
        )

        # ----------------------------------------------------
        # Save
        # ----------------------------------------------------

        save_button = self.create_tool_button(
            "▣",
            "Save"
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
        # SETTINGS BAR
        # ====================================================

        control_bar = QFrame()
        control_bar.setObjectName(
            "controlBar"
        )

        control_bar.setFixedHeight(38)

        controls = QHBoxLayout(
            control_bar
        )

        controls.setContentsMargins(
            12,
            4,
            12,
            4
        )

        controls.setSpacing(12)

        # ----------------------------------------------------
        # Brush Size
        # ----------------------------------------------------

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

        self.brush_slider.valueChanged.connect(
            self.change_brush_size
        )

        controls.addWidget(
            self.brush_slider
        )

        # ----------------------------------------------------
        # Opacity
        # ----------------------------------------------------

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

        self.opacity_slider.valueChanged.connect(
            self.change_opacity
        )

        controls.addWidget(
            self.opacity_slider
        )

        # Spacer
        controls_spacer = QWidget()

        controls_spacer.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred
        )

        controls.addWidget(
            controls_spacer
        )

        # ----------------------------------------------------
        # Mode indicator
        # ----------------------------------------------------

        mode_label = QLabel(
            "●  Mouse Drawing Mode"
        )

        mode_label.setStyleSheet("""
            QLabel {
                background-color: #E5F0FA;
                color: #B0C7E3;
                border-radius: 14px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 600;
            }
        """)

        controls.addWidget(
            mode_label
        )

        main_layout.addWidget(
            control_bar
        )

        # ====================================================
        # CANVAS
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

        canvas_layout.setSpacing(0)

        self.canvas = DrawingCanvas()

        canvas_layout.addWidget(
            self.canvas
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

        button.setToolTip(
            tooltip
        )

        button.setFixedSize(
            38,
            36
        )

        button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 7px;
                color: #5474A8;
                font-size: 19px;
            }

            QPushButton:hover {
                background-color: #E7F0FA;
            }

            QPushButton:checked {
                background-color: #B7CCEA;
                color: #0E2F76;
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

        for name, button in buttons.items():

            if name == tool:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #B7CCEA;
                        border: none;
                        border-radius: 7px;
                        color: #0E2F76;
                        font-size: 19px;
                    }
                """)

            else:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        border-radius: 7px;
                        color: #5474A8;
                        font-size: 19px;
                    }

                    QPushButton:hover {
                        background-color: #E7F0FA;
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
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:

            self.canvas.clear_canvas()

    # ========================================================
    # SAVE
    # ========================================================

    def save_whiteboard(self):

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Whiteboard",
            "whiteboard.png",
            "PNG Image (*.png)"
        )

        if not file_path:
            return

        try:

            self.canvas.canvas.save(
                file_path,
                "PNG"
            )

            QMessageBox.information(
                self,
                "Whiteboard Saved",
                "Your whiteboard has been saved successfully."
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

    def updateCameraName(
        self,
        name
    ):

        self.active_camera_name = name
