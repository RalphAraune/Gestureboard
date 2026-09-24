import os
import math
import time

import cv2
import numpy as np

try:
    import mediapipe as mp
except Exception:
    mp = None

from PyQt5.QtWidgets import (
    QApplication,
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
    QAction,
)
from PyQt5.QtCore import (
    Qt,
    QPoint,
    QTimer,
    QStandardPaths,
    QRect,
)
from PyQt5.QtGui import (
    QPainter,
    QPen,
    QColor,
    QPixmap,
    QCursor,
    QImage,
    QPolygon,
)
from PyQt5.QtTest import QTest


# ============================================================
# CUSTOM CURSORS
# ============================================================

def create_pen_cursor():

    pixmap = QPixmap(
        32,
        32
    )

    pixmap.fill(
        Qt.transparent
    )

    painter = QPainter(
        pixmap
    )

    painter.setRenderHint(
        QPainter.Antialiasing,
        True
    )

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
            QPoint(6, 23),
            QPoint(10, 27),
            QPoint(25, 12),
            QPoint(21, 8),
        ])
    )

    painter.setBrush(
        QColor("#E8D3B0")
    )

    painter.drawPolygon(
        QPolygon([
            QPoint(6, 23),
            QPoint(10, 27),
            QPoint(4, 29),
        ])
    )

    painter.setBrush(
        QColor("#F28B8B")
    )

    painter.drawPolygon(
        QPolygon([
            QPoint(21, 8),
            QPoint(25, 12),
            QPoint(28, 9),
            QPoint(24, 5),
        ])
    )

    painter.end()

    return QCursor(
        pixmap,
        5,
        28
    )


def create_highlighter_cursor():

    pixmap = QPixmap(
        32,
        32
    )

    pixmap.fill(
        Qt.transparent
    )

    painter = QPainter(
        pixmap
    )

    painter.setRenderHint(
        QPainter.Antialiasing,
        True
    )

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
        6,
        6,
        21,
        10,
        3,
        3
    )

    painter.setBrush(
        QColor("#E8D3B0")
    )

    painter.drawPolygon(
        QPolygon([
            QPoint(7, 16),
            QPoint(16, 16),
            QPoint(11, 24),
        ])
    )

    painter.end()

    return QCursor(
        pixmap,
        11,
        24
    )


def create_eraser_cursor():

    pixmap = QPixmap(
        32,
        32
    )

    pixmap.fill(
        Qt.transparent
    )

    painter = QPainter(
        pixmap
    )

    painter.setRenderHint(
        QPainter.Antialiasing,
        True
    )

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
        5,
        8,
        22,
        14,
        4,
        4
    )

    painter.setBrush(
        QColor("#FFFFFF")
    )

    painter.drawRect(
        17,
        9,
        8,
        12
    )

    painter.end()

    return QCursor(
        pixmap,
        16,
        16
    )


def create_select_cursor():

    pixmap = QPixmap(
        24,
        24
    )

    pixmap.fill(
        Qt.transparent
    )

    painter = QPainter(
        pixmap
    )

    painter.setRenderHint(
        QPainter.Antialiasing,
        True
    )

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
            QPoint(3, 20),
            QPoint(8, 15),
            QPoint(12, 22),
            QPoint(15, 20),
            QPoint(11, 14),
            QPoint(19, 14),
        ])
    )

    painter.end()

    return QCursor(
        pixmap,
        3,
        2
    )


def create_hand_cursor():

    pixmap = QPixmap(
        28,
        28
    )

    pixmap.fill(
        Qt.transparent
    )

    painter = QPainter(
        pixmap
    )

    painter.setRenderHint(
        QPainter.Antialiasing,
        True
    )

    painter.setPen(
        QPen(
            QColor("#0E2F76"),
            2
        )
    )

    painter.setBrush(
        Qt.NoBrush
    )

    painter.drawEllipse(
        4,
        4,
        20,
        20
    )

    painter.drawLine(
        14,
        7,
        14,
        21
    )

    painter.drawLine(
        7,
        14,
        21,
        14
    )

    painter.end()

    return QCursor(
        pixmap,
        14,
        14
    )


# ============================================================
# DRAWING CANVAS
# ============================================================

