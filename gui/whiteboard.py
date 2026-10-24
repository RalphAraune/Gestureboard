import os
import math
import time

import cv2

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
    QButtonGroup,
    QGridLayout,
    QToolButton,
    QShortcut,
)
from PyQt5.QtCore import (
    Qt,
    QPoint,
    QPointF,
    QRect,
    QTimer,
    QStandardPaths,
    QSize,
    QEvent,
)
from PyQt5.QtGui import (
    QPainter,
    QPen,
    QColor,
    QPixmap,
    QCursor,
    QPolygon,
    QPolygonF,
    QBrush,
    QIcon,
    QKeySequence,
)


# ============================================================
# SETTINGS
# ============================================================

CAMERA_PREVIEW_WIDTH = 140
CAMERA_PREVIEW_HEIGHT = 105

# How often the page checks the Virtual Mouse for a new camera frame.
# The hand is only processed when a NEW frame has arrived, so a short
# interval just means less delay, not more work.
POLL_INTERVAL_MS = 15

# MediaPipe hand landmark indexes.
WRIST = 0
INDEX_PIP, INDEX_TIP = 6, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_TIP = 9, 10, 12
RING_PIP, RING_TIP = 14, 16
PINKY_PIP, PINKY_TIP = 18, 20

# Index + middle fingertip gap, as a fraction of the palm length.
# Tips must be this close to START drawing, and may part a little
# (up to KEEP) before the stroke ends. Spreading them wider lifts
# the pen.
DRAW_GAP_START = 0.32
DRAW_GAP_KEEP = 0.40

# A finger counts as straight when its tip is this much further from
# the wrist than its middle knuckle.
FINGER_UP_RATIO = 1.2

# Frames in a row without the draw gesture before the pen lifts.
# 2 frames (~60 ms) hides a single bad detection without making the
# pen feel slow to stop.
DRAW_RELEASE_FRAMES = 2

# Lift the pen when no new camera frame arrives for this long.
HAND_TIMEOUT = 0.3

# Minimum points required before automatic shape recognition.
MIN_SHAPE_POINTS = 12

