import os
import math
import time

import cv2
import pyautogui

# MediaPipe may fail to load its DLL on some Python setups. Make it optional
# so the rest of the app still starts.
try:
    import mediapipe as mp
except Exception:
    mp = None

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
    QMenu,
)
from PyQt5.QtCore import (
    Qt,
    QPoint,
    QRect,
    QTimer,
    QStandardPaths,
)
from PyQt5.QtGui import (
    QPainter,
    QPen,
    QColor,
    QPixmap,
    QCursor,
    QPolygon,
    QBrush,
)


# ============================================================
# SETTINGS
# ============================================================

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

CAMERA_PREVIEW_WIDTH = 140
CAMERA_PREVIEW_HEIGHT = 105

# Cursor smoothing.
# Smaller = smoother/slower.
# Larger = faster/more responsive.
CURSOR_SMOOTHING = 0.12

# Ignore tiny hand movements.
CURSOR_DEADZONE = 0.008

# Closed-palm click cooldown.
CLICK_COOLDOWN = 0.65

# Index + middle finger distance.
# Smaller = must be more tightly together.
DRAW_FINGER_DISTANCE = 0.055

# Minimum points required before automatic shape recognition.
MIN_SHAPE_POINTS = 12


# ============================================================
# CURSOR HELPERS
# ============================================================

def create_pen_cursor():
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


def create_hand_cursor():
    """
    Open-hand style cursor.
    """

    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)

    painter.setPen(
        QPen(
            QColor("#0E2F76"),
            2
        )
    )

    painter.setBrush(
        QColor("#FFFFFF")
    )

    # Palm
    painter.drawRoundedRect(
        9,
        10,
        14,
        15,
        5,
        5
    )

    # Fingers
    painter.drawRoundedRect(
        7,
        3,
        4,
        12,
        2,
        2
    )

    painter.drawRoundedRect(
        12,
        2,
        4,
        13,
        2,
        2
    )

    painter.drawRoundedRect(
        17,
        3,
        4,
        12,
        2,
        2
    )

    painter.drawRoundedRect(
        22,
        6,
        4,
        10,
        2,
        2
    )

    painter.end()

    return QCursor(
        pixmap,
        16,
        16
    )


def create_eraser_cursor():
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
    pixmap = QPixmap(28, 28)
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
            QPoint(3, 22),
            QPoint(9, 16),
            QPoint(13, 24),
            QPoint(17, 22),
            QPoint(13, 15),
            QPoint(21, 15),
        ])
    )

    painter.end()

    return QCursor(
        pixmap,
        3,
        2
    )


# ============================================================
# DRAWING CANVAS
# ============================================================