class DrawingCanvas(QWidget):

    def __init__(
        self,
        parent=None
    ):

        super().__init__(
            parent
        )

        # ====================================================
        # CANVAS
        # ====================================================

        self.canvas = QPixmap(
            1200,
            650
        )

        self.canvas.fill(
            QColor("#FFFFFF")
        )

        self.setMinimumSize(
            700,
            450
        )

        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
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

        self.stroke_points = []

        # ====================================================
        # UNDO / REDO
        # ====================================================

        self.undo_stack = []

        self.redo_stack = []

        # ====================================================
        # CURSORS
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

        self.setMouseTracking(
            True
        )

        self.set_tool(
            "pen"
        )

    # ========================================================
    # RESIZE
    # ========================================================

    def resizeEvent(
        self,
        event
    ):

        new_width = max(
            1,
            self.width()
        )

        new_height = max(
            1,
            self.height()
        )

        if (
            self.canvas.width()
            != new_width
            or
            self.canvas.height()
            != new_height
        ):

            old_canvas = (
                self.canvas
            )

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

            painter.setRenderHint(
                QPainter.SmoothPixmapTransform,
                True
            )

            painter.drawPixmap(
                QRect(
                    0,
                    0,
                    new_width,
                    new_height
                ),
                old_canvas,
                QRect(
                    0,
                    0,
                    old_canvas.width(),
                    old_canvas.height()
                )
            )

            painter.end()

            self.canvas = (
                new_canvas
            )

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

        elif tool == "shape":

            self.setCursor(
                self.pen_cursor
            )

        else:

            self.setCursor(
                Qt.ArrowCursor
            )

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

    # ========================================================
    # BRUSH SIZE
    # ========================================================

    def set_brush_size(
        self,
        value
    ):

        self.brush_size = int(
            value
        )

    # ========================================================
    # OPACITY
    # ========================================================

    def set_opacity(
        self,
        value
    ):

        self.opacity = int(
            value
        )

    # ========================================================
    # SAVE STATE
    # ========================================================

    def save_state(self):

        self.undo_stack.append(
            self.canvas.copy()
        )

        if len(
            self.undo_stack
        ) > 30:

            self.undo_stack.pop(
                0
            )

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
    # MOUSE DRAWING
    # ========================================================

    def mousePressEvent(
        self,
        event
    ):

        if (
            event.button()
            != Qt.LeftButton
        ):

            return

        if self.tool not in [
            "pen",
            "highlighter",
            "eraser",
            "shape"
        ]:

            return

        self.save_state()

        self.drawing = True

        self.stroke_points = [
            event.pos()
        ]

        self.last_point = (
            event.pos()
        )

        if self.tool != "shape":

            self.draw_segment(
                event.pos(),
                event.pos()
            )

        event.accept()

    # ========================================================
    # MOUSE MOVE
    # ========================================================

    def mouseMoveEvent(
        self,
        event
    ):

        if not self.drawing:

            return

        if not (
            event.buttons()
            & Qt.LeftButton
        ):

            return

        point = QPoint(
            max(
                0,
                min(
                    self.width() - 1,
                    event.pos().x()
                )
            ),
            max(
                0,
                min(
                    self.height() - 1,
                    event.pos().y()
                )
            )
        )

        self.stroke_points.append(
            point
        )

        if self.tool != "shape":

            self.draw_segment(
                self.last_point,
                point
            )

        self.last_point = (
            point
        )

        event.accept()

    # ========================================================
    # MOUSE RELEASE
    # ========================================================

    def mouseReleaseEvent(
        self,
        event
    ):

        if (
            event.button()
            != Qt.LeftButton
        ):

            return

        if self.drawing:

            self.drawing = False

            if (
                self.tool == "shape"
                and
                len(self.stroke_points) >= 4
            ):

                self.draw_auto_shape(
                    self.stroke_points
                )

            elif (
                self.tool == "pen"
                and
                len(self.stroke_points) >= 5
            ):

                self.auto_correct_pen_stroke(
                    self.stroke_points
                )

        self.stroke_points = []

        event.accept()

    # ========================================================
    # DRAW SEGMENT
    # ========================================================

    def draw_segment(
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

        # ----------------------------------------------------
        # ERASER
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # HIGHLIGHTER
        # ----------------------------------------------------

        elif self.tool == "highlighter":

            color = QColor(
                self.color
            )

            color.setAlpha(
                int(
                    self.opacity
                    * 255
                    / 100
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

        # ----------------------------------------------------
        # PEN
        # ----------------------------------------------------

        else:

            color = QColor(
                self.color
            )

            color.setAlpha(
                int(
                    self.opacity
                    * 255
                    / 100
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
    # PEN
    # ========================================================

    def create_pen(self):

        color = QColor(
            self.color
        )

        color.setAlpha(
            int(
                self.opacity
                * 255
                / 100
            )
        )

        return QPen(
            color,
            max(
                1,
                self.brush_size
            ),
            Qt.SolidLine,
            Qt.RoundCap,
            Qt.RoundJoin
        )

    # ========================================================
    # STROKE GEOMETRY
    # ========================================================

    def get_stroke_geometry(
        self,
        points
    ):

        if len(points) < 4:

            return None

        array = np.array(
            [
                [
                    point.x(),
                    point.y()
                ]
                for point in points
            ],
            dtype=np.float32
        )

        x_min = float(
            array[:, 0].min()
        )

        x_max = float(
            array[:, 0].max()
        )

        y_min = float(
            array[:, 1].min()
        )

        y_max = float(
            array[:, 1].max()
        )

        width = max(
            1.0,
            x_max - x_min
        )

        height = max(
            1.0,
            y_max - y_min
        )

        diagonal = math.hypot(
            width,
            height
        )

        differences = np.diff(
            array,
            axis=0
        )

        segment_lengths = (
            np.linalg.norm(
                differences,
                axis=1
            )
        )

        path_length = float(
            segment_lengths.sum()
        )

        direct_distance = float(
            np.linalg.norm(
                array[-1]
                -
                array[0]
            )
        )

        closed = (
            direct_distance
            <=
            max(
                12.0,
                diagonal * 0.22
            )
        )

        contour = array.reshape(
            -1,
            1,
            2
        )

        area = abs(
            float(
                cv2.contourArea(
                    contour
                )
            )
        )

        approximation = cv2.approxPolyDP(
            contour,
            max(
                2.0,
                path_length * 0.035
            ),
            True
        )

        return {
            "array": array,
            "x": x_min,
            "y": y_min,
            "width": width,
            "height": height,
            "diagonal": diagonal,
            "path": path_length,
            "direct": direct_distance,
            "closed": closed,
            "area": area,
            "approx": approximation,
        }

    # ========================================================
    # RESTORE BEFORE AUTO SHAPE
    # ========================================================

    def restore_before_stroke(self):

        if self.undo_stack:

            self.canvas = (
                self.undo_stack[-1].copy()
            )

    # ========================================================
    # PERFECT LINE
    # ========================================================

    def draw_perfect_line(
        self,
        start,
        end
    ):

        self.restore_before_stroke()

        painter = QPainter(
            self.canvas
        )

        painter.setRenderHint(
            QPainter.Antialiasing,
            True
        )

        painter.setPen(
            self.create_pen()
        )

        painter.drawLine(
            start,
            end
        )

        painter.end()

        self.update()

    # ========================================================
    # PERFECT CIRCLE
    # ========================================================

    def draw_perfect_circle(
        self,
        center,
        radius
    ):

        self.restore_before_stroke()

        radius = max(
            2,
            int(radius)
        )

        painter = QPainter(
            self.canvas
        )

        painter.setRenderHint(
            QPainter.Antialiasing,
            True
        )

        painter.setPen(
            self.create_pen()
        )

        painter.setBrush(
            Qt.NoBrush
        )

        painter.drawEllipse(
            center.x() - radius,
            center.y() - radius,
            radius * 2,
            radius * 2
        )

        painter.end()

        self.update()

    # ========================================================
    # RECTANGLE
    # ========================================================

    def draw_rectangle(
        self,
        rect,
        square=False
    ):

        self.restore_before_stroke()

        if square:

            side = min(
                rect.width(),
                rect.height()
            )

            rect = QRect(
                rect.left(),
                rect.top(),
                side,
                side
            )

        painter = QPainter(
            self.canvas
        )

        painter.setRenderHint(
            QPainter.Antialiasing,
            True
        )

        painter.setPen(
            self.create_pen()
        )

        painter.setBrush(
            Qt.NoBrush
        )

        painter.drawRect(
            rect
        )

        painter.end()

        self.update()

    # ========================================================
    # TRIANGLE
    # ========================================================

    def draw_triangle(
        self,
        points
    ):

        self.restore_before_stroke()

        painter = QPainter(
            self.canvas
        )

        painter.setRenderHint(
            QPainter.Antialiasing,
            True
        )

        painter.setPen(
            self.create_pen()
        )

        painter.setBrush(
            Qt.NoBrush
        )

        painter.drawPolygon(
            QPolygon(
                points
            )
        )

        painter.end()

        self.update()

    # ========================================================
    # ARROW
    # ========================================================

    def draw_arrow(
        self,
        start,
        end
    ):

        self.restore_before_stroke()

        painter = QPainter(
            self.canvas
        )

        painter.setRenderHint(
            QPainter.Antialiasing,
            True
        )

        painter.setPen(
            self.create_pen()
        )

        painter.drawLine(
            start,
            end
        )

        angle = math.atan2(
            end.y() - start.y(),
            end.x() - start.x()
        )

        head = max(
            10,
            self.brush_size * 3
        )

        point1 = QPoint(
            int(
                end.x()
                -
                head
                *
                math.cos(
                    angle - math.pi / 6
                )
            ),
            int(
                end.y()
                -
                head
                *
                math.sin(
                    angle - math.pi / 6
                )
            )
        )

        point2 = QPoint(
            int(
                end.x()
                -
                head
                *
                math.cos(
                    angle + math.pi / 6
                )
            ),
            int(
                end.y()
                -
                head
                *
                math.sin(
                    angle + math.pi / 6
                )
            )
        )

        painter.drawLine(
            end,
            point1
        )

        painter.drawLine(
            end,
            point2
        )

        painter.end()

        self.update()

    # ========================================================
    # AUTOMATIC SHAPE RECOGNITION
    # ========================================================

    def auto_correct_pen_stroke(
        self,
        points
    ):

        geometry = (
            self.get_stroke_geometry(
                points
            )
        )

        if not geometry:

            return

        width = geometry[
            "width"
        ]

        height = geometry[
            "height"
        ]

        diagonal = geometry[
            "diagonal"
        ]

        approximation = geometry[
            "approx"
        ]

        # ----------------------------------------------------
        # VERY SMALL MARK
        # ----------------------------------------------------

        if diagonal < 18:

            return

        # ----------------------------------------------------
        # STRAIGHT LINE
        # ----------------------------------------------------

        if (
            geometry["direct"]
            /
            max(
                geometry["path"],
                1.0
            )
            >=
            0.93
        ):

            self.draw_perfect_line(
                points[0],
                points[-1]
            )

            return

        # ----------------------------------------------------
        # MUST BE CLOSED FOR SHAPES
        # ----------------------------------------------------

        if not geometry[
            "closed"
        ]:

            return

        # ----------------------------------------------------
        # CIRCLE FIRST
        #
        # IMPORTANT:
        # Circle is checked BEFORE 3/4 corner detection.
        #
        # This prevents a small circle from becoming a square.
        # ----------------------------------------------------

        perimeter = max(
            geometry["path"],
            1.0
        )

        circularity = (
            4.0
            *
            math.pi
            *
            geometry["area"]
            /
            (
                perimeter
                *
                perimeter
            )
        )

        aspect_ratio = (
            min(
                width,
                height
            )
            /
            max(
                width,
                height
            )
        )

        if (
            circularity >= 0.68
            and
            aspect_ratio >= 0.72
        ):

            center = QPoint(
                int(
                    geometry["x"]
                    +
                    width / 2
                ),
                int(
                    geometry["y"]
                    +
                    height / 2
                )
            )

            radius = int(
                min(
                    width,
                    height
                )
                /
                2
            )

            self.draw_perfect_circle(
                center,
                radius
            )

            return

        # ----------------------------------------------------
        # TRIANGLE
        # ----------------------------------------------------

        corners = len(
            approximation
        )

        if corners == 3:

            triangle_points = [
                QPoint(
                    int(point[0][0]),
                    int(point[0][1])
                )
                for point in approximation
            ]

            self.draw_triangle(
                triangle_points
            )

            return

        # ----------------------------------------------------
        # RECTANGLE / SQUARE
        # ----------------------------------------------------

        if corners == 4:

            rectangle = QRect(
                int(
                    geometry["x"]
                ),
                int(
                    geometry["y"]
                ),
                max(
                    2,
                    int(
                        width
                    )
                ),
                max(
                    2,
                    int(
                        height
                    )
                )
            )

            is_square = (
                aspect_ratio >= 0.78
            )

            self.draw_rectangle(
                rectangle,
                is_square
            )

    # ========================================================
    # SHAPE MODE
    # ========================================================

    def draw_auto_shape(
        self,
        points
    ):

        geometry = (
            self.get_stroke_geometry(
                points
            )
        )

        if not geometry:

            return

        approximation = geometry[
            "approx"
        ]

        corners = len(
            approximation
        )

        # ----------------------------------------------------
        # CIRCLE
        # ----------------------------------------------------

        if geometry[
            "closed"
        ]:

            perimeter = max(
                geometry["path"],
                1.0
            )

            circularity = (
                4
                *
                math.pi
                *
                geometry["area"]
                /
                (
                    perimeter
                    *
                    perimeter
                )
            )

            aspect_ratio = (
                min(
                    geometry["width"],
                    geometry["height"]
                )
                /
                max(
                    geometry["width"],
                    geometry["height"]
                )
            )

            if (
                circularity >= 0.62
                and
                aspect_ratio >= 0.70
            ):

                center = QPoint(
                    int(
                        geometry["x"]
                        +
                        geometry["width"]
                        /
                        2
                    ),
                    int(
                        geometry["y"]
                        +
                        geometry["height"]
                        /
                        2
                    )
                )

                radius = int(
                    min(
                        geometry["width"],
                        geometry["height"]
                    )
                    /
                    2
                )

                self.draw_perfect_circle(
                    center,
                    radius
                )

                return

        # ----------------------------------------------------
        # TRIANGLE
        # ----------------------------------------------------

        if (
            corners == 3
            and
            geometry["closed"]
        ):

            points3 = [
                QPoint(
                    int(point[0][0]),
                    int(point[0][1])
                )
                for point in approximation
            ]

            self.draw_triangle(
                points3
            )

            return

        # ----------------------------------------------------
        # RECTANGLE / SQUARE
        # ----------------------------------------------------

        if (
            corners == 4
            and
            geometry["closed"]
        ):

            rectangle = QRect(
                int(
                    geometry["x"]
                ),
                int(
                    geometry["y"]
                ),
                max(
                    2,
                    int(
                        geometry["width"]
                    )
                ),
                max(
                    2,
                    int(
                        geometry["height"]
                    )
                )
            )

            is_square = (
                min(
                    geometry["width"],
                    geometry["height"]
                )
                /
                max(
                    geometry["width"],
                    geometry["height"]
                )
                >=
                0.78
            )

            self.draw_rectangle(
                rectangle,
                is_square
            )

            return

        # ----------------------------------------------------
        # IF NOT RECOGNIZED
        # ----------------------------------------------------

        self.restore_before_stroke()

        painter = QPainter(
            self.canvas
        )

        painter.setRenderHint(
            QPainter.Antialiasing,
            True
        )

        painter.setPen(
            self.create_pen()
        )

        for start, end in zip(
            points[:-1],
            points[1:]
        ):

            painter.drawLine(
                start,
                end
            )

        painter.end()

        self.update()

    # ========================================================
    # PAINT EVENT
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

        # ----------------------------------------------------
        # LIGHT GRID
        # ----------------------------------------------------

        grid_size = 40

        painter.setPen(
            QPen(
                QColor("#F1F3F6"),
                1
            )
        )

        for x in range(
            0,
            self.width(),
            grid_size
        ):

            painter.drawLine(
                x,
                0,
                x,
                self.height()
            )

        for y in range(
            0,
            self.height(),
            grid_size
        ):

            painter.drawLine(
                0,
                y,
                self.width(),
                y
            )

        painter.drawPixmap(
            0,
            0,
            self.canvas
        )

        painter.end()


# ============================================================
# WHITEBOARD PAGE
# ============================================================

class WhiteboardPage(
    QWidget
):

    def __init__(
        self,
        parent=None
    ):

        super().__init__(
            parent
        )

        self.parent_window = (
            parent
        )

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

        self.selected_shape = (
            "Line"
        )

        # ====================================================
        # CAMERA
        # ====================================================

        self.camera = None

        self.camera_running = False

        self.camera_timer = QTimer(
            self
        )

        self.camera_timer.timeout.connect(
            self.update_camera
        )

        # ====================================================
        # MEDIAPIPE
        # ====================================================

        self.mp_hands = None

        self.mp_drawing = None

        self.hands = None

        # ====================================================
        # GESTURE STATE
        # ====================================================

        self.last_gesture = (
            "None"
        )

        self.gesture_candidate = (
            "None"
        )

        self.gesture_candidate_since = (
            0.0
        )

        self.last_click_time = (
            0.0
        )

        # ====================================================
        # CURSOR SMOOTHING
        # ====================================================

        self.cursor_x = None

        self.cursor_y = None

        self.cursor_smoothing = (
            0.35
        )

        # ====================================================
        # GESTURE DRAWING
        # ====================================================

        self.gesture_drawing = False

        self.last_draw_point = None

        # ====================================================
        # BUILD
        # ====================================================

        self.setup_ui()

        self.setup_mediapipe()

        QTimer.singleShot(
            250,
            self.start_camera
        )

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

            QFrame#canvasFrame {
                background-color: #FFFFFF;
                border: 1px solid #D7E5F3;
                border-radius: 12px;
            }
        """)

        # ====================================================
        # MAIN
        # ====================================================

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
            8
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
            "Draw, write, highlight, create shapes, and control the whiteboard using hand gestures."
        )

        subtitle.setStyleSheet("""
            QLabel {
                font-size: 12px;
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
            8,
            5,
            8,
            5
        )

        toolbar_layout.setSpacing(
            4
        )

        # ====================================================
        # SELECT / CURSOR
        # ====================================================

        self.select_button = (
            self.create_tool_button(
                "↖",
                "Select / Cursor"
            )
        )

        self.select_button.clicked.connect(
            lambda:
            self.set_tool(
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
                "Pen / Automatic Shape Recognition"
            )
        )

        self.pen_button.clicked.connect(
            lambda:
            self.set_tool(
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
            lambda:
            self.set_tool(
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
            lambda:
            self.set_tool(
                "eraser"
            )
        )

        toolbar_layout.addWidget(
            self.eraser_button
        )

        # ====================================================
        # SHAPE
        # ====================================================

        self.shape_button = (
            self.create_tool_button(
                "△",
                "Shape"
            )
        )

        self.shape_button.clicked.connect(
            self.show_shape_menu
        )

        toolbar_layout.addWidget(
            self.shape_button
        )

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
                21,
                21
            )

            color_button.setToolTip(
                f"Color {color}"
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
                lambda
                checked=False,
                c=color:
                self.set_color(
                    c
                )
            )

            toolbar_layout.addWidget(
                color_button
            )

        toolbar_layout.addWidget(
            self.create_separator()
        )

        # ====================================================
        # SIZE
        # ====================================================

        size_label = QLabel(
            "Size"
        )

        size_label.setStyleSheet(
            "font-size:11px;color:#6682AC;"
        )

        toolbar_layout.addWidget(
            size_label
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
            80
        )

        self.brush_slider.valueChanged.connect(
            self.change_brush_size
        )

        toolbar_layout.addWidget(
            self.brush_slider
        )

        # ====================================================
        # OPACITY
        # ====================================================

        opacity_label = QLabel(
            "Opacity"
        )

        opacity_label.setStyleSheet(
            "font-size:11px;color:#6682AC;"
        )

        toolbar_layout.addWidget(
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
            80
        )

        self.opacity_slider.valueChanged.connect(
            self.change_opacity
        )

        toolbar_layout.addWidget(
            self.opacity_slider
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
        # GESTURE STATUS
        # ====================================================

        self.gesture_status = QLabel(
            "● Open Palm — Cursor"
        )

        self.gesture_status.setStyleSheet("""
            QLabel {
                background: #EEF5FF;
                border: 1px solid #D7E5F3;
                border-radius: 12px;
                color: #5574A8;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: 600;
            }
        """)

        main_layout.addWidget(
            self.gesture_status
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
        # NO QSCROLLAREA
        # ====================================================

        self.canvas = DrawingCanvas()

        canvas_layout.addWidget(
            self.canvas
        )

        main_layout.addWidget(
            canvas_frame,
            1
        )

        # ====================================================
        # CAMERA OVERLAY
        # ====================================================

        self.camera_overlay = QLabel(
            self
        )

        self.camera_overlay.setFixedSize(
            140,
            105
        )

        self.camera_overlay.setAlignment(
            Qt.AlignCenter
        )

        self.camera_overlay.setStyleSheet("""
            QLabel {
                background: #101820;
                border: 2px solid #FFFFFF;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 9px;
            }
        """)

        self.camera_overlay.setText(
            "Camera"
        )

        self.camera_overlay.raise_()

        self.set_tool(
            "pen"
        )

    # ========================================================
    # RESIZE
    # ========================================================

    def resizeEvent(
        self,
        event
    ):

        super().resizeEvent(
            event
        )

        margin = 8

        self.camera_overlay.move(
            self.width()
            -
            self.camera_overlay.width()
            -
            margin,

            self.height()
            -
            self.camera_overlay.height()
            -
            margin
        )

        self.camera_overlay.raise_()

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
            40,
            38
        )

        button.setToolTip(
            tooltip
        )

        button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 8px;
                color: #5474A8;
                font-size: 19px;
                font-weight: 500;
            }

            QPushButton:hover {
                background: #E7F0FA;
                color: #0E2F76;
            }

            QPushButton:pressed {
                background: #D5E4F5;
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
    # SET TOOL
    # ========================================================

    def set_tool(
        self,
        tool
    ):

        self.current_tool = (
            tool
        )

        self.canvas.set_tool(
            tool
        )

        buttons = {
            "pen":
                self.pen_button,

            "highlighter":
                self.highlighter_button,

            "eraser":
                self.eraser_button,

            "select":
                self.select_button,

            "shape":
                self.shape_button,
        }

        normal_style = """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 8px;
                color: #5474A8;
                font-size: 19px;
                font-weight: 500;
            }

            QPushButton:hover {
                background: #E7F0FA;
                color: #0E2F76;
            }
        """

        active_style = """
            QPushButton {
                background: #B7CCEA;
                border: none;
                border-radius: 8px;
                color: #0E2F76;
                font-size: 19px;
                font-weight: 700;
            }
        """

        for button in (
            buttons.values()
        ):

            button.setStyleSheet(
                normal_style
            )

        if tool in buttons:

            buttons[
                tool
            ].setStyleSheet(
                active_style
            )

        if tool == "pen":

            self.gesture_status.setText(
                "● Open Palm — Cursor   |   Closed Palm — Click   |   Index + Middle Together — Draw"
            )

        elif tool == "highlighter":

            self.gesture_status.setText(
                "● Open Palm — Cursor   |   Closed Palm — Click   |   Index + Middle Together — Highlight"
            )

        elif tool == "eraser":

            self.gesture_status.setText(
                "● Open Palm — Cursor   |   Closed Palm — Click   |   Index + Middle Together — Erase"
            )

        elif tool == "shape":

            self.gesture_status.setText(
                f"● Shape Mode: {self.selected_shape}   |   Open Palm — Cursor   |   Closed Palm — Click"
            )

        else:

            self.gesture_status.setText(
                "● Open Palm — Cursor   |   Closed Palm — Click"
            )

    # ========================================================
    # SHAPE MENU
    # ========================================================

    def show_shape_menu(
        self
    ):

        menu = QMenu(
            self
        )

        menu.setStyleSheet("""
            QMenu {
                background: #FFFFFF;
                border: 1px solid #D7E5F3;
                padding: 5px;
            }

            QMenu::item {
                padding: 7px 25px 7px 10px;
                color: #0E2F76;
            }

            QMenu::item:selected {
                background: #E7F0FA;
            }
        """)

        shapes = [
            "Line",
            "Circle",
            "Rectangle",
            "Square",
            "Triangle",
            "Arrow",
        ]

        for shape in shapes:

            action = QAction(
                shape,
                self
            )

            action.triggered.connect(
                lambda
                checked=False,
                s=shape:
                self.select_shape(
                    s
                )
            )

            menu.addAction(
                action
            )

        menu.exec_(
            self.shape_button.mapToGlobal(
                QPoint(
                    0,
                    self.shape_button.height()
                )
            )
        )

    # ========================================================
    # SELECT SHAPE
    # ========================================================

    def select_shape(
        self,
        shape
    ):

        self.selected_shape = (
            shape
        )

        self.set_tool(
            "shape"
        )

    # ========================================================
    # COLOR
    # ========================================================

    def set_color(
        self,
        color
    ):

        self.current_color = (
            color
        )

        self.canvas.set_color(
            color
        )

        self.set_tool(
            "pen"
        )

    # ========================================================
    # BRUSH
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
            QMessageBox.Yes
            |
            QMessageBox.No,
            QMessageBox.No
        )

        if (
            reply
            ==
            QMessageBox.Yes
        ):

            self.canvas.clear_canvas()

    # ========================================================
    # MEDIAPIPE
    # ========================================================

    def setup_mediapipe(
        self
    ):

        if mp is None:

            return

        try:

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
                    model_complexity=0,
                    min_detection_confidence=0.55,
                    min_tracking_confidence=0.55
                )
            )

        except Exception:

            self.hands = None

    # ========================================================
    # FINGER DETECTION
    # ========================================================

    def finger_extended(
        self,
        landmarks,
        tip,
        pip
    ):

        return (
            landmarks[tip].y
            <
            landmarks[pip].y
            -
            0.015
        )

    # ========================================================
    # GESTURE DETECTION
    # ========================================================

    def detect_gesture(
        self,
        hand
    ):

        landmarks = (
            hand.landmark
        )

        index_up = (
            self.finger_extended(
                landmarks,
                self.mp_hands.HandLandmark.INDEX_FINGER_TIP,
                self.mp_hands.HandLandmark.INDEX_FINGER_PIP
            )
        )

        middle_up = (
            self.finger_extended(
                landmarks,
                self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
                self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP
            )
        )

        ring_up = (
            self.finger_extended(
                landmarks,
                self.mp_hands.HandLandmark.RING_FINGER_TIP,
                self.mp_hands.HandLandmark.RING_FINGER_PIP
            )
        )

        pinky_up = (
            self.finger_extended(
                landmarks,
                self.mp_hands.HandLandmark.PINKY_TIP,
                self.mp_hands.HandLandmark.PINKY_PIP
            )
        )

        index_tip = landmarks[
            self.mp_hands.HandLandmark.INDEX_FINGER_TIP
        ]

        middle_tip = landmarks[
            self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP
        ]

        wrist = landmarks[
            self.mp_hands.HandLandmark.WRIST
        ]

        index_mcp = landmarks[
            self.mp_hands.HandLandmark.INDEX_FINGER_MCP
        ]

        hand_scale = math.hypot(
            index_mcp.x
            -
            wrist.x,

            index_mcp.y
            -
            wrist.y
        )

        hand_scale = max(
            hand_scale,
            0.05
        )

        finger_distance = math.hypot(
            index_tip.x
            -
            middle_tip.x,

            index_tip.y
            -
            middle_tip.y
        )

        # ====================================================
        # INDEX + MIDDLE TOGETHER
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
            finger_distance
            <=
            hand_scale * 0.55
        ):

            return "DRAW"

        # ====================================================
        # CLOSED PALM
        # ====================================================

        if (
            not index_up
            and
            not middle_up
            and
            not ring_up
            and
            not pinky_up
        ):

            return "CLICK"

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

            return "CURSOR"

        return "IDLE"

    # ========================================================
    # START CAMERA
    # ========================================================

    def start_camera(
        self
    ):

        if self.camera_running:

            return

        camera_indices = []

        if (
            self.active_camera_index
            is not None
        ):

            camera_indices.append(
                self.active_camera_index
            )

        camera_indices.extend([
            0,
            1,
            2,
            3
        ])

        checked = set()

        for index in camera_indices:

            if index in checked:

                continue

            checked.add(
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

                camera.set(
                    cv2.CAP_PROP_FRAME_WIDTH,
                    640
                )

                camera.set(
                    cv2.CAP_PROP_FRAME_HEIGHT,
                    480
                )

                camera.set(
                    cv2.CAP_PROP_FPS,
                    30
                )

                self.camera = (
                    camera
                )

                self.camera_running = (
                    True
                )

                self.camera_timer.start(
                    30
                )

                return

            camera.release()

        self.camera_overlay.setText(
            "Camera unavailable"
        )

    # ========================================================
    # STOP CAMERA
    # ========================================================

    def stop_camera(
        self
    ):

        self.camera_running = (
            False
        )

        if self.camera_timer.isActive():

            self.camera_timer.stop()

        if self.camera is not None:

            self.camera.release()

            self.camera = None

    # ========================================================
    # CAMERA → SCREEN
    # ========================================================

    def camera_to_screen(
        self,
        x,
        y
    ):

        screen = (
            QApplication.primaryScreen()
        )

        if screen is None:

            return None

        geometry = (
            screen.geometry()
        )

        x = max(
            0.0,
            min(
                1.0,
                x
            )
        )

        y = max(
            0.0,
            min(
                1.0,
                y
            )
        )

        screen_x = (
            geometry.left()
            +
            int(
                x
                *
                (
                    geometry.width()
                    -
                    1
                )
            )
        )

        screen_y = (
            geometry.top()
            +
            int(
                y
                *
                (
                    geometry.height()
                    -
                    1
                )
            )
        )

        return QPoint(
            screen_x,
            screen_y
        )

    # ========================================================
    # OPEN PALM = SYSTEM CURSOR
    # ========================================================

    def move_system_cursor(
        self,
        hand
    ):

        index_tip = hand.landmark[
            self.mp_hands.HandLandmark.INDEX_FINGER_TIP
        ]

        target = (
            self.camera_to_screen(
                index_tip.x,
                index_tip.y
            )
        )

        if target is None:

            return

        if (
            self.cursor_x
            is None
        ):

            self.cursor_x = (
                target.x()
            )

            self.cursor_y = (
                target.y()
            )

        else:

            self.cursor_x = (
                self.cursor_x
                *
                (
                    1
                    -
                    self.cursor_smoothing
                )
                +
                target.x()
                *
                self.cursor_smoothing
            )

            self.cursor_y = (
                self.cursor_y
                *
                (
                    1
                    -
                    self.cursor_smoothing
                )
                +
                target.y()
                *
                self.cursor_smoothing
            )

        QCursor.setPos(
            int(
                self.cursor_x
            ),
            int(
                self.cursor_y
            )
        )

    # ========================================================
    # CLOSED PALM = REAL LEFT CLICK
    # ========================================================

    def click_under_cursor(
        self
    ):

        current_time = (
            time.monotonic()
        )

        if (
            current_time
            -
            self.last_click_time
            <
            0.65
        ):

            return

        self.last_click_time = (
            current_time
        )

        screen_position = (
            QCursor.pos()
        )

        widget = (
            QApplication.widgetAt(
                screen_position
            )
        )

        if widget is None:

            return

        # ----------------------------------------------------
        # FIND BUTTON
        # ----------------------------------------------------

        target = widget

        while target is not None:

            if isinstance(
                target,
                QPushButton
            ):

                local_position = (
                    target.mapFromGlobal(
                        screen_position
                    )
                )

                QTest.mouseClick(
                    target,
                    Qt.LeftButton,
                    Qt.NoModifier,
                    local_position
                )

                return

            target = (
                target.parentWidget()
            )

        # ----------------------------------------------------
        # SLIDER
        # ----------------------------------------------------

        if isinstance(
            widget,
            QSlider
        ):

            local_position = (
                widget.mapFromGlobal(
                    screen_position
                )
            )

            QTest.mouseClick(
                widget,
                Qt.LeftButton,
                Qt.NoModifier,
                local_position
            )

    # ========================================================
    # SCREEN → CANVAS
    # ========================================================

    def screen_to_canvas(
        self,
        screen_point
    ):

        local_point = (
            self.canvas.mapFromGlobal(
                screen_point
            )
        )

        if not (
            self.canvas.rect().contains(
                local_point
            )
        ):

            return None

        return QPoint(
            local_point.x(),
            local_point.y()
        )

    # ========================================================
    # INDEX + MIDDLE = DRAW
    # ========================================================

    def draw_gesture_segment(
        self,
        hand
    ):

        index_tip = hand.landmark[
            self.mp_hands.HandLandmark.INDEX_FINGER_TIP
        ]

        middle_tip = hand.landmark[
            self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP
        ]

        # Midpoint between the two fingers.
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

        screen_point = (
            self.camera_to_screen(
                x,
                y
            )
        )

        if screen_point is None:

            return

        canvas_point = (
            self.screen_to_canvas(
                screen_point
            )
        )

        # ====================================================
        # OUTSIDE WHITEBOARD
        # ====================================================

        if canvas_point is None:

            if self.gesture_drawing:

                self.gesture_drawing = (
                    False
                )

                self.last_draw_point = (
                    None
                )

                self.canvas.stroke_points = []

            return

        # ====================================================
        # START DRAWING
        # ====================================================

        if not self.gesture_drawing:

            self.canvas.save_state()

            self.gesture_drawing = (
                True
            )

            self.last_draw_point = (
                canvas_point
            )

            self.canvas.stroke_points = [
                canvas_point
            ]

            if self.current_tool == "shape":

                return

            self.canvas.draw_segment(
                canvas_point,
                canvas_point
            )

            return

        # ====================================================
        # CONTINUE DRAWING
        # ====================================================

        self.canvas.stroke_points.append(
            canvas_point
        )

        if self.current_tool != "shape":

            self.canvas.draw_segment(
                self.last_draw_point,
                canvas_point
            )

        self.last_draw_point = (
            canvas_point
        )

    # ========================================================
    # FINISH GESTURE DRAWING
    # ========================================================

    def finish_gesture_drawing(
        self
    ):

        if not self.gesture_drawing:

            return

        self.gesture_drawing = (
            False
        )

        self.last_draw_point = (
            None
        )

        points = list(
            self.canvas.stroke_points
        )

        self.canvas.stroke_points = []

        if len(points) < 2:

            return

        # ====================================================
        # SHAPE MODE
        # ====================================================

        if self.current_tool == "shape":

            self.canvas.draw_auto_shape(
                points
            )

        # ====================================================
        # PEN AUTO SHAPE
        # ====================================================

        elif (
            self.current_tool
            ==
            "pen"
            and
            len(points)
            >=
            5
        ):

            self.canvas.auto_correct_pen_stroke(
                points
            )

    # ========================================================
    # CAMERA UPDATE
    # ========================================================

    def update_camera(
        self
    ):

        if (
            not self.camera_running
            or
            self.camera is None
        ):

            return

        success, frame = (
            self.camera.read()
        )

        if not success:

            return

        # Mirror camera.
        frame = cv2.flip(
            frame,
            1
        )

        gesture = "IDLE"

        hand = None

        # ====================================================
        # MEDIAPIPE
        # ====================================================

        if self.hands is not None:

            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            rgb.flags.writeable = (
                False
            )

            results = (
                self.hands.process(
                    rgb
                )
            )

            rgb.flags.writeable = (
                True
            )

            if results.multi_hand_landmarks:

                hand = (
                    results.multi_hand_landmarks[0]
                )

                gesture = (
                    self.detect_gesture(
                        hand
                    )
                )

                if (
                    self.mp_drawing
                    is not None
                ):

                    self.mp_drawing.draw_landmarks(
                        frame,
                        hand,
                        self.mp_hands.HAND_CONNECTIONS
                    )

        current_time = (
            time.monotonic()
        )

        # ====================================================
        # GESTURE STABILIZATION
        # ====================================================

        if (
            gesture
            !=
            self.gesture_candidate
        ):

            self.gesture_candidate = (
                gesture
            )

            self.gesture_candidate_since = (
                current_time
            )

        stable = (
            current_time
            -
            self.gesture_candidate_since
            >=
            0.08
        )

        if stable:

            active_gesture = (
                self.gesture_candidate
            )

        else:

            active_gesture = (
                self.last_gesture
            )

        # ====================================================
        # OPEN PALM
        # ====================================================

        if (
            hand is not None
            and
            active_gesture
            ==
            "CURSOR"
        ):

            self.finish_gesture_drawing()

            self.move_system_cursor(
                hand
            )

            self.gesture_status.setText(
                "● Open Palm — Cursor"
            )

        # ====================================================
        # CLOSED PALM
        # ====================================================

        elif (
            hand is not None
            and
            active_gesture
            ==
            "CLICK"
        ):

            self.finish_gesture_drawing()

            self.click_under_cursor()

            self.gesture_status.setText(
                "● Closed Palm — LEFT CLICK"
            )

        # ====================================================
        # INDEX + MIDDLE
        # ====================================================

        elif (
            hand is not None
            and
            active_gesture
            ==
            "DRAW"
        ):

            self.draw_gesture_segment(
                hand
            )

            self.gesture_status.setText(
                "● Index + Middle Together — DRAW"
            )

        # ====================================================
        # SEPARATED FINGERS
        # ====================================================

        else:

            self.finish_gesture_drawing()

            if hand is None:

                self.gesture_status.setText(
                    "● No Hand Detected"
                )

            else:

                self.gesture_status.setText(
                    "● Fingers Separate — Drawing OFF"
                )

        self.last_gesture = (
            active_gesture
        )

        # ====================================================
        # CAMERA DISPLAY
        # ====================================================

        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        height, width, channels = (
            rgb_frame.shape
        )

        bytes_per_line = (
            channels
            *
            width
        )

        image = QImage(
            rgb_frame.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888
        ).copy()

        pixmap = (
            QPixmap.fromImage(
                image
            ).scaled(
                self.camera_overlay.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )

        self.camera_overlay.setPixmap(
            pixmap
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
            os.path.expanduser(
                "~"
            )
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

            QMessageBox.information(
                self,
                "Whiteboard Saved",
                "Your whiteboard has been saved to:\n\n"
                +
                file_path
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

        self.active_camera_index = (
            index
        )

        self.active_camera_name = (
            name
        )

        if self.isVisible():

            self.stop_camera()

            QTimer.singleShot(
                100,
                self.start_camera
            )

    # ========================================================
    # CAMERA NAME
    # ========================================================

    def updateCameraName(
        self,
        name
    ):

        self.active_camera_name = (
            name
        )

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

        self.camera_overlay.raise_()

        if not self.camera_running:

            QTimer.singleShot(
                150,
                self.start_camera
            )

    # ========================================================
    # HIDE EVENT
    # ========================================================

    def hideEvent(
        self,
        event
    ):

        self.finish_gesture_drawing()

        self.stop_camera()

        super().hideEvent(
            event
        )

    # ========================================================
    # CLOSE EVENT
    # ========================================================

    def closeEvent(
        self,
        event
    ):

        self.finish_gesture_drawing()

        self.stop_camera()

        if self.hands is not None:

            try:

                self.hands.close()

            except Exception:

                pass

        super().closeEvent(
            event
        )