# Strokes smaller than this (bounding-box diagonal, px) are left as
# drawn, so handwriting such as "o" or "D" is never turned into shapes.
MIN_SHAPE_SIZE = 60


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

        # Shape mode: "auto" recognises the shape, "free" keeps every
        # stroke as drawn, otherwise it forces the chosen shape (see
        # SHAPE_LABELS).
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

        old = self.gesture_cursor_rect()

        self.gesture_cursor_pos = point

        self.show_gesture_cursor = visible

        # Repaint only where the cursor was and where it is now;
        # a full-board repaint every camera frame is what made
        # hand drawing lag.
        new = self.gesture_cursor_rect()

        if old is not None:
            self.update(old)

        if new is not None:
            self.update(new)

    def gesture_cursor_radius(self):

        return max(8, int(self.brush_size * 1.8))

    def gesture_cursor_rect(self):

        if not (self.show_gesture_cursor and self.gesture_cursor_pos):
            return None

        reach = self.gesture_cursor_radius() + 8

        return QRect(
            self.gesture_cursor_pos.x() - reach,
            self.gesture_cursor_pos.y() - reach,
            reach * 2,
            reach * 2,
        )

    def ring_rect(self):
        """Area covered by the circle (brush) cursor, or None."""

        if not (self.cursor_visible and self.mouse_pos is not None):
            return None

        reach = max(8, int(self.current_width() / 2) + 5) + 4

        return QRect(
            self.mouse_pos.x() - reach,
            self.mouse_pos.y() - reach,
            reach * 2,
            reach * 2,
        )

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
    # REVERT STROKE
    #
    # Puts back the board as it was before the current stroke,
    # without touching undo / redo. Used to swap a rough stroke for
    # a perfect shape: one Undo then removes the shape completely.
    # ========================================================

    def revert_to_last_state(self):

        if not self.undo_stack:
            return

        self.canvas = self.undo_stack[-1].copy()

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
        if self.tool == "pen" and self.shape_mode not in ("auto", "free"):

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
        old_ring = self.ring_rect()

        self.mouse_pos = current_point

        self.cursor_visible = True

        # Live shape preview while dragging.
        if self._shape_dragging:

            self._shape_current = current_point

            self.update()

            event.accept()

            return

        # Repaint only the old and new cursor ring.
        if old_ring is not None:
            self.update(old_ring)

        self.update(self.ring_rect())

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

        pen = self.make_pen()

        painter.setPen(
            pen
        )

        painter.drawLine(
            start,
            end
        )

        painter.end()

        # Repaint just the segment, not the whole board.
        reach = int(pen.widthF() / 2) + 3

        self.update(
            QRect(start, end).normalized().adjusted(
                -reach, -reach, reach, reach
            )
        )

    # ========================================================
    # PEN FOR THE ACTIVE TOOL
    # ========================================================

    def make_pen(
        self,
        tool=None
    ):

        tool = tool or self.tool

        if tool == "eraser":

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

        elif tool == "highlighter":

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

        return pen

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

        # ====================================================
        # DRAWING
        #
        # The canvas pixmap is opaque white and always covers the
        # widget, so only the repainted area is copied across.
        # ====================================================

        dirty = event.rect()

        painter.fillRect(
            dirty,
            QColor("#FFFFFF")
        )

        painter.drawPixmap(
            dirty,
            self.canvas,
            dirty
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

            radius = self.gesture_cursor_radius()

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

            # Same geometry as the shape that is committed on release.
            paint_shape(
                painter,
                drag_shape(
                    self.shape_mode,
                    (shape_start.x(), shape_start.y()),
                    (shape_end.x(), shape_end.y())
                )
            )

        # ====================================================
        # CIRCLE (BRUSH) CURSOR
        # Size follows the current tool width. Drawn as a large,
        # semi-transparent ring so it never looks like a black blob.
        # ====================================================

        # Hidden while the hand draws, so only one cursor shows.
        if (
            self.cursor_visible
            and self.mouse_pos is not None
            and self.tool in ("pen", "highlighter", "eraser")
            and not self.show_gesture_cursor
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
# SHAPE GEOMETRY
#
# Shapes are plain tuples, so one description drives the drag
# preview, the shapes picked in the Shapes menu and auto-shape:
#
#   ("line", p1, p2)            ("arrow", p1, p2)
#   ("polygon", [p, ...])       ("ellipse", cx, cy, rx, ry, angle)
#
# Points are (x, y) floats and angles are in degrees.
# ============================================================

SHAPE_LABELS = {
    "auto": "Automatic",
    "free": "Freehand",
    "line": "Line",
    "arrow": "Arrow",
    "circle": "Circle",
    "oval": "Oval",
    "square": "Square",
    "rectangle": "Rectangle",
    "triangle": "Triangle",
    "diamond": "Diamond",
    "pentagon": "Pentagon",
    "hexagon": "Hexagon",
    "star": "Star",
}


def _distance(a, b):

    return math.hypot(a[0] - b[0], a[1] - b[1])


def _centre(points):

    return (
        sum(p[0] for p in points) / len(points),
        sum(p[1] for p in points) / len(points),
    )


def _path_length(points, closed=False):

    total = sum(
        _distance(points[i - 1], points[i])
        for i in range(1, len(points))
    )

    if closed and len(points) > 1:
        total += _distance(points[-1], points[0])

    return total


def _resample(points, count):
    """Return `count` points spaced evenly along the stroke.

    Hand and mouse strokes bunch points up where the pen slows down;
    even spacing keeps slow corners from outweighing fast edges.
    """

    step = _path_length(points) / (count - 1)

    if step <= 0:
        return list(points)

    result = [points[0]]
    carried = 0.0
    previous = points[0]

    for point in points[1:]:

        segment = _distance(previous, point)

        while segment > 0 and carried + segment >= step:

            t = (step - carried) / segment

            previous = (
                previous[0] + (point[0] - previous[0]) * t,
                previous[1] + (point[1] - previous[1]) * t,
            )

            result.append(previous)

            segment = _distance(previous, point)
            carried = 0.0

        carried += segment
        previous = point

    while len(result) < count:
        result.append(points[-1])

    return result[:count]


def _segment_distance(p, a, b):

    dx, dy = b[0] - a[0], b[1] - a[1]
    length_sq = dx * dx + dy * dy

    if length_sq == 0:
        return _distance(p, a)

    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length_sq
    t = max(0.0, min(1.0, t))

    return _distance(p, (a[0] + dx * t, a[1] + dy * t))


def _polygon_error(points, corners):
    """Mean distance from the stroke to the polygon's outline."""

    edges = [
        (corners[i - 1], corners[i])
        for i in range(len(corners))
    ]

    return sum(
        min(_segment_distance(p, a, b) for a, b in edges)
        for p in points
    ) / len(points)


def _corner_angle(previous, corner, following):
    """Inside angle at `corner`, in degrees."""

    v1 = (previous[0] - corner[0], previous[1] - corner[1])
    v2 = (following[0] - corner[0], following[1] - corner[1])

    size = math.hypot(*v1) * math.hypot(*v2)

    if size == 0:
        return 180.0

    cosine = (v1[0] * v2[0] + v1[1] * v2[1]) / size

    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def _find_corners(loop):
    """Corners of a closed stroke.

    Wobbles that only bend the line a little, and two corners found
    right next to each other (where the stroke starts and ends), are
    merged so a square gives 4 corners, not 5 or 6.
    """

    contour = np_array(loop).reshape(-1, 1, 2)

    epsilon = cv2.arcLength(contour, True) * 0.035

    corners = [
        (float(p[0][0]), float(p[0][1]))
        for p in cv2.approxPolyDP(contour, epsilon, True)
    ]

    perimeter = _path_length(loop, closed=True)

    changed = True

    while changed and len(corners) > 3:

        changed = False
        count = len(corners)

        for i in range(count):

            previous = corners[i - 1]
            corner = corners[i]
            following = corners[(i + 1) % count]

            if _distance(corner, following) < perimeter * 0.05:

                corners[i] = (
                    (corner[0] + following[0]) / 2.0,
                    (corner[1] + following[1]) / 2.0,
                )

                del corners[(i + 1) % count]
                changed = True
                break

            if _corner_angle(previous, corner, following) > 155:

                del corners[i]
                changed = True
                break

    return corners


def _fit_ellipse(loop):
    """Best ellipse for a closed stroke: (cx, cy, rx, ry, angle, error)."""

    (cx, cy), (width, height), angle = cv2.fitEllipse(np_array(loop))

    rx, ry = width / 2.0, height / 2.0

    if rx <= 1 or ry <= 1:
        return None

    cos_a = math.cos(math.radians(angle))
    sin_a = math.sin(math.radians(angle))

    error = 0.0

    for x, y in loop:

        dx, dy = x - cx, y - cy

        # Into the ellipse's own axes.
        u = dx * cos_a + dy * sin_a
        v = -dx * sin_a + dy * cos_a

        scale = math.hypot(u / rx, v / ry)

        if scale > 0:
            # Distance to the outline along the ray from the centre.
            error += math.hypot(u, v) * abs(1.0 - 1.0 / scale)

    return cx, cy, rx, ry, angle, error / len(loop)


def _snap(angle, step, tolerance):
    """Snap `angle` to the nearest multiple of `step` when close to it."""

    nearest = round(angle / step) * step

    return nearest if abs(angle - nearest) <= tolerance else angle


def _rotation(corners, cx, cy, sides):
    """Angle of the first corner of a near-regular polygon (degrees)."""

    s = sum(
        math.sin(sides * math.atan2(y - cy, x - cx))
        for x, y in corners
    )

    c = sum(
        math.cos(sides * math.atan2(y - cy, x - cx))
        for x, y in corners
    )

    return math.degrees(math.atan2(s, c)) / sides


def _upright(rotation, sides, targets=(-90.0,), tolerance=12.0):
    """Stand a regular shape up straight when it is nearly upright.

    -90 degrees points a corner straight up (screen y grows down).
    """

    step = 360.0 / sides

    for target in targets:

        offset = (rotation - target + step / 2.0) % step - step / 2.0

        if abs(offset) <= tolerance:
            return target

    return rotation


def _regular_polygon(cx, cy, radius, sides, rotation, turn=1):
    """Corners of a regular polygon. `turn` 2 joins every second
    corner, which turns 5 corners into a five-pointed star."""

    return [
        (
            cx + radius * math.cos(math.radians(rotation + i * turn * 360.0 / sides)),
            cy + radius * math.sin(math.radians(rotation + i * turn * 360.0 / sides)),
        )
        for i in range(sides)
    ]


def _star_outline(cx, cy, outer, inner, rotation):
    """Outline of a five-pointed star (10 corners)."""

    points = []

    for i in range(5):

        tip = math.radians(rotation + i * 72.0)
        dip = tip + math.radians(36.0)

        points.append((cx + outer * math.cos(tip), cy + outer * math.sin(tip)))
        points.append((cx + inner * math.cos(dip), cy + inner * math.sin(dip)))

    return points


def _straight_line(start, end):
    """A line from `start`, snapped flat, upright or 45 degrees when close."""

    length = _distance(start, end)

    angle = _snap(
        math.degrees(math.atan2(end[1] - start[1], end[0] - start[0])),
        45.0,
        7.0,
    )

    return (
        "line",
        start,
        (
            start[0] + length * math.cos(math.radians(angle)),
            start[1] + length * math.sin(math.radians(angle)),
        ),
    )


def _perfect_triangle(corners):

    sides = [
        _distance(corners[i], corners[(i + 1) % 3])
        for i in range(3)
    ]

    if min(sides) <= 0:
        return None

    angles = [
        _corner_angle(corners[i - 1], corners[i], corners[(i + 1) % 3])
        for i in range(3)
    ]

    cx, cy = _centre(corners)

    # All sides about the same: equilateral, pointing up or down.
    if max(sides) / min(sides) < 1.25:

        radius = sum(_distance((cx, cy), p) for p in corners) / 3.0

        rotation = _upright(
            _rotation(corners, cx, cy, 3), 3, (-90.0, 90.0), 20.0
        )

        return "Triangle", ("polygon", _regular_polygon(cx, cy, radius, 3, rotation))

    # One corner close to square: a right triangle with an exact
    # 90 degree corner, lined up with the board when nearly level.
    right = min(range(3), key=lambda i: abs(angles[i] - 90.0))

    if abs(angles[right] - 90.0) <= 15:

        p = corners[right]
        a = corners[right - 1]
        b = corners[(right + 1) % 3]

        heading = math.radians(
            _snap(math.degrees(math.atan2(a[1] - p[1], a[0] - p[0])), 90.0, 15.0)
        )

        ux, uy = math.cos(heading), math.sin(heading)

        # Keep the second leg on the side it was drawn.
        side = 1 if (b[0] - p[0]) * -uy + (b[1] - p[1]) * ux >= 0 else -1

        la, lb = _distance(p, a), _distance(p, b)

        return "Right triangle", (
            "polygon",
            [
                p,
                (p[0] + ux * la, p[1] + uy * la),
                (p[0] - uy * lb * side, p[1] + ux * lb * side),
            ],
        )

    # Two sides about the same: a symmetric (isosceles) triangle.
    for i in range(3):

        apex = corners[i]
        left = corners[i - 1]
        right_corner = corners[(i + 1) % 3]

        s1, s2 = _distance(apex, left), _distance(apex, right_corner)

        if abs(s1 - s2) / max(s1, s2) < 0.15:

            mx = (left[0] + right_corner[0]) / 2.0
            my = (left[1] + right_corner[1]) / 2.0

            axis = math.radians(
                _snap(math.degrees(math.atan2(apex[1] - my, apex[0] - mx)), 90.0, 15.0)
            )

            ux, uy = math.cos(axis), math.sin(axis)

            height = _distance(apex, (mx, my))
            half = _distance(left, right_corner) / 2.0

            return "Triangle", (
                "polygon",
                [
                    (mx + ux * height, my + uy * height),
                    (mx + uy * half, my - ux * half),
                    (mx - uy * half, my + ux * half),
                ],
            )

    # Any other triangle: keep its corners, with straight sides.
    return "Triangle", ("polygon", corners)


def _perfect_quad(corners, loop):

    angles = [
        _corner_angle(corners[i - 1], corners[i], corners[(i + 1) % 4])
        for i in range(4)
    ]

    sides = [
        _distance(corners[i], corners[(i + 1) % 4])
        for i in range(4)
    ]

    if min(sides) <= 0:
        return None

    # Square corners: a square or rectangle, the size of the stroke.
    if all(70 <= a <= 110 for a in angles):

        (cx, cy), (w, h), angle = cv2.minAreaRect(np_array(loop))

        turns = round(angle / 90.0)

        if abs(angle - turns * 90.0) <= 12:

            angle = 0.0

            # A box turned 90 degrees is the same box, tall <-> wide.
            if turns % 2:
                w, h = h, w

        if min(w, h) / max(w, h) >= 0.85:

            w = h = (w + h) / 2.0
            name = "Square" if angle == 0.0 else "Diamond"

        else:

            name = "Rectangle"

        box = cv2.boxPoints(((cx, cy), (w, h), angle))

        return name, ("polygon", [(float(x), float(y)) for x, y in box])

    # Four equal-ish sides with slanted corners: a diamond.
    if max(sides) / min(sides) < 1.3:

        xs = [p[0] for p in corners]
        ys = [p[1] for p in corners]

        cx = (min(xs) + max(xs)) / 2.0
        cy = (min(ys) + max(ys)) / 2.0

        w = max(xs) - min(xs)
        h = max(ys) - min(ys)

        if min(w, h) / max(w, h) >= 0.85:
            w = h = (w + h) / 2.0

        return "Diamond", (
            "polygon",
            [(cx, cy - h / 2), (cx + w / 2, cy), (cx, cy + h / 2), (cx - w / 2, cy)],
        )

    # Any other four-sided shape: keep its corners, straight sides.
    return "Shape", ("polygon", corners)


def _perfect_regular(corners, name):
    """Pentagon or hexagon, or a five-pointed star drawn in one line."""

    sides = len(corners)

    cx, cy = _centre(corners)

    radius = sum(_distance((cx, cy), p) for p in corners) / sides

    # A star drawn in one line jumps about 144 degrees around the
    # centre from tip to tip; a pentagon steps about 72.
    if sides == 5:

        bearings = [math.atan2(y - cy, x - cx) for x, y in corners]

        steps = [
            abs((math.degrees(bearings[(i + 1) % 5] - bearings[i]) + 180) % 360 - 180)
            for i in range(5)
        ]

        if all(step > 108 for step in steps):

            rotation = _upright(_rotation(corners, cx, cy, 5), 5, (-90.0,), 15.0)

            return "Star", (
                "polygon",
                _regular_polygon(cx, cy, radius, 5, rotation, turn=2),
            )

    targets = (-90.0,) if sides == 5 else (-90.0, 0.0)

    rotation = _upright(_rotation(corners, cx, cy, sides), sides, targets)

    return name, ("polygon", _regular_polygon(cx, cy, radius, sides, rotation))


def _perfect_outline_star(corners):
    """A star drawn around its outline: 10 corners, tips and dips."""

    cx, cy = _centre(corners)

    distances = [_distance((cx, cy), p) for p in corners]

    tips, dips = distances[0::2], distances[1::2]
    tip_corners = corners[0::2]

    if sum(tips) < sum(dips):
        tips, dips = dips, tips
        tip_corners = corners[1::2]

    # Tips and dips must alternate clearly.
    if min(tips) <= max(dips) or max(dips) <= 0:
        return None

    outer = sum(tips) / 5.0
    inner = sum(dips) / 5.0

    rotation = _upright(_rotation(tip_corners, cx, cy, 5), 5, (-90.0,), 15.0)

    return "Star", ("polygon", _star_outline(cx, cy, outer, inner, rotation))


def _perfect_ellipse(fit, loop):

    cx, cy, rx, ry, angle, _ = fit

    # Nearly round: a true circle, as big as the stroke.
    if min(rx, ry) / max(rx, ry) >= 0.8:

        radius = sum(_distance((cx, cy), p) for p in loop) / len(loop)

        return "Circle", ("ellipse", cx, cy, radius, radius, 0.0)

    return "Oval", ("ellipse", cx, cy, rx, ry, _snap(angle, 90.0, 15.0))


def recognise_shape(points):
    """Return (name, shape) for a rough stroke, or None to keep it.

    Each candidate outline (polygon or ellipse) is measured against
    the stroke, and the closest fit wins. Strokes that fit nothing
    well, or are small like handwriting, are left exactly as drawn.
    """

    clean = []

    for point in points:
        if not clean or _distance(point, clean[-1]) >= 2:
            clean.append(point)

    if len(clean) < MIN_SHAPE_POINTS:
        return None

    xs = [p[0] for p in clean]
    ys = [p[1] for p in clean]

    diagonal = math.hypot(max(xs) - min(xs), max(ys) - min(ys))

    if diagonal < MIN_SHAPE_SIZE:
        return None

    length = _path_length(clean)
    gap = _distance(clean[0], clean[-1])

    # Open and nearly straight: a line.
    if gap >= length * 0.92:
        return "Line", _straight_line(clean[0], clean[-1])

    # Open curves (ticks, waves, letters) stay as drawn.
    if gap > diagonal * 0.3:
        return None

    loop = _resample(clean + [clean[0]], 97)[:-1]

    corners = _find_corners(loop)
    count = len(corners)

    polygon_error = (
        _polygon_error(loop, corners) / diagonal if count >= 3 else 1.0
    )

    fit = _fit_ellipse(loop)

    ellipse_error = fit[5] / diagonal if fit else 1.0

    if 3 <= count <= 6 and polygon_error < 0.05 and polygon_error < ellipse_error:

        if count == 3:
            result = _perfect_triangle(corners)
        elif count == 4:
            result = _perfect_quad(corners, loop)
        else:
            result = _perfect_regular(
                corners, "Pentagon" if count == 5 else "Hexagon"
            )

        if result:
            return result

    if count == 10 and polygon_error < 0.05:

        result = _perfect_outline_star(corners)

        if result:
            return result

    if fit and ellipse_error < 0.06:
        return _perfect_ellipse(fit, loop)

    return None


def drag_shape(mode, start, end):
    """The shape picked in the Shapes menu, fitted to a start / end drag."""

    x0, y0 = start
    x1, y1 = end

    left, right = min(x0, x1), max(x0, x1)
    top, bottom = min(y0, y1), max(y0, y1)

    w, h = right - left, bottom - top
    cx, cy = (left + right) / 2.0, (top + bottom) / 2.0

    if mode == "arrow":
        return ("arrow", start, end)

    if mode in ("circle", "square"):

        # Even sides: grow from the start corner towards the pointer.
        side = max(w, h)

        x2 = x0 + side * (1 if x1 >= x0 else -1)
        y2 = y0 + side * (1 if y1 >= y0 else -1)

        l, r = min(x0, x2), max(x0, x2)
        t, b = min(y0, y2), max(y0, y2)

        if mode == "circle":
            return ("ellipse", (l + r) / 2.0, (t + b) / 2.0, side / 2.0, side / 2.0, 0.0)

        return ("polygon", [(l, t), (r, t), (r, b), (l, b)])

    if mode == "oval":
        return ("ellipse", cx, cy, w / 2.0, h / 2.0, 0.0)

    if mode == "rectangle":
        return ("polygon", [(left, top), (right, top), (right, bottom), (left, bottom)])

    if mode == "triangle":
        return ("polygon", [(cx, top), (right, bottom), (left, bottom)])

    if mode == "diamond":
        return ("polygon", [(cx, top), (right, cy), (cx, bottom), (left, cy)])

    radius = min(w, h) / 2.0

    if mode == "pentagon":
        return ("polygon", _regular_polygon(cx, cy, radius, 5, -90.0))

    if mode == "hexagon":
        return ("polygon", _regular_polygon(cx, cy, radius, 6, 0.0))

    if mode == "star":
        return ("polygon", _star_outline(cx, cy, radius, radius * 0.4, -90.0))

    return ("line", start, end)


def paint_shape(painter, shape):
    """Draw a shape tuple with the painter's current pen."""

    kind = shape[0]

    if kind in ("line", "arrow"):

        a = QPointF(*shape[1])
        b = QPointF(*shape[2])

        painter.drawLine(a, b)

        length = _distance(shape[1], shape[2])

        if kind == "arrow" and length >= 1:

            head = min(length * 0.4, max(16.0, painter.pen().widthF() * 4))
            angle = math.atan2(b.y() - a.y(), b.x() - a.x())

            for side in (-1, 1):

                spread = angle + math.pi + side * math.radians(28)

                painter.drawLine(
                    b,
                    QPointF(
                        b.x() + head * math.cos(spread),
                        b.y() + head * math.sin(spread),
                    ),
                )

    elif kind == "polygon":

        painter.drawPolygon(
            QPolygonF([QPointF(x, y) for x, y in shape[1]])
        )

    elif kind == "ellipse":

        _, cx, cy, rx, ry, angle = shape

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(angle)
        painter.drawEllipse(QPointF(0, 0), rx, ry)
        painter.restore()


# ============================================================
# WHITEBOARD PAGE
# ============================================================

# ============================================================
# TOOL ICONS
#
# One line-icon set (24 x 24 grid, rounded 1.8 px strokes), the
# same style as the sidebar, instead of mixed Unicode symbols.
# ============================================================

def _tool_path(name):

    from PyQt5.QtGui import QPainterPath, QTransform
    from PyQt5.QtCore import QPointF, QRectF

    path = QPainterPath()

    if name == "select":
        path.moveTo(6, 4); path.lineTo(6, 18.5); path.lineTo(9.8, 15)
        path.lineTo(12.6, 20.5); path.lineTo(15, 19.4); path.lineTo(12.3, 14)
        path.lineTo(17.5, 13.6); path.closeSubpath()

    elif name == "pen":
        path.moveTo(5, 19); path.lineTo(6, 15); path.lineTo(15.5, 5.5)
        path.lineTo(18.5, 8.5); path.lineTo(9, 18); path.closeSubpath()
        path.moveTo(13.5, 7.5); path.lineTo(16.5, 10.5)

    elif name == "highlighter":
        path.moveTo(9, 13); path.lineTo(15, 7); path.lineTo(19, 11)
        path.lineTo(13, 17); path.closeSubpath()
        path.moveTo(9, 13); path.lineTo(6.5, 17.5); path.lineTo(10, 17.5)
        path.lineTo(13, 17)
        path.moveTo(4, 21); path.lineTo(20, 21)

    elif name == "eraser":
        path.moveTo(4.5, 14.5); path.lineTo(11.5, 7.5); path.lineTo(17.5, 13.5)
        path.lineTo(12.5, 18.5); path.lineTo(8.5, 18.5); path.closeSubpath()
        path.moveTo(8, 11); path.lineTo(14, 17)
        path.moveTo(12.5, 18.5); path.lineTo(20, 18.5)

    elif name == "shape":
        path.addRoundedRect(QRectF(3.5, 10, 10, 10), 1.5, 1.5)
        path.addEllipse(QPointF(15.5, 8.5), 5, 5)

    elif name in ("undo", "redo"):
        path.moveTo(9, 5); path.lineTo(5, 9); path.lineTo(9, 13)
        path.moveTo(5, 9); path.lineTo(14, 9)
        path.cubicTo(17.5, 9, 20, 11.5, 20, 14.5)
        path.cubicTo(20, 17.5, 17.5, 19.5, 14.5, 19.5)
        path.lineTo(10, 19.5)

        if name == "redo":
            path = QTransform(-1, 0, 0, 1, 24, 0).map(path)

    elif name == "clear":
        path.moveTo(4.5, 7); path.lineTo(19.5, 7)
        path.moveTo(9, 7); path.lineTo(9.6, 4.5); path.lineTo(14.4, 4.5); path.lineTo(15, 7)
        path.moveTo(6.5, 7); path.lineTo(7.5, 20); path.lineTo(16.5, 20); path.lineTo(17.5, 7)
        path.moveTo(10, 10.5); path.lineTo(10, 16.5)
        path.moveTo(14, 10.5); path.lineTo(14, 16.5)

    elif name == "save":
        path.moveTo(12, 4); path.lineTo(12, 14.5)
        path.moveTo(7.5, 10); path.lineTo(12, 14.5); path.lineTo(16.5, 10)
        path.moveTo(4.5, 15); path.lineTo(4.5, 19.5); path.lineTo(19.5, 19.5); path.lineTo(19.5, 15)

    return path


def tool_pixmap(name, color, size=20):

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
    painter.drawPath(_tool_path(name))
    painter.end()

    return pixmap


def tool_icon(name, color, size=20):

    return QIcon(tool_pixmap(name, color, size))


# ============================================================
# BRUSH PREVIEW
#
# A dot showing exactly what the next stroke looks like: the picked
# colour, at the brush size and opacity.
# ============================================================

class BrushPreview(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setFixedSize(40, 40)
        self.setToolTip("Current brush")

        self._color = QColor("#172033")
        self._size = 4
        self._opacity = 100
        self._ring = QColor("#BED2E9")

    def set_ring(self, color):

        self._ring = QColor(color)
        self.update()

    def set_brush(self, color, size, opacity):

        self._color = QColor(color)
        self._size = size
        self._opacity = opacity
        self.update()

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # White well, like a dab on the board itself.
        painter.setPen(QPen(self._ring, 1))
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(QRect(1, 1, self.width() - 2, self.height() - 2))

        color = QColor(self._color)
        color.setAlphaF(self._opacity / 100.0)

        diameter = max(3.0, min(32.0, self._size * 1.5))

        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(
            int(self.width() / 2 - diameter / 2),
            int(self.height() / 2 - diameter / 2),
            int(diameter),
            int(diameter),
        )

        painter.end()


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
        # GESTURE STATE
        #
        # The hand comes from the Virtual Mouse (it owns the camera
        # and MediaPipe); this page only reads each new frame's hand.
        # ====================================================

        # Capture time of the last Virtual Mouse frame handled here.
        self._last_stamp = None

        self._last_hand_time = 0.0

        # Frames in a row without the draw gesture (see
        # DRAW_RELEASE_FRAMES).
        self._release_frames = 0

        # Last status / camera pill shown, so the pills are only
        # re-styled when they actually change.
        self._status_shown = None

        self._camera_shown = None

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
                background-color: #0E2F76;
                border: 2px solid #FFFFFF;
                border-radius: 10px;
                color: #C9D8EE;
                font-size: 10px;
                font-weight: 600;
            }
        """)

        self.camera_label.setAlignment(
            Qt.AlignCenter
        )

        self.camera_label.setWordWrap(
            True
        )

        self.camera_label.setText(
            "Camera"
        )

        self.camera_label.raise_()

        # ====================================================
        # BUILD UI
        # ====================================================

        self.setup_ui()

        from widgets import page_background

        page_background.clear_layers(self)

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

        # Watch the Virtual Mouse for new frames (preview + hand).
        if not self.camera_timer.isActive():

            self.camera_timer.start(POLL_INTERVAL_MS)

    def update_camera_status(self):
        """Reflect the Virtual Mouse camera state in the header pill."""

        if not hasattr(self, "camera_status"):
            return

        vmouse = getattr(
            self.parent_window, "virtual_mouse", None
        )

        running = bool(
            vmouse is not None
            and getattr(vmouse, "camera_running", False)
        )

        # Called on every poll: only re-style when the state flips.
        if running == self._camera_shown:
            return

        self._camera_shown = running

        self.camera_status.setText(
            "●  Camera on" if running else "●  Camera off"
        )
        self.camera_status.setProperty("on", bool(running))
        self.camera_status.style().unpolish(self.camera_status)
        self.camera_status.style().polish(self.camera_status)

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

        if getattr(self, "hint_chips", None):
            needed = sum(c.sizeHint().width() + 8 for c in self.hint_chips)
            self._reflow_hints(
                len(self.hint_chips) if needed <= self.width() - 64 else 2
            )

    # ========================================================
    # POSITION CAMERA
    # ========================================================

    def position_camera_preview(self):

        margin = 14

        frame = getattr(self, "canvas_frame", None)

        if frame is not None:
            area = frame.geometry()
        else:
            area = self.rect()

        x = area.right() - CAMERA_PREVIEW_WIDTH - margin
        y = area.bottom() - CAMERA_PREVIEW_HEIGHT - margin

        self.camera_label.move(
            max(0, x),
            max(0, y)
        )

        self.camera_label.raise_()

    # ========================================================
    # BACKGROUND
    # ========================================================

    def paintEvent(self, event):

        from widgets import page_background

        page_background.paint_page_background(self, self._page_colors)

    # ========================================================
    # SETUP UI
    #
    # One tool dock above the board: tools, history, colours and
    # Save on top; brush size, opacity, a live brush preview and the
    # gesture status underneath. Gesture hints sit under the board.
    # ========================================================

    SWATCHES = [
        ("#172033", "Ink"),
        ("#F04444", "Red"),
        ("#2876E8", "Blue"),
        ("#28C76F", "Green"),
        ("#FFB020", "Yellow"),
        ("#FF8B32", "Orange"),
        ("#9B51E0", "Purple"),
    ]

    def setup_ui(
        self
    ):

        from widgets import page_background

        # Same soft-blue page as Saved Files (painted in paintEvent);
        # apply_theme() swaps in the dark surfaces when needed.
        self._page_colors = page_background.page_colors()

        # Tool buttons and swatches are remembered so apply_theme()
        # can recolour their icons and rings.
        self._tool_buttons = []
        self.swatch_buttons = {}

        main_layout = QVBoxLayout(
            self
        )

        main_layout.setContentsMargins(
            32,
            24,
            32,
            18
        )

        main_layout.setSpacing(
            12
        )

        # ====================================================
        # HEADER
        # ====================================================

        title = QLabel("Whiteboard")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Draw with your hand through the Virtual Mouse, or with a regular mouse."
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)

        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)

        header_row.addLayout(title_col, 1)

        # What the hand is doing right now, large and up top where it
        # is easy to find.
        self.gesture_status = QLabel()
        self.gesture_status.setObjectName("statusPill")

        header_row.addWidget(
            self.gesture_status,
            alignment=Qt.AlignTop
        )

        self.camera_status = QLabel("● Camera off")
        self.camera_status.setObjectName("cameraPill")
        self.camera_status.setProperty("on", False)

        header_row.addWidget(
            self.camera_status,
            alignment=Qt.AlignTop
        )

        main_layout.addLayout(header_row)

        # ====================================================
        # TOOL DOCK
        #
        # Every tool shows its name under the icon, so nothing has to
        # be guessed from a symbol, and the buttons are large targets
        # for both the mouse and the hand cursor.
        # ====================================================

        dock = QFrame()
        dock.setObjectName("dock")

        dock_layout = QVBoxLayout(dock)
        dock_layout.setContentsMargins(12, 10, 14, 10)
        dock_layout.setSpacing(10)

        # ---------- row 1: tools, history, save ----------

        tools_row = QHBoxLayout()
        tools_row.setSpacing(6)

        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        self.select_button = self.create_tool_button("select", "Select", "Select and move (V)")
        self.pen_button = self.create_tool_button("pen", "Pen", "Pen (P)")
        self.highlighter_button = self.create_tool_button("highlighter", "Marker", "Highlighter (H)")
        self.eraser_button = self.create_tool_button("eraser", "Eraser", "Eraser (E)")

        for name, button in (
            ("select", self.select_button),
            ("pen", self.pen_button),
            ("highlighter", self.highlighter_button),
            ("eraser", self.eraser_button),
        ):
            button.setCheckable(True)
            self.tool_group.addButton(button)
            button.clicked.connect(
                lambda checked=False, tool=name: self.set_tool(tool)
            )
            tools_row.addWidget(button)

        self.shape_button = self.create_tool_button(
            "shape", SHAPE_LABELS["auto"],
            "Shapes: pick a shape, or let rough shapes be tidied"
        )
        self.shape_button.setFixedWidth(92)
        self.shape_button.clicked.connect(self.show_shape_menu)
        tools_row.addWidget(self.shape_button)

        tools_row.addWidget(self.create_separator())

        undo_button = self.create_tool_button("undo", "Undo", "Undo (Ctrl+Z)")
        undo_button.clicked.connect(self.canvas_undo)
        tools_row.addWidget(undo_button)

        redo_button = self.create_tool_button("redo", "Redo", "Redo (Ctrl+Y)")
        redo_button.clicked.connect(self.canvas_redo)
        tools_row.addWidget(redo_button)

        clear_button = self.create_tool_button(
            "clear", "Clear", "Clear the whiteboard", danger=True
        )
        clear_button.clicked.connect(self.clear_canvas)
        tools_row.addWidget(clear_button)

        tools_row.addStretch()

        save_button = QPushButton("Save")
        save_button.setObjectName("saveButton")
        save_button.setCursor(Qt.PointingHandCursor)
        save_button.setToolTip("Save the whiteboard as an image (Ctrl+S)")
        save_button.setIcon(tool_icon("save", "#F5FEFF", 22))
        save_button.setIconSize(QSize(22, 22))
        save_button.setMinimumHeight(56)
        save_button.clicked.connect(self.save_whiteboard)
        tools_row.addWidget(save_button)

        dock_layout.addLayout(tools_row)

        rule = QFrame()
        rule.setObjectName("dockRule")
        rule.setFixedHeight(1)
        dock_layout.addWidget(rule)

        # ---------- row 2: colours, brush ----------

        brush_row = QHBoxLayout()
        brush_row.setContentsMargins(4, 0, 0, 0)
        brush_row.setSpacing(6)

        colour_label = QLabel("Colour")
        colour_label.setObjectName("controlLabel")
        brush_row.addWidget(colour_label)

        # Colour swatches: the picked one gets a cyan ring, which shows
        # on every swatch (navy vanished around the ink colour).
        self.swatch_group = QButtonGroup(self)
        self.swatch_group.setExclusive(True)

        for color, name in self.SWATCHES:

            swatch = QPushButton()
            swatch.setCheckable(True)
            swatch.setFixedSize(40, 40)
            swatch.setCursor(Qt.PointingHandCursor)
            swatch.setToolTip(name)
            swatch.clicked.connect(
                lambda checked=False, c=color: self.set_color(c)
            )

            self.swatch_group.addButton(swatch)
            self.swatch_buttons[color] = swatch
            brush_row.addWidget(swatch)

        brush_row.addWidget(self.create_separator())

        self.brush_preview = BrushPreview()
        brush_row.addWidget(self.brush_preview)

        size_label = QLabel("Size")
        size_label.setObjectName("controlLabel")
        brush_row.addWidget(size_label)

        self.brush_slider = QSlider(Qt.Horizontal)
        self.brush_slider.setRange(1, 20)
        self.brush_slider.setValue(4)
        self.brush_slider.setMinimumWidth(70)
        self.brush_slider.setMaximumWidth(170)
        self.brush_slider.setCursor(Qt.PointingHandCursor)
        self.brush_slider.valueChanged.connect(self.change_brush_size)
        brush_row.addWidget(self.brush_slider, 1)

        self.brush_value = QLabel("4 px")
        self.brush_value.setObjectName("controlValue")
        self.brush_value.setFixedWidth(46)
        brush_row.addSpacing(6)
        brush_row.addWidget(self.brush_value)

        brush_row.addSpacing(6)

        opacity_label = QLabel("Opacity")
        opacity_label.setObjectName("controlLabel")
        brush_row.addWidget(opacity_label)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setMinimumWidth(70)
        self.opacity_slider.setMaximumWidth(170)
        self.opacity_slider.setCursor(Qt.PointingHandCursor)
        self.opacity_slider.valueChanged.connect(self.change_opacity)
        brush_row.addWidget(self.opacity_slider, 1)

        self.opacity_value = QLabel("100%")
        self.opacity_value.setObjectName("controlValue")
        self.opacity_value.setFixedWidth(50)
        brush_row.addSpacing(6)
        brush_row.addWidget(self.opacity_value)

        brush_row.addStretch()

        dock_layout.addLayout(brush_row)

        main_layout.addWidget(dock)

        # Keyboard shortcuts named in the tooltips.
        for keys, action in (
            ("V", lambda: self.set_tool("select")),
            ("P", lambda: self.set_tool("pen")),
            ("H", lambda: self.set_tool("highlighter")),
            ("E", lambda: self.set_tool("eraser")),
            ("Ctrl+Z", self.canvas_undo),
            ("Ctrl+Y", self.canvas_redo),
            ("Ctrl+S", self.save_whiteboard),
        ):
            QShortcut(QKeySequence(keys), self, action)

        # ====================================================
        # CANVAS FRAME
        # ====================================================

        canvas_frame = QFrame()

        canvas_frame.setObjectName(
            "canvasFrame"
        )

        self.canvas_frame = canvas_frame

        canvas_layout = QVBoxLayout(
            canvas_frame
        )

        canvas_layout.setContentsMargins(
            3,
            3,
            3,
            3
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

        # Keep the camera preview tucked into the board's corner.
        canvas_frame.installEventFilter(self)

        # ====================================================
        # GESTURE HINTS (same list as the tutorial)
        # ====================================================

        hints_row = QGridLayout()
        hints_row.setHorizontalSpacing(8)
        hints_row.setVerticalSpacing(6)

        try:
            from gui.tutorial import STEPS

            hints = STEPS[2]["groups"][0][1]
        except Exception:
            hints = []

        self.hint_chips = []

        for icon, name, action in hints:
            chip = QLabel(f"{icon}  <b>{name}</b>  {action}")
            chip.setObjectName("hintChip")
            chip.setTextFormat(Qt.RichText)
            self.hint_chips.append(chip)

        self.hints_grid = hints_row
        self._hint_columns = 0
        self._reflow_hints(len(self.hint_chips))

        self.guide_label = None

        main_layout.addLayout(hints_row)

        # ====================================================
        # DEFAULT
        # ====================================================

        self.set_tool(
            "pen"
        )

        self.swatch_buttons[self.current_color].setChecked(True)
        self.brush_preview.set_brush(self.current_color, 4, 100)

        self._set_gesture_status("Open palm moves the cursor", "info")

        self.apply_theme()

        self.position_camera_preview()

    # ========================================================
    # THEME (light / dark)
    # ========================================================

    # The board itself stays white in both themes (it is a whiteboard,
    # and saved images keep a white background); only the chrome
    # around it follows the app theme.
    LIGHT_PALETTE = {
        "page": "#F2F8FC",
        "text": "#0E2F76",
        "muted": "#5A6B93",
        "dock": "#EAF2FB",
        "border": "#BED2E9",
        "hover": "#C9DAEE",
        "pressed": "#BED2E9",
        "primary": "#0E2F76",
        "primary_hover": "#1B4499",
        "danger_hover": "#F3DCDA",
        "groove": "#C9DAEE",
        "handle": "#FFFFFF",
        "pill": "#DCE7F3",
        "move_bg": "#E3F4EA",
        "move_text": "#23804F",
        "click_bg": "#FFF0DD",
        "click_text": "#A8621A",
        "draw_bg": "#DCE6FA",
        "draw_text": "#0E2F76",
        "menu": "#F5F9FD",
        "swatch_ring": "#EAF2FB",
        "tool_icon": "#3D5A8A",
        "danger_icon": "#B83227",
    }

    DARK_PALETTE = {
        "page": "#0B1A30",
        "text": "#E6EEF8",
        "muted": "#9DB2CC",
        "dock": "#132742",
        "border": "#27496E",
        "hover": "#1B3A63",
        "pressed": "#27496E",
        "primary": "#3E7CF7",
        "primary_hover": "#5A92FA",
        "danger_hover": "#4A2328",
        "groove": "#27496E",
        "handle": "#0B1A30",
        "pill": "#1B3A63",
        "move_bg": "#173B2E",
        "move_text": "#5FD39A",
        "click_bg": "#3D2C12",
        "click_text": "#F2B45A",
        "draw_bg": "#1B3060",
        "draw_text": "#8FB4FF",
        "menu": "#132742",
        "swatch_ring": "#4A6F9A",
        "tool_icon": "#9DB2CC",
        "danger_icon": "#F07A70",
    }

    @property
    def _palette(self):

        from settings import theme as app_theme

        return self.DARK_PALETTE if app_theme.is_dark() else self.LIGHT_PALETTE

    def apply_theme(self):

        from widgets import page_background

        self._page_colors = page_background.page_colors()

        p = self._palette

        self.setStyleSheet(page_background.LAYER_RULE + f"""
            QWidget {{
                background-color: {p['page']};
                color: {p['text']};
                font-family: "Segoe UI";
            }}

            QLabel {{
                background: transparent;
            }}

            QLabel#pageTitle {{
                font-size: 28px;
                font-weight: 800;
            }}

            QLabel#pageSubtitle {{
                font-size: 16px;
                color: {p['muted']};
            }}

            /* ---------- tool dock ---------- */

            QFrame#dock {{
                background-color: {p['dock']};
                border: 1px solid {p['border']};
                border-radius: 14px;
            }}

            QFrame#dockRule {{
                background-color: {p['border']};
                border: none;
            }}

            QFrame#divider {{
                background-color: {p['border']};
                border: none;
            }}

            QToolButton#tool, QToolButton#dangerTool {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 12px;
                color: {p['text']};
                font-size: 13px;
                font-weight: 600;
                padding: 4px 2px 3px 2px;
            }}

            QToolButton#tool:hover {{
                background: {p['hover']};
            }}

            QToolButton#tool:pressed {{
                background: {p['pressed']};
            }}

            QToolButton#tool:checked {{
                background: {p['primary']};
                color: #F5FEFF;
            }}

            QToolButton#tool:focus, QToolButton#dangerTool:focus {{
                outline: none;
            }}

            QToolButton#dangerTool {{
                color: {p['danger_icon']};
            }}

            QToolButton#dangerTool:hover {{
                background: {p['danger_hover']};
            }}

            QPushButton#saveButton {{
                background: {p['primary']};
                color: #F5FEFF;
                border: none;
                border-radius: 12px;
                padding: 10px 24px 10px 18px;
                font-size: 17px;
                font-weight: 700;
            }}

            QPushButton#saveButton:hover {{
                background: {p['primary_hover']};
            }}

            QLabel#controlLabel {{
                font-size: 15px;
                font-weight: 600;
                color: {p['muted']};
            }}

            QLabel#controlValue {{
                font-size: 15px;
                font-weight: 700;
            }}

            QSlider {{
                background: transparent;
                min-height: 30px;
            }}

            QSlider::groove:horizontal {{
                height: 8px;
                background: {p['groove']};
                border-radius: 4px;
            }}

            QSlider::sub-page:horizontal {{
                background: {p['primary']};
                border-radius: 4px;
            }}

            QSlider::handle:horizontal {{
                width: 20px;
                height: 20px;
                margin: -8px 0;
                background: {p['handle']};
                border: 3px solid {p['primary']};
                border-radius: 12px;
            }}

            /* ---------- status pills ---------- */

            QLabel#statusPill, QLabel#cameraPill {{
                background: {p['pill']};
                color: {p['muted']};
                border-radius: 18px;
                padding: 8px 18px;
                font-size: 15px;
                font-weight: 700;
            }}

            QLabel#statusPill[tone="move"], QLabel#cameraPill[on="true"] {{
                background: {p['move_bg']};
                color: {p['move_text']};
            }}

            QLabel#statusPill[tone="click"] {{
                background: {p['click_bg']};
                color: {p['click_text']};
            }}

            QLabel#statusPill[tone="draw"] {{
                background: {p['draw_bg']};
                color: {p['draw_text']};
            }}

            /* ---------- board and hints ---------- */

            QFrame#canvasFrame {{
                background-color: #FFFFFF;
                border: 1px solid {p['border']};
                border-radius: 8px;
            }}

            QLabel#hintChip {{
                background: {p['dock']};
                border: 1px solid {p['border']};
                border-radius: 14px;
                padding: 7px 14px;
                font-size: 15px;
                color: {p['text']};
            }}
        """)

        for button, icon, danger in self._tool_buttons:
            self._paint_tool_icon(button, icon, danger)

        for color, swatch in self.swatch_buttons.items():
            swatch.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {color};
                    border: 3px solid {p['swatch_ring']};
                    border-radius: 20px;
                }}

                QPushButton:hover {{
                    border: 3px solid {p['hover']};
                }}

                QPushButton:checked {{
                    border: 5px solid #22C3DE;
                }}

                QPushButton:focus {{
                    outline: none;
                }}
                """
            )

        self.brush_preview.set_ring(p["border"])

        self.update()

    def _reflow_hints(self, columns):
        """Lay the gesture hint chips out in `columns` columns."""

        columns = max(1, columns)

        if columns == self._hint_columns:
            return

        self._hint_columns = columns

        for chip in self.hint_chips:
            self.hints_grid.removeWidget(chip)

        for i, chip in enumerate(self.hint_chips):
            self.hints_grid.addWidget(
                chip, i // columns, i % columns, Qt.AlignLeft
            )

        # Empty column after the chips soaks up the extra width.
        for c in range(len(self.hint_chips) + 1):
            self.hints_grid.setColumnStretch(c, 0)
        self.hints_grid.setColumnStretch(columns, 1)

    def eventFilter(self, watched, event):

        if (
            watched is getattr(self, "canvas_frame", None)
            and event.type() in (QEvent.Resize, QEvent.Move)
        ):
            self.position_camera_preview()

        return super().eventFilter(watched, event)

    def _set_gesture_status(self, text, tone="info", hold=0.0):
        """Update the status pill; tone is info, move, click or draw.

        `hold` keeps this message up for that many seconds, so a
        short note such as "Made a neat circle" can be read before
        the next camera frame replaces it.
        """

        now = time.monotonic()

        if hold > 0:
            self._status_hold_until = now + hold
        elif now < getattr(self, "_status_hold_until", 0.0):
            return

        # Called for every camera frame: re-styling an unchanged pill
        # each time was a steady source of lag.
        if (text, tone) == self._status_shown:
            return

        self._status_shown = (text, tone)

        self.gesture_status.setText(f"●  {text}")
        self.gesture_status.setProperty("tone", tone)
        self.gesture_status.style().unpolish(self.gesture_status)
        self.gesture_status.style().polish(self.gesture_status)

    # ========================================================
    # TOOL BUTTON
    # ========================================================

    def create_tool_button(
        self,
        icon,
        label,
        tooltip,
        danger=False
    ):

        # Icon with its name underneath, in a large square button.
        button = QToolButton()
        button.setObjectName("dangerTool" if danger else "tool")
        button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        button.setText(label)
        button.setFixedSize(64, 60)
        button.setCursor(Qt.PointingHandCursor)
        button.setToolTip(tooltip)

        button.setIconSize(QSize(26, 26))

        self._tool_buttons.append((button, icon, danger))
        self._paint_tool_icon(button, icon, danger)

        return button

    def _paint_tool_icon(self, button, icon, danger):

        # Muted when idle, white on the "selected" fill.
        p = self._palette
        idle = p["danger_icon"] if danger else p["tool_icon"]

        qicon = QIcon()
        qicon.addPixmap(tool_pixmap(icon, idle, 26), QIcon.Normal, QIcon.Off)
        qicon.addPixmap(tool_pixmap(icon, "#F5FEFF", 26), QIcon.Normal, QIcon.On)

        button.setIcon(qicon)

    # ========================================================
    # SEPARATOR
    # ========================================================

    def create_separator(
        self
    ):

        separator = QFrame()
        separator.setObjectName("divider")
        separator.setFixedSize(1, 26)

        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.addWidget(separator, 0, Qt.AlignVCenter)

        return wrapper

    # ========================================================
    # SHAPE MENU
    # ========================================================

    # Shapes menu entries, in groups. "auto" and "free" change how
    # pen strokes are treated; the rest draw that shape.
    SHAPE_MENU = (
        ("auto", "Automatic  (tidy rough shapes)"),
        ("free", "Freehand  (keep strokes as drawn)"),
        None,
        ("line", "Line"),
        ("arrow", "Arrow"),
        None,
        ("circle", "Circle"),
        ("oval", "Oval"),
        ("square", "Square"),
        ("rectangle", "Rectangle"),
        ("triangle", "Triangle"),
        ("diamond", "Diamond"),
        ("pentagon", "Pentagon"),
        ("hexagon", "Hexagon"),
        ("star", "Star"),
    )

    def show_shape_menu(self):

        menu = QMenu(
            self
        )

        p = self._palette

        # Large, well spaced rows so every entry is easy to read and hit.
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {p['menu']};
                border: 1px solid {p['border']};
                border-radius: 12px;
                padding: 8px;
                font-size: 16px;
            }}

            QMenu::item {{
                padding: 10px 30px 10px 34px;
                color: {p['text']};
                border-radius: 8px;
            }}

            QMenu::item:selected {{
                background-color: {p['pill']};
            }}

            QMenu::indicator {{
                left: 10px;
            }}

            QMenu::separator {{
                height: 1px;
                background: {p['border']};
                margin: 6px 10px;
            }}
        """)

        actions = {}

        for entry in self.SHAPE_MENU:

            if entry is None:
                menu.addSeparator()
                continue

            mode, label = entry

            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(mode == self.canvas.shape_mode)

            actions[action] = mode

        action = menu.exec_(
            self.shape_button.mapToGlobal(
                QPoint(
                    0,
                    self.shape_button.height() + 4
                )
            )
        )

        if action not in actions:

            return

        self.set_shape_mode(
            actions[action]
        )

    def set_shape_mode(
        self,
        mode
    ):

        self.canvas.shape_mode = mode

        self.set_tool(
            "pen"
        )

        # Show the choice on the button itself, so it is always clear
        # what the pen will do.
        self.shape_button.setText(
            SHAPE_LABELS.get(mode, "Shapes")
        )

        if mode == "auto":
            message = "Rough shapes will be tidied"
        elif mode == "free":
            message = "Strokes stay as drawn"
        else:
            message = f"Drag to draw a {SHAPE_LABELS[mode].lower()}"

        self._set_gesture_status(
            message, "draw", hold=2.0
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
            "select": self.select_button,
            "pen": self.pen_button,
            "highlighter": self.highlighter_button,
            "eraser": self.eraser_button,
        }

        if tool in buttons:
            buttons[tool].setChecked(True)

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

        if color in getattr(self, "swatch_buttons", {}):
            self.swatch_buttons[color].setChecked(True)

        self.brush_preview.set_brush(
            color, self.brush_slider.value(), self.opacity_slider.value()
        )

        self.set_tool(
            "pen"
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

        self.brush_value.setText(f"{value} px")
        self.brush_preview.set_brush(
            self.current_color, value, self.opacity_slider.value()
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

        self.opacity_value.setText(f"{value}%")
        self.brush_preview.set_brush(
            self.current_color, self.brush_slider.value(), value
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
    #
    # The Whiteboard never opens the webcam itself. The Virtual
    # Mouse owns the camera and MediaPipe, and this page reads the
    # hand it found in each frame, so one camera powers the cursor,
    # the clicks and drawing without any device conflict.
    # ========================================================

    def start_camera(
        self
    ):

        # Kept for the main window, which calls it when the camera
        # changes. Frames always come from the Virtual Mouse.
        return

    # ========================================================
    # STOP CAMERA
    # ========================================================

    def stop_camera(
        self
    ):

        self.camera_timer.stop()

        self.finish_gesture_drawing()

        self._last_stamp = None

        self.camera_label.setText(
            "Camera"
        )

    # ========================================================
    # CAMERA UPDATE
    # ========================================================

    def update_camera(
        self
    ):

        # Keep the header pill in sync if the Virtual Mouse starts or
        # stops while the Whiteboard is open.
        self.update_camera_status()

        vmouse = getattr(
            self.parent_window, "virtual_mouse", None
        )

        if (
            vmouse is None
            or not getattr(vmouse, "camera_running", False)
            or getattr(vmouse, "camera_paused", False)
        ):

            self.finish_gesture_drawing()

            self._last_stamp = None

            self.camera_label.setText(
                "Camera off  (start Virtual Mouse)"
            )

            self._set_gesture_status(
                "Start the Virtual Mouse to draw by hand", "info"
            )

            return

        # A new frame has a new capture time and a new hand object;
        # both are checked in case two frames share a clock tick.
        stamp = (
            getattr(vmouse, "_frame_stamp", None),
            id(vmouse.get_latest_hand()),
        )

        # Nothing new from the camera yet.
        if stamp[0] is None or stamp == self._last_stamp:

            # Lift the pen if the camera stalls mid-stroke.
            if (
                self.gesture_drawing
                and time.monotonic() - self._last_hand_time > HAND_TIMEOUT
            ):
                self.finish_gesture_drawing()

            return

        self._last_stamp = stamp

        self.process_hand(
            vmouse
        )

        frame = vmouse.get_latest_frame()

        if frame is not None:

            self.display_camera(
                frame
            )

    # ========================================================
    # HAND GESTURES
    #
    # Open palm, closed hand and pinch are handled by the Virtual
    # Mouse itself (move, left click, right click). This page adds
    # drawing: index and middle fingers held together draw, and
    # spreading them apart lifts the pen.
    # ========================================================

    def process_hand(
        self,
        vmouse
    ):

        hand = vmouse.get_latest_hand()

        if hand is None:

            self.finish_gesture_drawing()

            self._set_gesture_status(
                "Show your hand to the camera", "info"
            )

            return

        self._last_hand_time = time.monotonic()

        if self.is_draw_gesture(hand):

            self._release_frames = 0

            self.draw_from_gesture(
                hand,
                vmouse
            )

            return

        # Pen is down but the fingers parted: lift it. One frame of
        # grace keeps a single bad detection from breaking the line.
        if self.gesture_drawing:

            self._release_frames += 1

            if self._release_frames < DRAW_RELEASE_FRAMES:
                return

        self.finish_gesture_drawing()

        gesture = getattr(vmouse, "last_gesture", "None")

        if gesture == "Open Palm":

            self._set_gesture_status(
                "Open hand: moving the cursor", "move"
            )

        elif gesture == "Fist":

            self._set_gesture_status(
                "Closed hand: click", "click"
            )

        elif gesture == "Pinch":

            self._set_gesture_status(
                "Pinch: right click", "click"
            )

        else:

            self._set_gesture_status(
                "Hold index and middle together to draw", "info"
            )

    def is_draw_gesture(
        self,
        hand
    ):
        """Index and middle straight and touching, ring and pinky folded."""

        lm = hand.landmark

        wrist = lm[WRIST]

        def gap(a, b):
            return math.hypot(a.x - b.x, a.y - b.y)

        # Measured against the palm, so it works near or far from
        # the camera.
        palm = gap(wrist, lm[MIDDLE_MCP]) or 1e-6

        def straight(tip, pip):
            return gap(lm[tip], wrist) > gap(lm[pip], wrist) * FINGER_UP_RATIO

        if not (
            straight(INDEX_TIP, INDEX_PIP)
            and straight(MIDDLE_TIP, MIDDLE_PIP)
        ):
            return False

        # An open hand with the fingers together is "move", not "draw".
        if straight(RING_TIP, RING_PIP) or straight(PINKY_TIP, PINKY_PIP):
            return False

        limit = DRAW_GAP_KEEP if self.gesture_drawing else DRAW_GAP_START

        return gap(lm[INDEX_TIP], lm[MIDDLE_TIP]) / palm < limit

    # ========================================================
    # DRAW FROM GESTURE
    # ========================================================

    def draw_from_gesture(
        self,
        hand,
        vmouse
    ):

        if self.current_tool not in ("pen", "highlighter", "eraser"):

            self._set_gesture_status(
                "Pick the pen to draw", "info"
            )

            return

        # Steer the real cursor with the Virtual Mouse's own mapping
        # and smoothing, so the pen lands where the open hand left
        # the cursor and follows the hand the same way.
        if hasattr(vmouse, "move_cursor"):

            try:
                vmouse.move_cursor(hand)
            except Exception:
                pass

        point = self.canvas.mapFromGlobal(
            QCursor.pos()
        )

        if not self.canvas.rect().contains(point):

            self.finish_gesture_drawing()

            self._set_gesture_status(
                "Move onto the board to draw", "info"
            )

            return

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

            # A dot, so a quick touch still marks the board.
            self.canvas.draw_gesture_line(
                point,
                point
            )

            self._set_gesture_status(
                "Drawing  (spread fingers to stop)", "draw"
            )

            return

        # ====================================================
        # DRAW
        # ====================================================

        # Ignore 1 px jitter.
        if (
            abs(point.x() - self.last_draw_point.x())
            + abs(point.y() - self.last_draw_point.y())
            < 2
        ):
            return

        self.canvas.draw_gesture_line(
            self.last_draw_point,
            point
        )

        self.gesture_points.append(
            point
        )

        self.last_draw_point = point

    # ========================================================
    # FINISH GESTURE DRAWING
    # ========================================================

    def finish_gesture_drawing(
        self
    ):

        self._release_frames = 0

        if not self.gesture_drawing:

            if self.canvas.show_gesture_cursor:

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

        # Tidy the stroke into a perfect shape, like a mouse stroke.
        if self.current_tool == "pen":

            self.on_canvas_stroke_finished(
                points
            )

    # ========================================================
    # SHAPES
    #
    # "Automatic" turns a rough square, circle, triangle, ... into
    # a perfect one the same size; small strokes and open curves
    # (handwriting) are left alone. "Freehand" never changes a
    # stroke. Any other choice draws that shape.
    # ========================================================

    def on_canvas_stroke_finished(
        self,
        points
    ):
        """Tidy a finished pen stroke (mouse or hand) into a shape."""

        if len(points) < 2:

            return

        mode = getattr(
            self.canvas,
            "shape_mode",
            "auto"
        )

        if mode == "free":

            return

        coords = [
            (float(p.x()), float(p.y()))
            for p in points
        ]

        if mode == "auto":

            result = recognise_shape(
                coords
            )

            if result is not None:

                self.commit_shape(
                    *result
                )

            return

        # A shape picked in the Shapes menu: a mouse drag gives its
        # two corners; a hand stroke gives the box around it.
        if len(coords) == 2 or mode in ("line", "arrow"):

            start, end = coords[0], coords[-1]

        else:

            xs = [p[0] for p in coords]
            ys = [p[1] for p in coords]

            start, end = (min(xs), min(ys)), (max(xs), max(ys))

        if abs(end[0] - start[0]) < 4 and abs(end[1] - start[1]) < 4:

            return

        self.commit_shape(
            SHAPE_LABELS.get(mode, "Shape"),
            drag_shape(mode, start, end)
        )

    def commit_shape(
        self,
        name,
        shape
    ):
        """Swap the rough stroke for the perfect shape."""

        # Back to the board before the stroke (undo stays intact, so
        # one Undo removes the shape).
        self.canvas.revert_to_last_state()

        painter = QPainter(
            self.canvas.canvas
        )

        painter.setRenderHint(
            QPainter.Antialiasing,
            True
        )

        painter.setPen(
            self.canvas.make_pen("pen")
        )

        painter.setBrush(
            Qt.NoBrush
        )

        paint_shape(
            painter,
            shape
        )

        painter.end()

        self.canvas.update()

        self._set_gesture_status(
            f"Made a neat {name.lower()}", "draw", hold=1.5
        )

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

        # Shrink first: converting and scaling a full camera frame on
        # every update was wasted work for a 140 px preview.
        frame_h, frame_w = frame.shape[:2]

        scale = min(
            (CAMERA_PREVIEW_WIDTH - 4) / frame_w,
            (CAMERA_PREVIEW_HEIGHT - 4) / frame_h
        )

        small = cv2.resize(
            frame,
            (max(1, int(frame_w * scale)), max(1, int(frame_h * scale))),
            interpolation=cv2.INTER_AREA
        )

        frame_rgb = cv2.cvtColor(
            small,
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

        self.camera_label.setPixmap(
            pixmap
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