class DrawingCanvas(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.tool = "pen"

        self.color = QColor(
            "#172033"
        )

        self.brush_size = 4

        self.opacity = 100

        self.drawing = False

        self.mouse_drawing = False

        self.last_point = QPoint()

        self.undo_stack = []

        self.redo_stack = []

        # Gesture drawing cursor.
        self.gesture_cursor_pos = None

        self.show_gesture_cursor = False

        # Circle (brush) cursor that follows the pointer. Its size matches
        # the current tool width.
        self.mouse_pos = None

        self.cursor_visible = False

        # Points of the current mouse stroke (used for auto-shape).
        self.stroke_points = []

        # Callback set by the page to auto-correct a finished stroke.
        self.on_stroke_finished = None

        # Shape mode: "auto" recognises the shape, otherwise it forces the
        # chosen shape (line / circle / rectangle / triangle / arrow).
        self.shape_mode = "auto"

        # Rubber-band shape drag (drag to set the size of the shape).
        self._shape_dragging = False
        self._shape_start = None
        self._shape_current = None

        # ====================================================
        # PIXMAP
        # ====================================================

        self.canvas = QPixmap(
            1200,
            700
        )

        self.canvas.fill(
            QColor("#FFFFFF")
        )

        self.setMinimumSize(
            400,
            300
        )

        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

        self.setMouseTracking(True)

        # ====================================================
        # CURSORS
        # ====================================================

        self.pen_cursor = create_pen_cursor()

        self.eraser_cursor = create_eraser_cursor()

        self.select_cursor = create_select_cursor()

        self.hand_cursor = create_hand_cursor()

        self.setCursor(
            self.pen_cursor
        )

    # ========================================================
    # RESIZE
    # ========================================================

    def resizeEvent(self, event):

        new_width = max(
            400,
            self.width()
        )

        new_height = max(
            300,
            self.height()
        )

        old_canvas = self.canvas

        if (
            old_canvas.width() != new_width
            or
            old_canvas.height() != new_height
        ):

            new_canvas = QPixmap(
                new_width,
                new_height
            )

            new_canvas.fill(
                QColor("#FFFFFF")
            )

            painter = QPainter(
                new_canvas
            )

            painter.drawPixmap(
                0,
                0,
                old_canvas
            )

            painter.end()

            self.canvas = new_canvas

        super().resizeEvent(
            event
        )

    # ========================================================
    # TOOL
    # ========================================================

    def set_tool(
        self,
        tool
    ):

        self.tool = tool

        # Draw tools use the drawn circle cursor (blank system cursor).
        # Select mode keeps a normal arrow.
        if tool in ("pen", "highlighter", "eraser"):

            self.setCursor(
                Qt.BlankCursor
            )

        elif tool == "select":

            self.setCursor(
                self.select_cursor
            )

        else:

            self.setCursor(
                Qt.ArrowCursor
            )

        self.update()

    # ========================================================
    # TOOL WIDTH
    # ========================================================

    def current_width(self):
        """Stroke width for the active tool (also the cursor size)."""

        if self.tool == "eraser":

            return int(self.brush_size * 4)

        if self.tool == "highlighter":

            return int(max(10, self.brush_size * 3))

        return int(self.brush_size)

    # ========================================================
    # COLOR
    # ========================================================

    def set_color(
        self,
        color
    ):

        self.color = QColor(
            color
        )

        if self.tool == "eraser":

            self.set_tool(
                "pen"
            )

    # ========================================================
    # BRUSH SIZE
    # ========================================================

    def set_brush_size(
        self,
        value
    ):

        self.brush_size = value

    # ========================================================
    # OPACITY
    # ========================================================

    def set_opacity(
        self,
        value
    ):

        self.opacity = value

    # ========================================================
    # GESTURE CURSOR
    # ========================================================

    def set_gesture_cursor(
        self,
        point,
        visible=True
    ):

        self.gesture_cursor_pos = point

        self.show_gesture_cursor = visible

        self.update()

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
    # MOUSE PRESS
    # ========================================================

    def mousePressEvent(
        self,
        event
    ):

        if event.button() != Qt.LeftButton:

            return

        if self.tool not in [
            "pen",
            "highlighter",
            "eraser"
        ]:

            return

        # Explicit shape mode: drag to draw the shape (rubber-band),
        # instead of free-hand drawing.
        if self.tool == "pen" and self.shape_mode != "auto":

            self.save_state()

            point = self.clamp_point(
                event.pos()
            )

            self._shape_dragging = True

            self._shape_start = point

            self._shape_current = point

            self.update()

            event.accept()

            return

        self.save_state()

        self.mouse_drawing = True

        point = self.clamp_point(
            event.pos()
        )

        self.last_point = point

        self.mouse_pos = point

        self.cursor_visible = True

        # Start a new stroke (used for auto-shape recognition).
        self.stroke_points = [point]

        self.draw_line(
            point,
            point
        )

        event.accept()

    # ========================================================
    # MOUSE MOVE
    # ========================================================

    def mouseMoveEvent(
        self,
        event
    ):

        current_point = self.clamp_point(
            event.pos()
        )

        # Keep the circle cursor following the pointer.
        self.mouse_pos = current_point

        self.cursor_visible = True

        # Live shape preview while dragging.
        if self._shape_dragging:

            self._shape_current = current_point

            self.update()

            event.accept()

            return

        self.update()

        if not self.mouse_drawing:

            event.accept()

            return

        if not (
            event.buttons()
            &
            Qt.LeftButton
        ):

            return

        self.draw_line(
            self.last_point,
            current_point
        )

        self.last_point = (
            current_point
        )

        self.stroke_points.append(
            current_point
        )

        event.accept()

    # ========================================================
    # MOUSE RELEASE
    # ========================================================

    def mouseReleaseEvent(
        self,
        event
    ):

        if event.button() == Qt.LeftButton:

            # Commit a dragged shape.
            if self._shape_dragging:

                start = self._shape_start

                end = self._shape_current

                self._shape_dragging = False

                self._shape_start = None

                self._shape_current = None

                if (
                    start is not None
                    and end is not None
                    and self.on_stroke_finished is not None
                ):

                    try:

                        self.on_stroke_finished(
                            [start, end]
                        )

                    except Exception:

                        pass

                self.update()

                event.accept()

                return

            was_drawing = self.mouse_drawing

            self.mouse_drawing = False

            # Auto-shape: let the page "perfect" the finished pen stroke.
            if (
                was_drawing
                and self.tool == "pen"
                and self.on_stroke_finished is not None
                and len(self.stroke_points) >= MIN_SHAPE_POINTS
            ):

                try:

                    self.on_stroke_finished(
                        list(self.stroke_points)
                    )

                except Exception:

                    pass

            self.stroke_points = []

            event.accept()

    # ========================================================
    # LEAVE (hide the circle cursor)
    # ========================================================

    def leaveEvent(
        self,
        event
    ):

        self.cursor_visible = False

        self.update()

        super().leaveEvent(
            event
        )

    # ========================================================
    # CLAMP
    # ========================================================

    def clamp_point(
        self,
        point
    ):

        x = max(
            0,
            min(
                self.width() - 1,
                point.x()
            )
        )

        y = max(
            0,
            min(
                self.height() - 1,
                point.y()
            )
        )

        return QPoint(
            x,
            y
        )

    # ========================================================
    # DRAW LINE
    # ========================================================

    def draw_line(
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

        if self.tool == "eraser":

            pen = QPen(
                QColor("#FFFFFF"),
                max(
                    10,
                    self.brush_size * 4
                ),
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin
            )

        elif self.tool == "highlighter":

            color = QColor(
                self.color
            )

            color.setAlpha(
                int(
                    self.opacity
                    *
                    255
                    /
                    100
                    *
                    0.35
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

        else:

            color = QColor(
                self.color
            )

            color.setAlpha(
                int(
                    self.opacity
                    *
                    255
                    /
                    100
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
    # DRAW GESTURE LINE
    # ========================================================

    def draw_gesture_line(
        self,
        start,
        end
    ):

        self.draw_line(
            start,
            end
        )

    # ========================================================
    # PAINT
    # ========================================================

    def paintEvent(
        self,
        event
    ):

        painter = QPainter(
            self
        )

        painter.setRenderHint(
            QPainter.Antialiasing,
            True
        )

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

        x = 0

        while x < self.width():

            painter.drawLine(
                x,
                0,
                x,
                self.height()
            )

            x += grid_size

        y = 0

        while y < self.height():

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

        # ====================================================
        # GESTURE DRAWING CURSOR
        # ====================================================

        if (
            self.show_gesture_cursor
            and
            self.gesture_cursor_pos
        ):

            center = (
                self.gesture_cursor_pos
            )

            radius = max(
                8,
                int(
                    self.brush_size * 1.8
                )
            )

            painter.setBrush(
                QColor(
                    14,
                    47,
                    118,
                    25
                )
            )

            painter.setPen(
                QPen(
                    QColor(
                        "#0E2F76"
                    ),
                    2
                )
            )

            painter.drawEllipse(
                center,
                radius,
                radius
            )

            painter.setPen(
                QPen(
                    QColor(
                        "#0E2F76"
                    ),
                    1
                )
            )

            painter.drawLine(
                center.x() - radius - 4,
                center.y(),
                center.x() + radius + 4,
                center.y()
            )

            painter.drawLine(
                center.x(),
                center.y() - radius - 4,
                center.x(),
                center.y() + radius + 4
            )

        # ====================================================
        # LIVE SHAPE PREVIEW (rubber-band while dragging a shape)
        # ====================================================

        if (
            self._shape_dragging
            and self._shape_start is not None
            and self._shape_current is not None
        ):

            shape_start = self._shape_start

            shape_end = self._shape_current

            preview_color = QColor(
                self.color
            )

            preview_color.setAlpha(170)

            painter.setBrush(
                Qt.NoBrush
            )

            painter.setPen(
                QPen(
                    preview_color,
                    2,
                    Qt.DashLine
                )
            )

            mode = self.shape_mode

            if mode == "circle":

                painter.drawEllipse(
                    QRect(
                        shape_start,
                        shape_end
                    ).normalized()
                )

            elif mode == "rectangle":

                painter.drawRect(
                    QRect(
                        shape_start,
                        shape_end
                    ).normalized()
                )

            elif mode == "triangle":

                rect = QRect(
                    shape_start,
                    shape_end
                ).normalized()

                icon_points = QPolygon(
                    [
                        QPoint(
                            rect.center().x(),
                            rect.top()
                        ),
                        QPoint(
                            rect.right(),
                            rect.bottom()
                        ),
                        QPoint(
                            rect.left(),
                            rect.bottom()
                        ),
                    ]
                )

                painter.drawPolygon(
                    icon_points
                )

            else:

                painter.drawLine(
                    shape_start,
                    shape_end
                )

        # ====================================================
        # CIRCLE (BRUSH) CURSOR
        # Size follows the current tool width. Drawn as a large,
        # semi-transparent ring so it never looks like a black blob.
        # ====================================================

        if (
            self.cursor_visible
            and self.mouse_pos is not None
            and self.tool in ("pen", "highlighter", "eraser")
        ):

            radius = max(
                8,
                int(self.current_width() / 2) + 5
            )

            ring_color = QColor(
                self.color
            )

            if self.tool == "eraser":

                ring_color = QColor("#5A6B93")

            ring_color.setAlpha(170)

            painter.setBrush(
                Qt.NoBrush
            )

            painter.setPen(
                QPen(
                    ring_color,
                    2
                )
            )

            painter.drawEllipse(
                self.mouse_pos,
                radius,
                radius
            )

            # Semi-transparent centre marker (not a solid dot).
            marker = QColor(
                ring_color
            )

            marker.setAlpha(110)

            painter.setBrush(
                marker
            )

            painter.setPen(
                Qt.NoPen
            )

            painter.drawEllipse(
                self.mouse_pos,
                2,
                2
            )

        painter.end()


# ============================================================
# WHITEBOARD PAGE
# ============================================================

class WhiteboardPage(QWidget):

    def __init__(
        self,
        parent=None
    ):

        super().__init__(
            parent
        )

        self.parent_window = parent

        # ====================================================
        # CAMERA
        # ====================================================

        self.camera = None

        self.camera_timer = QTimer(
            self
        )

        self.camera_timer.timeout.connect(
            self.update_camera
        )

        self.camera_running = False

        self.camera_index = 0

        self.active_camera_index = None

        self.active_camera_name = (
            "No camera selected"
        )

        # ====================================================
        # MEDIAPIPE
        # ====================================================

        if mp is not None:

            self.mp_hands = (
                mp.solutions.hands
            )

            self.mp_drawing = (
                mp.solutions.drawing_utils
            )

            self.hands = (
                self.mp_hands.Hands(
                    static_image_mode=False,
                    max_num_hands=1,
                    min_detection_confidence=0.65,
                    min_tracking_confidence=0.65,
                    model_complexity=1
                )
            )

        else:

            self.mp_hands = None
            self.mp_drawing = None
            self.hands = None

        # ====================================================
        # GESTURE STATE
        # ====================================================

        self.current_gesture = "None"

        self.previous_gesture = "None"

        self.last_click_time = 0

        # ====================================================
        # CURSOR
        # ====================================================

        pyautogui.FAILSAFE = False

        screen_width, screen_height = (
            pyautogui.size()
        )

        self.screen_width = (
            screen_width
        )

        self.screen_height = (
            screen_height
        )

        self.cursor_x = (
            screen_width / 2
        )

        self.cursor_y = (
            screen_height / 2
        )

        self.last_hand_x = None

        self.last_hand_y = None

        # ====================================================
        # DRAWING
        # ====================================================

        self.gesture_drawing = False

        self.gesture_points = []

        self.last_draw_point = None

        # ====================================================
        # TOOL
        # ====================================================

        self.current_tool = "pen"

        self.current_color = (
            "#172033"
        )

        # ====================================================
        # CAMERA LABEL
        # ====================================================

        self.camera_label = QLabel(
            self
        )

        # The preview is only decorative now (the Virtual Mouse shows the
        # real camera). Make it transparent to mouse events so it never
        # blocks drawing on the canvas underneath.
        self.camera_label.setAttribute(
            Qt.WA_TransparentForMouseEvents,
            True
        )

        self.camera_label.setFixedSize(
            CAMERA_PREVIEW_WIDTH,
            CAMERA_PREVIEW_HEIGHT
        )

        self.camera_label.setStyleSheet("""
            QLabel {
                background-color: #10264E;
                border: 2px solid #FFFFFF;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 9px;
            }
        """)

        self.camera_label.setAlignment(
            Qt.AlignCenter
        )

        self.camera_label.setText(
            "Camera"
        )

        self.camera_label.raise_()

        # ====================================================
        # BUILD UI
        # ====================================================

        self.setup_ui()

    # ========================================================
    # SHOW EVENT
    # ========================================================

    def showEvent(
        self,
        event
    ):

        super().showEvent(
            event
        )

        # The Whiteboard does not open the webcam any more: the Virtual
        # Mouse provides the cursor and the index+middle "draw" gesture, so
        # both features can be used together (no camera conflict).

        self.update_camera_status()

        # Place the small camera feed in the lower-right corner.
        self.position_camera_preview()

        # Run the (shared) preview refresh loop.
        if not self.camera_timer.isActive():

            self.camera_timer.start(40)

    def update_camera_status(self):
        """Reflect the Virtual Mouse camera state in the header pill."""

        if not hasattr(self, "camera_status"):
            return

        vmouse = getattr(
            self.parent_window, "virtual_mouse", None
        )

        running = (
            vmouse is not None
            and getattr(vmouse, "camera_running", False)
        )

        self.camera_status.setText(
            "● Camera ON" if running else "● Camera OFF"
        )

    # ========================================================
    # HIDE EVENT
    # ========================================================

    def hideEvent(
        self,
        event
    ):

        super().hideEvent(
            event
        )

        # Release the webcam when leaving so it never fights the
        # Virtual Mouse or other camera pages.
        self.stop_camera()

    # ========================================================
    # RESIZE EVENT
    # ========================================================

    def resizeEvent(
        self,
        event
    ):

        super().resizeEvent(
            event
        )

        self.position_camera_preview()

    # ========================================================
    # POSITION CAMERA
    # ========================================================

    def position_camera_preview(self):

        margin = 12

        x = (
            self.width()
            -
            CAMERA_PREVIEW_WIDTH
            -
            margin
        )

        y = (
            self.height()
            -
            CAMERA_PREVIEW_HEIGHT
            -
            margin
        )

        self.camera_label.move(
            max(0, x),
            max(0, y)
        )

        self.camera_label.raise_()

    # ========================================================
    # SETUP UI
    # ========================================================

    def setup_ui(
        self
    ):

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
                background: transparent;
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

        main_layout = QVBoxLayout(
            self
        )

        main_layout.setContentsMargins(
            24,
            18,
            24,
            18
        )

        main_layout.setSpacing(
            10
        )

        # ====================================================
        # HEADER
        # ====================================================

        title = QLabel(
            "GestureBoard Whiteboard"
        )

        title.setStyleSheet("""
            QLabel {
                font-size: 25px;
                font-weight: 700;
                color: #0E2F76;
            }
        """)

        subtitle = QLabel(
            "Move the cursor with the Virtual Mouse (open palm) and draw with "
            "your index + middle fingers held together."
        )

        subtitle.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #6482B1;
            }
        """)

        # Header row: title + camera/gesture status pill.
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)

        header_row.addLayout(title_col)
        header_row.addStretch()

        self.camera_status = QLabel("● Camera ON")

        self.camera_status.setStyleSheet("""
            QLabel {
                background-color: #0E2F76;
                color: #F5FEFF;
                border-radius: 13px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 700;
            }
        """)

        header_row.addWidget(
            self.camera_status,
            alignment=Qt.AlignTop
        )

        main_layout.addLayout(header_row)

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
            lambda:
            self.set_tool("select")
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
            lambda:
            self.set_tool("pen")
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
            lambda:
            self.set_tool("highlighter")
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
            lambda:
            self.set_tool("eraser")
        )

        toolbar_layout.addWidget(
            self.eraser_button
        )

        toolbar_layout.addWidget(
            self.create_separator()
        )

        # ====================================================
        # SHAPE
        # ====================================================

        self.shape_button = (
            self.create_tool_button(
                "□",
                "Shape"
            )
        )

        self.shape_button.clicked.connect(
            self.show_shape_menu
        )

        toolbar_layout.addWidget(
            self.shape_button
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
                "⌫",
                "Clear Whiteboard"
            )
        )

        clear_button.clicked.connect(
            self.clear_canvas
        )

        toolbar_layout.addWidget(
            clear_button
        )

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
                28,
                28
            )

            color_button.setToolTip(
                f"Color: {color}"
            )

            color_button.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {color};
                    border: 3px solid #FFFFFF;
                    border-radius: 14px;
                }}

                QPushButton:hover {{
                    border: 3px solid #8FAED5;
                }}

                QPushButton:pressed {{
                    border: 3px solid #0E2F76;
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
            48
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
        # SIZE
        # ====================================================

        brush_label = QLabel(
            "Size"
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

        self.opacity_slider.valueChanged.connect(
            self.change_opacity
        )

        controls.addWidget(
            self.opacity_slider
        )

        # ----------------------------------------------------
        # GESTURE GUIDE (aligned with the tools / size row)
        # ----------------------------------------------------

        self.guide_label = QLabel(
            "🖐️ Open hand: cursor    •    "
            "✊ Fist: click    •    "
            "✌️ Peace: draw cursor    •    "
            "✌️ Together: draw"
        )

        self.guide_label.setStyleSheet("""
            QLabel {
                color: #46638F;
                font-size: 12px;
                padding-left: 6px;
            }
        """)

        controls.addWidget(
            self.guide_label
        )

        controls_spacer = QWidget()

        controls_spacer.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred
        )

        controls.addWidget(
            controls_spacer
        )

        # ====================================================
        # GESTURE STATUS
        # ====================================================

        self.gesture_status = QLabel(
            "● Open Palm = Cursor"
        )

        self.gesture_status.setStyleSheet("""
            QLabel {
                background-color: #E5F0FA;
                color: #5474A8;
                border-radius: 14px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 600;
            }
        """)

        controls.addWidget(
            self.gesture_status
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
        # CANVAS
        # ====================================================

        self.canvas = DrawingCanvas()

        # Auto-shape: when a pen stroke finishes, "perfect" it.
        self.canvas.on_stroke_finished = (
            self.on_canvas_stroke_finished
        )

        canvas_layout.addWidget(
            self.canvas
        )

        main_layout.addWidget(
            canvas_frame,
            1
        )

        # ====================================================
        # DEFAULT
        # ====================================================

        self.set_tool(
            "pen"
        )

        self.position_camera_preview()

    # ========================================================
    # TOOL BUTTON
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
            48,
            44
        )

        button.setToolTip(
            tooltip
        )

        button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 9px;
                color: #3D5A8A;
                font-size: 24px;
                font-weight: 600;
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

    def create_separator(
        self
    ):

        separator = QFrame()

        separator.setFrameShape(
            QFrame.VLine
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
    # SHAPE MENU
    # ========================================================

    def show_shape_menu(self):

        menu = QMenu(
            self
        )

        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #D7E5F3;
                padding: 5px;
            }

            QMenu::item {
                padding: 8px 25px;
                color: #0E2F76;
            }

            QMenu::item:selected {
                background-color: #E7F0FA;
            }
        """)

        auto_action = menu.addAction(
            "Automatic Shape"
        )

        line_action = menu.addAction(
            "Line"
        )

        circle_action = menu.addAction(
            "Circle"
        )

        rectangle_action = menu.addAction(
            "Rectangle"
        )

        triangle_action = menu.addAction(
            "Triangle"
        )

        arrow_action = menu.addAction(
            "Arrow"
        )

        action = menu.exec_(
            self.shape_button.mapToGlobal(
                QPoint(
                    0,
                    self.shape_button.height()
                )
            )
        )

        if action == auto_action:

            self.canvas.shape_mode = "auto"

        elif action == line_action:

            self.canvas.shape_mode = "line"

        elif action == circle_action:

            self.canvas.shape_mode = "circle"

        elif action == rectangle_action:

            self.canvas.shape_mode = "rectangle"

        elif action == triangle_action:

            self.canvas.shape_mode = "triangle"

        elif action == arrow_action:

            self.canvas.shape_mode = "arrow"

        else:

            return

        self.set_tool(
            "pen"
        )

        self.gesture_status.setText(
            f"Shape Mode: {self.canvas.shape_mode.title()}"
        )

    # ========================================================
    # TOOL
    # ========================================================

    def set_tool(
        self,
        tool
    ):

        self.current_tool = tool

        self.canvas.set_tool(
            tool
        )

        buttons = {
            "pen": self.pen_button,
            "highlighter": self.highlighter_button,
            "eraser": self.eraser_button,
        }

        normal_style = """
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
        """

        active_style = """
            QPushButton {
                background-color: #B7CCEA;
                border: none;
                border-radius: 8px;
                color: #0E2F76;
                font-size: 19px;
                font-weight: 700;
            }
        """

        for button in buttons.values():

            button.setStyleSheet(
                normal_style
            )

        if tool in buttons:

            buttons[
                tool
            ].setStyleSheet(
                active_style
            )

    # ========================================================
    # COLOR
    # ========================================================

    def set_color(
        self,
        color
    ):

        self.current_color = color

        self.canvas.set_color(
            color
        )

        self.set_tool(
            "pen"
        )

        self.gesture_status.setText(
            "Color Selected • Open Palm = Cursor"
        )

    # ========================================================
    # SIZE
    # ========================================================

    def change_brush_size(
        self,
        value
    ):

        self.canvas.set_brush_size(
            value
        )

    # ========================================================
    # OPACITY
    # ========================================================

    def change_opacity(
        self,
        value
    ):

        self.canvas.set_opacity(
            value
        )

    # ========================================================
    # UNDO
    # ========================================================

    def canvas_undo(
        self
    ):

        self.canvas.undo()

    # ========================================================
    # REDO
    # ========================================================

    def canvas_redo(
        self
    ):

        self.canvas.redo()

    # ========================================================
    # CLEAR
    # ========================================================

    def clear_canvas(
        self
    ):

        reply = QMessageBox.question(
            self,
            "Clear Whiteboard",
            "Are you sure you want to clear the whiteboard?",
            QMessageBox.Yes |
            QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:

            self.canvas.clear_canvas()

    # ========================================================
    # CAMERA
    # ========================================================

    def start_camera(
        self
    ):

        # The Whiteboard no longer opens the webcam directly. Drawing is done
        # with the Virtual Mouse (move cursor + index+middle together to
        # draw), so opening the camera here would fight the Virtual Mouse.
        # Returning immediately keeps the webcam free for the mouse.
        return

        if self.camera_running:

            return

        indexes = []

        if self.active_camera_index is not None:

            indexes.append(
                self.active_camera_index
            )

        indexes.extend(
            [0, 1, 2, 3]
        )

        tested = set()

        for index in indexes:

            if index in tested:

                continue

            tested.add(
                index
            )

            camera = cv2.VideoCapture(
                index,
                cv2.CAP_DSHOW
            )

            if not camera.isOpened():

                camera.release()

                camera = cv2.VideoCapture(
                    index
                )

            if camera.isOpened():

                self.camera = camera

                self.camera_index = index

                break

            camera.release()

        if self.camera is None:

            self.camera_label.setText(
                "Camera unavailable"
            )

            return

        self.camera.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            CAMERA_WIDTH
        )

        self.camera.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            CAMERA_HEIGHT
        )

        self.camera.set(
            cv2.CAP_PROP_FPS,
            30
        )

        self.camera_running = True

        self.camera_timer.start(
            30
        )

        self.camera_label.raise_()

    # ========================================================
    # STOP CAMERA
    # ========================================================

    def stop_camera(
        self
    ):

        self.camera_running = False

        self.camera_timer.stop()

        if self.camera:

            self.camera.release()

            self.camera = None

        self.finish_gesture_drawing()

        self.camera_label.setText(
            "Camera"
        )

    # ========================================================
    # CAMERA UPDATE
    # ========================================================

    def update_camera(
        self
    ):

        # The Whiteboard does not open its own webcam. It mirrors the
        # Virtual Mouse's camera feed into the small preview, so both
        # features share one camera and never conflict.
        if not self.camera:

            self.update_shared_preview()
            return

        success, frame = (
            self.camera.read()
        )

        if not success:

            return

        frame = cv2.flip(
            frame,
            1
        )

        gesture = "None"

        hand = None

        if self.hands is not None:

            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            rgb.flags.writeable = False

            results = self.hands.process(
                rgb
            )

            rgb.flags.writeable = True

            if results.multi_hand_landmarks:

                hand = (
                    results.multi_hand_landmarks[0]
                )

                self.mp_drawing.draw_landmarks(
                    frame,
                    hand,
                    self.mp_hands.HAND_CONNECTIONS
                )

                gesture = (
                    self.detect_gesture(
                        hand
                    )
                )

        self.current_gesture = gesture

        if hand:

            self.process_gesture(
                gesture,
                hand
            )

        else:

            self.finish_gesture_drawing()

            self.gesture_status.setText(
                "No Hand Detected"
            )

        self.display_camera(
            frame
        )

    # ========================================================
    # SHARED PREVIEW (from the Virtual Mouse)
    # ========================================================

    def update_shared_preview(self):

        vmouse = getattr(
            self.parent_window, "virtual_mouse", None
        )

        frame = None

        if vmouse is not None and hasattr(
            vmouse, "get_latest_frame"
        ):

            frame = vmouse.get_latest_frame()

        if frame is None:

            if hasattr(self, "camera_label"):

                self.camera_label.setText(
                    "Camera off  (start Virtual Mouse)"
                )

            return

        self.display_camera(
            frame
        )

    # ========================================================
    # GESTURE DETECTION
    # ========================================================

    def detect_gesture(
        self,
        hand
    ):

        landmarks = hand.landmark

        thumb_tip = landmarks[
            self.mp_hands.HandLandmark.THUMB_TIP
        ]

        thumb_ip = landmarks[
            self.mp_hands.HandLandmark.THUMB_IP
        ]

        index_tip = landmarks[
            self.mp_hands.HandLandmark.INDEX_FINGER_TIP
        ]

        index_pip = landmarks[
            self.mp_hands.HandLandmark.INDEX_FINGER_PIP
        ]

        middle_tip = landmarks[
            self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP
        ]

        middle_pip = landmarks[
            self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP
        ]

        ring_tip = landmarks[
            self.mp_hands.HandLandmark.RING_FINGER_TIP
        ]

        ring_pip = landmarks[
            self.mp_hands.HandLandmark.RING_FINGER_PIP
        ]

        pinky_tip = landmarks[
            self.mp_hands.HandLandmark.PINKY_TIP
        ]

        pinky_pip = landmarks[
            self.mp_hands.HandLandmark.PINKY_PIP
        ]

        # ====================================================
        # FINGER STATES
        # ====================================================

        index_up = (
            index_tip.y
            <
            index_pip.y
            - 0.015
        )

        middle_up = (
            middle_tip.y
            <
            middle_pip.y
            - 0.015
        )

        ring_up = (
            ring_tip.y
            <
            ring_pip.y
            - 0.015
        )

        pinky_up = (
            pinky_tip.y
            <
            pinky_pip.y
            - 0.015
        )

        # ====================================================
        # INDEX + MIDDLE DISTANCE
        # ====================================================

        index_middle_distance = math.sqrt(
            (
                index_tip.x
                -
                middle_tip.x
            ) ** 2
            +
            (
                index_tip.y
                -
                middle_tip.y
            ) ** 2
        )

        # ====================================================
        # DRAW
        # MUST BE CHECKED BEFORE OPEN PALM
        # ====================================================

        if (
            index_up
            and
            middle_up
            and
            not ring_up
            and
            not pinky_up
            and
            index_middle_distance
            <
            DRAW_FINGER_DISTANCE
        ):

            return "Draw"

        # ====================================================
        # CLOSED PALM
        # ====================================================

        fingers_closed = (
            not index_up
            and
            not middle_up
            and
            not ring_up
            and
            not pinky_up
        )

        thumb_closed_distance = math.sqrt(
            (
                thumb_tip.x
                -
                thumb_ip.x
            ) ** 2
            +
            (
                thumb_tip.y
                -
                thumb_ip.y
            ) ** 2
        )

        if fingers_closed:

            return "Closed Palm"

        # ====================================================
        # OPEN PALM
        # ====================================================

        if (
            index_up
            and
            middle_up
            and
            ring_up
            and
            pinky_up
        ):

            return "Open Palm"

        return "None"

    # ========================================================
    # PROCESS GESTURE
    # ========================================================

    def process_gesture(
        self,
        gesture,
        hand
    ):

        # ====================================================
        # OPEN PALM
        # MOVE ONLY
        # ====================================================

        if gesture == "Open Palm":

            self.finish_gesture_drawing()

            self.move_cursor(
                hand
            )

            self.gesture_status.setText(
                "● Open Palm = Cursor"
            )

            self.gesture_status.setStyleSheet("""
                QLabel {
                    background-color: #EAF8EF;
                    color: #2A9561;
                    border-radius: 14px;
                    padding: 6px 14px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)

        # ====================================================
        # CLOSED PALM
        # CLICK ONLY
        #
        # IMPORTANT:
        # No move_cursor() here.
        # ====================================================

        elif gesture == "Closed Palm":

            self.finish_gesture_drawing()

            self.closed_palm_click()

            self.gesture_status.setText(
                "● Closed Palm = Left Click"
            )

            self.gesture_status.setStyleSheet("""
                QLabel {
                    background-color: #FFF2E2;
                    color: #B56C19;
                    border-radius: 14px;
                    padding: 6px 14px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)

        # ====================================================
        # DRAW
        # ====================================================

        elif gesture == "Draw":

            self.draw_from_gesture(
                hand
            )

            self.gesture_status.setText(
                "● Index + Middle Together = Draw"
            )

            self.gesture_status.setStyleSheet("""
                QLabel {
                    background-color: #EAF2FF;
                    color: #0E2F76;
                    border-radius: 14px;
                    padding: 6px 14px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)

        # ====================================================
        # NONE
        # ====================================================

        else:

            self.finish_gesture_drawing()

            self.gesture_status.setText(
                "Open Palm = Cursor • Closed Palm = Click"
            )

            self.gesture_status.setStyleSheet("""
                QLabel {
                    background-color: #E5F0FA;
                    color: #5474A8;
                    border-radius: 14px;
                    padding: 6px 14px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)

        self.previous_gesture = gesture

    # ========================================================
    # MOVE CURSOR
    # ========================================================

    def move_cursor(
        self,
        hand
    ):

        landmarks = hand.landmark

        index_tip = landmarks[
            self.mp_hands.HandLandmark.INDEX_FINGER_TIP
        ]

        target_x = (
            index_tip.x
            *
            self.screen_width
        )

        target_y = (
            index_tip.y
            *
            self.screen_height
        )

        # ====================================================
        # DEADZONE
        # ====================================================

        if (
            self.last_hand_x is not None
            and
            self.last_hand_y is not None
        ):

            if (
                abs(
                    index_tip.x
                    -
                    self.last_hand_x
                )
                <
                CURSOR_DEADZONE
                and
                abs(
                    index_tip.y
                    -
                    self.last_hand_y
                )
                <
                CURSOR_DEADZONE
            ):

                return

        self.last_hand_x = index_tip.x

        self.last_hand_y = index_tip.y

        # ====================================================
        # SMOOTHING
        # ====================================================

        self.cursor_x += (
            target_x
            -
            self.cursor_x
        ) * CURSOR_SMOOTHING

        self.cursor_y += (
            target_y
            -
            self.cursor_y
        ) * CURSOR_SMOOTHING

        self.cursor_x = max(
            1,
            min(
                self.screen_width - 2,
                self.cursor_x
            )
        )

        self.cursor_y = max(
            1,
            min(
                self.screen_height - 2,
                self.cursor_y
            )
        )

        try:

            pyautogui.moveTo(
                int(self.cursor_x),
                int(self.cursor_y),
                duration=0
            )

        except Exception:

            pass

    # ========================================================
    # CLOSED PALM CLICK
    # ========================================================

    def closed_palm_click(
        self
    ):

        now = time.monotonic()

        # ====================================================
        # ONLY CLICK ON NEW CLOSED-PALM EVENT
        # ====================================================

        if (
            self.previous_gesture
            ==
            "Closed Palm"
        ):

            return

        if (
            now
            -
            self.last_click_time
            <
            CLICK_COOLDOWN
        ):

            return

        self.last_click_time = now

        try:

            pyautogui.click()

        except Exception:

            pass

    # ========================================================
    # GET DRAW POINT
    # ========================================================

    def get_draw_point(
        self,
        hand
    ):

        landmarks = hand.landmark

        index_tip = landmarks[
            self.mp_hands.HandLandmark.INDEX_FINGER_TIP
        ]

        middle_tip = landmarks[
            self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP
        ]

        # ====================================================
        # MIDPOINT BETWEEN INDEX + MIDDLE
        # ====================================================

        x = (
            index_tip.x
            +
            middle_tip.x
        ) / 2.0

        y = (
            index_tip.y
            +
            middle_tip.y
        ) / 2.0

        canvas_width = (
            self.canvas.width()
        )

        canvas_height = (
            self.canvas.height()
        )

        px = int(
            x
            *
            canvas_width
        )

        py = int(
            y
            *
            canvas_height
        )

        px = max(
            0,
            min(
                canvas_width - 1,
                px
            )
        )

        py = max(
            0,
            min(
                canvas_height - 1,
                py
            )
        )

        return QPoint(
            px,
            py
        )

    # ========================================================
    # DRAW FROM GESTURE
    # ========================================================

    def draw_from_gesture(
        self,
        hand
    ):

        point = self.get_draw_point(
            hand
        )

        # ====================================================
        # SHOW CIRCLE CURSOR
        # ====================================================

        self.canvas.set_gesture_cursor(
            point,
            True
        )

        # ====================================================
        # START NEW STROKE
        # ====================================================

        if not self.gesture_drawing:

            self.gesture_drawing = True

            self.gesture_points = [
                point
            ]

            self.last_draw_point = point

            self.canvas.save_state()

            return

        # ====================================================
        # DRAW
        # ====================================================

        if self.last_draw_point:

            distance = math.sqrt(
                (
                    point.x()
                    -
                    self.last_draw_point.x()
                ) ** 2
                +
                (
                    point.y()
                    -
                    self.last_draw_point.y()
                ) ** 2
            )

            # Ignore tiny jitter.
            if distance >= 1:

                self.canvas.draw_gesture_line(
                    self.last_draw_point,
                    point
                )

                self.gesture_points.append(
                    point
                )

                self.last_draw_point = (
                    point
                )

    # ========================================================
    # FINISH DRAWING
    # ========================================================

    def on_canvas_stroke_finished(
        self,
        points
    ):
        """Auto-shape a finished mouse (Virtual Mouse) pen stroke."""

        if len(points) < 2:

            return

        mode = getattr(
            self.canvas,
            "shape_mode",
            "auto"
        )

        if mode == "auto":

            if len(points) < MIN_SHAPE_POINTS:

                return

            self.auto_correct_shape(
                points
            )

        else:

            self.force_shape(
                points,
                mode
            )

    # ========================================================
    # FORCE A CHOSEN SHAPE
    #
    # Used when the user picks a specific shape in the Shape menu.
    # The shape size follows the stroke's bounding box.
    # ========================================================

    def force_shape(
        self,
        points,
        mode
    ):

        xs = [p.x() for p in points]
        ys = [p.y() for p in points]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        if (max_x - min_x) < 8 and (max_y - min_y) < 8:

            return

        if mode == "line":

            self.replace_with_line(
                points[0],
                points[-1]
            )

            return

        if mode == "circle":

            self.replace_with_circle(
                points
            )

            return

        if mode == "rectangle":

            polygon = [
                QPoint(min_x, min_y),
                QPoint(max_x, min_y),
                QPoint(max_x, max_y),
                QPoint(min_x, max_y),
            ]

            self.replace_with_polygon(
                polygon,
                "rectangle"
            )

            return

        if mode == "triangle":

            center_x = (min_x + max_x) // 2

            polygon = [
                QPoint(center_x, min_y),
                QPoint(max_x, max_y),
                QPoint(min_x, max_y),
            ]

            self.replace_with_polygon(
                polygon,
                "triangle"
            )

            return

        if mode == "arrow":

            self.replace_with_line(
                points[0],
                points[-1]
            )

            return

    # ========================================================
    # FINISH GESTURE DRAWING
    # ========================================================

    def finish_gesture_drawing(
        self
    ):

        if not self.gesture_drawing:

            self.canvas.set_gesture_cursor(
                None,
                False
            )

            return

        points = list(
            self.gesture_points
        )

        self.gesture_drawing = False

        self.gesture_points = []

        self.last_draw_point = None

        self.canvas.set_gesture_cursor(
            None,
            False
        )

        # ====================================================
        # AUTO SHAPE
        # ====================================================

        if (
            self.current_tool
            ==
            "pen"
            and
            len(points)
            >=
            MIN_SHAPE_POINTS
        ):

            self.auto_correct_shape(
                points
            )

    # ========================================================
    # AUTO SHAPE RECOGNITION
    # ========================================================

    def auto_correct_shape(
        self,
        points
    ):

        if len(points) < MIN_SHAPE_POINTS:

            return

        # ====================================================
        # REMOVE DUPLICATES
        # ====================================================

        clean = []

        for point in points:

            if not clean:

                clean.append(
                    point
                )

                continue

            previous = clean[-1]

            distance = math.sqrt(
                (
                    point.x()
                    -
                    previous.x()
                ) ** 2
                +
                (
                    point.y()
                    -
                    previous.y()
                ) ** 2
            )

            if distance >= 2:

                clean.append(
                    point
                )

        points = clean

        if len(points) < MIN_SHAPE_POINTS:

            return

        # ====================================================
        # BOUNDING BOX
        # ====================================================

        xs = [
            p.x()
            for p in points
        ]

        ys = [
            p.y()
            for p in points
        ]

        min_x = min(xs)

        max_x = max(xs)

        min_y = min(ys)

        max_y = max(ys)

        width = (
            max_x
            -
            min_x
        )

        height = (
            max_y
            -
            min_y
        )

        if width < 8 or height < 8:

            return

        # ====================================================
        # PATH LENGTH
        # ====================================================

        path_length = 0.0

        for i in range(
            1,
            len(points)
        ):

            dx = (
                points[i].x()
                -
                points[i - 1].x()
            )

            dy = (
                points[i].y()
                -
                points[i - 1].y()
            )

            path_length += math.sqrt(
                dx * dx
                +
                dy * dy
            )

        if path_length <= 0:

            return

        # ====================================================
        # END DISTANCE
        # ====================================================

        start = points[0]

        end = points[-1]

        end_distance = math.sqrt(
            (
                end.x()
                -
                start.x()
            ) ** 2
            +
            (
                end.y()
                -
                start.y()
            ) ** 2
        )

        # ====================================================
        # CLOSEDNESS
        # ====================================================

        diagonal = math.sqrt(
            width * width
            +
            height * height
        )

        if diagonal <= 0:

            return

        closed_ratio = (
            end_distance
            /
            diagonal
        )

        is_closed = (
            closed_ratio
            <
            0.30
        )

        # ====================================================
        # STRAIGHT LINE (open strokes)
        # ====================================================

        direct_ratio = (
            end_distance
            /
            path_length
        )

        if (
            not is_closed
            and
            direct_ratio >= 0.90
        ):

            self.replace_with_line(
                points[0],
                points[-1]
            )

            return

        # ====================================================
        # POLYGON TEST (triangle / square / rectangle)
        #
        # IMPORTANT: polygons are tested BEFORE the circle so a drawn
        # square / rectangle is NOT mis-detected as a circle.
        # ====================================================

        polygon = self.approximate_polygon(
            points
        )

        corner_count = len(
            polygon
        )

        # ----------------------------------------------------
        # TRIANGLE
        # ----------------------------------------------------

        if (
            is_closed
            and
            corner_count == 3
        ):

            self.replace_with_polygon(
                polygon,
                "triangle"
            )

            return

        # ----------------------------------------------------
        # SQUARE / RECTANGLE
        # ----------------------------------------------------

        if (
            is_closed
            and
            corner_count == 4
            and
            self.is_rectangle(
                polygon
            )
        ):

            self.replace_with_polygon(
                polygon,
                "rectangle"
            )

            return

        # ====================================================
        # CIRCLE
        # ====================================================

        circle_score = (
            self.calculate_circle_score(
                points,
                min_x,
                max_x,
                min_y,
                max_y
            )
        )

        if (
            is_closed
            and
            circle_score >= 0.72
        ):

            self.replace_with_circle(
                points
            )

            return

    # ========================================================
    # CIRCLE SCORE
    # ========================================================

    def calculate_circle_score(
        self,
        points,
        min_x,
        max_x,
        min_y,
        max_y
    ):

        width = (
            max_x
            -
            min_x
        )

        height = (
            max_y
            -
            min_y
        )

        if width <= 0 or height <= 0:

            return 0.0

        aspect_ratio = (
            min(width, height)
            /
            max(width, height)
        )

        # Circle should be reasonably round.
        if aspect_ratio < 0.65:

            return 0.0

        # ====================================================
        # CENTER
        # ====================================================

        center_x = (
            min_x
            +
            max_x
        ) / 2.0

        center_y = (
            min_y
            +
            max_y
        ) / 2.0

        radii = []

        for point in points:

            dx = (
                point.x()
                -
                center_x
            )

            dy = (
                point.y()
                -
                center_y
            )

            radius = math.sqrt(
                dx * dx
                +
                dy * dy
            )

            radii.append(
                radius
            )

        if not radii:

            return 0.0

        average_radius = (
            sum(radii)
            /
            len(radii)
        )

        if average_radius <= 2:

            return 0.0

        variance = sum(
            (
                radius
                -
                average_radius
            ) ** 2
            for radius in radii
        ) / len(radii)

        standard_deviation = math.sqrt(
            variance
        )

        radial_consistency = max(
            0.0,
            1.0
            -
            (
                standard_deviation
                /
                average_radius
            )
        )

        # ====================================================
        # CIRCULARITY
        # ====================================================

        contour = []

        for point in points:

            contour.append([
                [
                    point.x(),
                    point.y()
                ]
            ])

        contour = (
            cv2.UMat(
                cv2.array(
                    contour
                )
            )
            if False
            else None
        )

        # Use polygon perimeter/area manually.
        area = (
            math.pi
            *
            (
                average_radius
                ** 2
            )
        )

        perimeter = (
            2
            *
            math.pi
            *
            average_radius
        )

        circularity = (
            (
                4
                *
                math.pi
                *
                area
            )
            /
            (
                perimeter
                *
                perimeter
            )
        )

        # The theoretical value is 1.
        # Radial consistency carries more weight
        # for small hand-drawn circles.
        score = (
            aspect_ratio
            *
            0.35
            +
            radial_consistency
            *
            0.65
        )

        return score

    # ========================================================
    # APPROXIMATE POLYGON
    # ========================================================

    def approximate_polygon(
        self,
        points
    ):

        contour = []

        for point in points:

            contour.append([
                float(point.x()),
                float(point.y())
            ])

        contour = (
            np_array(contour)
        )

        epsilon = max(
            2.0,
            cv2.arcLength(
                contour,
                True
            )
            *
            0.035
        )

        approximation = cv2.approxPolyDP(
            contour,
            epsilon,
            True
        )

        return [
            QPoint(
                int(point[0][0]),
                int(point[0][1])
            )
            for point in approximation
        ]

    # ========================================================
    # RECTANGLE CHECK
    # ========================================================

    def is_rectangle(
        self,
        polygon
    ):

        if len(polygon) != 4:

            return False

        angles = []

        for i in range(4):

            p1 = polygon[
                i - 1
            ]

            p2 = polygon[
                i
            ]

            p3 = polygon[
                (i + 1) % 4
            ]

            v1x = (
                p1.x()
                -
                p2.x()
            )

            v1y = (
                p1.y()
                -
                p2.y()
            )

            v2x = (
                p3.x()
                -
                p2.x()
            )

            v2y = (
                p3.y()
                -
                p2.y()
            )

            mag1 = math.sqrt(
                v1x * v1x
                +
                v1y * v1y
            )

            mag2 = math.sqrt(
                v2x * v2x
                +
                v2y * v2y
            )

            if mag1 == 0 or mag2 == 0:

                return False

            cosine = (
                (
                    v1x * v2x
                    +
                    v1y * v2y
                )
                /
                (
                    mag1
                    *
                    mag2
                )
            )

            cosine = max(
                -1,
                min(
                    1,
                    cosine
                )
            )

            angle = math.degrees(
                math.acos(
                    cosine
                )
            )

            angles.append(
                angle
            )

        # Allow hand-drawn imperfections.
        for angle in angles:

            if not (
                70
                <=
                angle
                <=
                110
            ):

                return False

        return True

    # ========================================================
    # REPLACE WITH LINE
    # ========================================================

    def replace_with_line(
        self,
        start,
        end
    ):

        self.canvas.undo()

        painter = QPainter(
            self.canvas.canvas
            if hasattr(
                self.canvas,
                "canvas"
            )
            else self.canvas.canvas
        )

        painter.setRenderHint(
            QPainter.Antialiasing,
            True
        )

        color = QColor(
            self.current_color
        )

        color.setAlpha(
            int(
                self.opacity_slider.value()
                *
                255
                /
                100
            )
        )

        pen = QPen(
            color,
            self.brush_slider.value(),
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

        self.canvas.update()

    # ========================================================
    # REPLACE WITH CIRCLE
    # ========================================================

    def replace_with_circle(
        self,
        points
    ):

        self.canvas.undo()

        xs = [
            p.x()
            for p in points
        ]

        ys = [
            p.y()
            for p in points
        ]

        min_x = min(xs)

        max_x = max(xs)

        min_y = min(ys)

        max_y = max(ys)

        width = (
            max_x
            -
            min_x
        )

        height = (
            max_y
            -
            min_y
        )

        center_x = (
            min_x
            +
            max_x
        ) / 2.0

        center_y = (
            min_y
            +
            max_y
        ) / 2.0

        radius = (
            min(
                width,
                height
            )
            /
            2.0
        )

        painter = QPainter(
            self.canvas.canvas
        )

        painter.setRenderHint(
            QPainter.Antialiasing,
            True
        )

        color = QColor(
            self.current_color
        )

        color.setAlpha(
            int(
                self.opacity_slider.value()
                *
                255
                /
                100
            )
        )

        painter.setPen(
            QPen(
                color,
                self.brush_slider.value(),
                Qt.SolidLine,
                Qt.RoundCap
            )
        )

        painter.setBrush(
            Qt.NoBrush
        )

        painter.drawEllipse(
            QPoint(
                int(center_x),
                int(center_y)
            ),
            int(radius),
            int(radius)
        )

        painter.end()

        self.canvas.update()

    # ========================================================
    # REPLACE WITH POLYGON
    # ========================================================

    def replace_with_polygon(
        self,
        polygon,
        shape
    ):

        if len(polygon) < 3:

            return

        self.canvas.undo()

        painter = QPainter(
            self.canvas.canvas
        )

        painter.setRenderHint(
            QPainter.Antialiasing,
            True
        )

        color = QColor(
            self.current_color
        )

        color.setAlpha(
            int(
                self.opacity_slider.value()
                *
                255
                /
                100
            )
        )

        painter.setPen(
            QPen(
                color,
                self.brush_slider.value(),
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin
            )
        )

        painter.setBrush(
            Qt.NoBrush
        )

        qpolygon = QPolygon(
            polygon
        )

        painter.drawPolygon(
            qpolygon
        )

        painter.end()

        self.canvas.update()

    # ========================================================
    # SAVE
    # ========================================================

    def save_whiteboard(
        self
    ):

        default_dir = (
            QStandardPaths.writableLocation(
                QStandardPaths.PicturesLocation
            )
            or
            os.path.expanduser("~")
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

        if not file_path.lower().endswith(
            ".png"
        ):

            file_path += ".png"

        try:

            self.canvas.canvas.save(
                file_path,
                "PNG"
            )

            # Also keep a copy in the app's Saved Files folder so the file
            # shows up in the side-bar "Saved Files" page.
            try:

                from pathlib import Path

                import shutil

                saved_dir = (
                    Path(os.getcwd())
                    / "saved_files"
                    / "whiteboards"
                )

                saved_dir.mkdir(
                    parents=True,
                    exist_ok=True
                )

                destination = (
                    saved_dir
                    / Path(file_path).name
                )

                shutil.copyfile(
                    file_path,
                    str(destination)
                )

                # Refresh the Saved Files page so the new file appears.
                page = getattr(
                    self.parent_window,
                    "saved_files",
                    None
                )

                if page is not None and hasattr(
                    page, "refresh_files"
                ):

                    page.refresh_files()

            except Exception:

                pass

            QMessageBox.information(
                self,
                "Whiteboard Saved",
                "Your whiteboard has been saved to:\n\n"
                +
                file_path
                +
                "\n\nIt also appears in the Saved Files page."
            )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Save Error",
                f"Could not save the whiteboard.\n\n{e}"
            )

    # ========================================================
    # CAMERA DISPLAY
    # ========================================================

    def display_camera(
        self,
        frame
    ):

        frame_rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        height, width, channels = (
            frame_rgb.shape
        )

        bytes_per_line = (
            channels
            *
            width
        )

        from PyQt5.QtGui import QImage

        image = QImage(
            frame_rgb.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888
        )

        pixmap = QPixmap.fromImage(
            image
        )

        pixmap = pixmap.scaled(
            CAMERA_PREVIEW_WIDTH - 4,
            CAMERA_PREVIEW_HEIGHT - 4,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.camera_label.setPixmap(
            pixmap
        )

        self.camera_label.raise_()

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

        if (
            index is not None
            and
            index != self.camera_index
        ):

            self.stop_camera()

            self.camera_index = index

            QTimer.singleShot(
                200,
                self.start_camera
            )

    # ========================================================
    # CAMERA NAME
    # ========================================================

    def updateCameraName(
        self,
        name
    ):

        self.active_camera_name = name

    # ========================================================
    # CLOSE
    # ========================================================

    def closeEvent(
        self,
        event
    ):

        self.stop_camera()

        if self.hands:

            self.hands.close()

        event.accept()


# ============================================================
# NUMPY HELPER
# ============================================================

def np_array(data):
    """
    Small helper so the code only needs numpy here.
    """

    import numpy as np

    return np.array(
        data,
        dtype=np.float32
    )