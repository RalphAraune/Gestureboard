# gui/presentation.py

import html
import os
import sys
import time

import cv2
import fitz

# MediaPipe may fail to load its DLL on some Python setups. Make it optional so
# the rest of the app still starts; feature code guards against mp being None.
try:
    import mediapipe as mp
except Exception:
    print("MediaPipe import error:", sys.exc_info()[1])
    mp = None

# PyAutoGUI is used for the Index Finger presentation cursor. Keep it optional.
try:
    import pyautogui
except Exception:
    pyautogui = None

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint, QRect, QRectF, QSize
from PyQt5.QtGui import (
    QImage, QPixmap, QPainter, QPainterPath, QFont, QColor, QBrush, QPen
)
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QComboBox,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFrame,
    QMessageBox,
    QDialog,
    QDialogButtonBox,
    QProgressDialog,
    QSlider,
    QSizePolicy,
    QSplitter,
    QSplitterHandle,
    QStackedWidget,
    QButtonGroup,
)

from core.gesture_detector import GestureDetector
from core.presentation_controller import PresentationController

try:
    from pptx import Presentation as PptxPresentation
except Exception:
    PptxPresentation = None


# ============================================================
# SLIDE VIEW  (slide image + temporary transparent annotation layer)
# ============================================================

class SlideView(QWidget):
    """Shows a slide and lets the user draw a TEMPORARY transparent
    overlay on top of it.

    The annotation layer is cleared automatically whenever the slide
    changes, so every slide starts clean and nothing is ever saved.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.slide = None          # QPixmap of the current slide
        self.layer = None          # QImage (ARGB) annotation overlay

        self.tool = "pen"          # pen / highlighter / eraser
        self.color = QColor("#E81123")
        self.brush_size = 4

        self.drawing = False
        self.last_point = QPoint()

        self.undo_stack = []
        self.redo_stack = []

        self.setMinimumSize(240, 150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setStyleSheet("background: #0B1A30; border-radius: 6px;")

    # --------------------------------------------------------

    def _ensure_layer(self):

        if (
            self.layer is None
            or self.layer.size() != self.size()
            or self.size().isEmpty()
        ):

            new_layer = QImage(
                max(1, self.width()),
                max(1, self.height()),
                QImage.Format_ARGB32
            )

            new_layer.fill(Qt.transparent)

            if self.layer is not None:

                painter = QPainter(new_layer)

                painter.drawImage(0, 0, self.layer)

                painter.end()

            self.layer = new_layer

    def resizeEvent(self, event):

        self._ensure_layer()

        super().resizeEvent(event)

    # --------------------------------------------------------
    # SLIDE
    # --------------------------------------------------------

    def set_slide(self, pixmap):
        """Show a new slide and CLEAR any previous annotations."""

        self.slide = pixmap

        self.clear_annotations()

        self.update()

    def has_slide(self):
        return self.slide is not None

    def slide_rect(self):
        """Return the rect the slide is drawn into (centred, KeepAspect)."""

        if self.slide is None:
            return self.rect()

        scaled = self.slide.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2

        return QRect(x, y, scaled.width(), scaled.height())

    # --------------------------------------------------------
    # ANNOTATION
    # --------------------------------------------------------

    def clear_annotations(self):

        self._ensure_layer()

        self.layer.fill(Qt.transparent)

        self.undo_stack = []
        self.redo_stack = []

        self.update()

    def save_state(self):

        if self.layer is None:
            return

        self.undo_stack.append(self.layer.copy())

        if len(self.undo_stack) > 30:
            self.undo_stack.pop(0)

        self.redo_stack.clear()

    def undo(self):

        if not self.undo_stack:
            return

        self.redo_stack.append(self.layer.copy())
        self.layer = self.undo_stack.pop()
        self.update()

    def redo(self):

        if not self.redo_stack:
            return

        self.undo_stack.append(self.layer.copy())
        self.layer = self.redo_stack.pop()
        self.update()

    def _width(self):

        if self.tool == "eraser":
            return self.brush_size * 4

        if self.tool == "highlighter":
            return max(10, self.brush_size * 3)

        return self.brush_size

    def _draw(self, start, end):

        self._ensure_layer()

        painter = QPainter(self.layer)
        painter.setRenderHint(QPainter.Antialiasing, True)

        if self.tool == "eraser":

            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            pen = QPen(Qt.transparent, self._width())

        elif self.tool == "highlighter":

            color = QColor(self.color)
            color.setAlpha(90)
            pen = QPen(color, self._width())

        else:

            color = QColor(self.color)
            color.setAlpha(235)
            pen = QPen(color, self._width())

        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)

        painter.drawLine(start, end)

        painter.end()

        self.update()

    # --------------------------------------------------------
    # MOUSE (driven by the Virtual Mouse style gestures)
    # --------------------------------------------------------

    def mousePressEvent(self, event):

        if event.button() != Qt.LeftButton:
            return

        if self.slide is None:
            return

        self.save_state()

        self.drawing = True
        self.last_point = event.pos()

        self._draw(self.last_point, self.last_point)

    def mouseMoveEvent(self, event):

        if not self.drawing:
            return

        if not (event.buttons() & Qt.LeftButton):
            return

        point = event.pos()

        self._draw(self.last_point, point)

        self.last_point = point

    def mouseReleaseEvent(self, event):

        if event.button() == Qt.LeftButton:
            self.drawing = False

    # --------------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        painter.fillRect(self.rect(), QColor("#0B1A30"))

        if self.slide is not None:

            rect = self.slide_rect()

            scaled = self.slide.scaled(
                rect.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            painter.drawPixmap(rect.topLeft(), scaled)

        else:

            painter.setPen(QColor("#7890B5"))
            painter.setFont(QFont("Segoe UI", 14))
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                "No slides yet\n\n"
                "Press Choose file to open a PDF or PowerPoint."
            )

        if self.layer is not None:

            painter.drawImage(0, 0, self.layer)

        painter.end()


# ============================================================
# SMALL WIDGETS USED BY THE PAGE
# ============================================================

class ToneLabel(QLabel):
    """Status label whose colour follows its text.

    `rules` is a list of (substring, tone) pairs checked in order; the
    stylesheet colours the label through its `tone` property.
    """

    def __init__(self, text="", rules=(), parent=None):
        super().__init__(parent)
        self._rules = list(rules)
        self.setText(text)

    def setText(self, text):
        super().setText(text)

        lowered = text.lower()
        tone = next(
            (tone for key, tone in self._rules if key in lowered),
            "idle",
        )

        # Re-polish only on a change: camera text updates every frame.
        if tone != self.property("tone"):
            self.setProperty("tone", tone)
            self.style().unpolish(self)
            self.style().polish(self)


class CameraFeed(QWidget):
    """Camera preview that fills whatever space it gets.

    The frame keeps its aspect ratio and is centred on a rounded well,
    so the panel can be dragged to any size.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._pixmap = None
        self._text = ""
        self._bg = QColor("#DCE7F3")
        self._fg = QColor("#5A6B93")

        self.setMinimumSize(180, 110)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def sizeHint(self):
        return QSize(320, 240)

    def set_colors(self, background, text):
        self._bg = QColor(background)
        self._fg = QColor(text)
        self.update()

    def setText(self, text):
        self._text = text
        self._pixmap = None
        self.update()

    def setPixmap(self, pixmap):
        self._pixmap = pixmap
        self.update()

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        well = QPainterPath()
        well.addRoundedRect(QRectF(self.rect()), 10, 10)
        painter.setClipPath(well)
        painter.fillRect(self.rect(), self._bg)

        if self._pixmap is not None and not self._pixmap.isNull():

            scaled = self._pixmap.size().scaled(
                self.size(), Qt.KeepAspectRatio
            )
            target = QRect(QPoint(0, 0), scaled)
            target.moveCenter(self.rect().center())

            frame = QPainterPath()
            frame.addRoundedRect(QRectF(target), 10, 10)
            painter.setClipPath(frame)
            painter.drawPixmap(target, self._pixmap)

        elif self._text:

            painter.setPen(self._fg)
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(self.rect(), Qt.AlignCenter, self._text)

        painter.end()


class _GripHandle(QSplitterHandle):
    """Splitter handle drawn as a small pill so it reads as draggable."""

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        color = QColor(self.splitter().property("gripColor") or "#AAC0E1")

        if not self.underMouse():
            color.setAlpha(150)

        length = 36
        thickness = 4

        if self.orientation() == Qt.Horizontal:
            pill = QRectF(0, 0, thickness, length)
        else:
            pill = QRectF(0, 0, length, thickness)

        pill.moveCenter(QRectF(self.rect()).center())

        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(pill, 2, 2)
        painter.end()

    def enterEvent(self, event):
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)


class GripSplitter(QSplitter):

    def createHandle(self):
        return _GripHandle(self.orientation(), self)


class PresentationPage(QWidget):

    # Signal can be connected to your MainWindow if needed.
    presentationAction = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.parent_window = parent

        # ---------------------------------------------------------
        # PRESENTATION
        # ---------------------------------------------------------

        self.file_path = None
        self.file_type = "Auto Detect"

        self.pdf_document = None
        self.current_page = 0
        self.total_pages = 0
        self.ppt_slides = None

        # In-app fullscreen presentation window (gesture controlled).
        self.fullscreen_window = None

        # ---------------------------------------------------------
        # CAMERA
        # ---------------------------------------------------------

        self.camera = None
        self.camera_index = 0

        # MediaPipe is optional: if it failed to load, disable hand tracking
        # but keep the page (and the rest of the app) fully functional.
        if mp is not None:
            self.mp_hands = mp.solutions.hands
            self.mp_drawing = mp.solutions.drawing_utils

            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                model_complexity=1,
                min_detection_confidence=0.55,
                min_tracking_confidence=0.55,
            )
        else:
            self.mp_hands = None
            self.mp_drawing = None
            self.hands = None

        self.gesture_detector = GestureDetector()
        self.presentation_controller = PresentationController()

        self.detected_gesture = "None"
        self.current_action = "Ready"

        # ---------------------------------------------------------
        # ANNOTATION OVERLAY (temporary, on top of the slide)
        # ---------------------------------------------------------

        # Annotation mode is toggled with the Three Fingers gesture while
        # presenting. It draws on a temporary transparent overlay above the
        # current slide; the overlay is cleared on every slide change.
        self.annotation_mode = False

        self.annotation_toolbar = None

        self._annot_drawing = False

        self.left_click_cooldown = 0

        # Tracks whether this page has been opened at least once. Used to stop
        # gesture handling from firing at startup (splash screen).
        self._page_opened = False

        # Hand-gesture control switch.
        #
        # IMPORTANT state rules:
        #   * Opening Presentation Control does NOT enable gestures.
        #   * Only the Start Presentation button enables them.
        #   * Stop / Exit Full Screen disables them again.
        #   * Switching to any other sidebar page disables them.
        self.gestures_enabled = False

        # Index Finger cursor state (smoothed movement).
        self._cursor_prev_x = None
        self._cursor_prev_y = None
        self._cursor_smoothing = 0.5

        try:
            # Allow the gesture cursor to reach the screen edges/corners.
            pyautogui.FAILSAFE = False
            self._screen_w, self._screen_h = (
                pyautogui.size() if pyautogui else (1920, 1080)
            )
        except Exception:
            self._screen_w, self._screen_h = (1920, 1080)

        # ---------------------------------------------------------
        # BUILD UI
        # ---------------------------------------------------------

        self.build_ui()

        from widgets import page_background

        page_background.clear_layers(self)

        self.apply_theme()

        # ---------------------------------------------------------
        # CAMERA TIMER
        # ---------------------------------------------------------

        self.camera_timer = QTimer(self)
        self.camera_timer.timeout.connect(self.update_camera)

    # ============================================================
    # SHOW EVENT — start the camera only when the page is shown.
    # ============================================================

    def showEvent(self, event):
        super().showEvent(event)
        self._page_opened = True

        # Opening (or returning to) the page must NEVER auto-start the
        # presentation or enable gesture control. The user has to press
        # Start Presentation explicitly.
        self.gestures_enabled = False
        self._refresh_controls()

        if self.camera is None:
            self.start_camera()

    def deactivate_gestures(self):
        """Disable presentation gestures and close any fullscreen view.

        Called when navigating away from Presentation Control (or on Stop /
        Exit Full Screen) so gestures can never open the presentation while
        the user is on another page.
        """

        self.gestures_enabled = False
        self.exit_fullscreen()
        self._refresh_controls()

        # Leaving the page also ends annotation mode and clears the
        # temporary overlay (annotations are never kept).
        try:
            self.set_annotation_mode(False)
        except Exception:
            pass

    # ============================================================
    # UI
    # ============================================================

    def build_ui(self):

        self.setObjectName("presentationPage")

        # Width / height breakpoints flip these (see _apply_density).
        self._narrow = False
        self._short = False

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 24, 32, 24)
        main_layout.setSpacing(14)
        self._main_layout = main_layout

        # --------------------------------------------------------
        # HEADER  (title on the left, gesture on/off on the right)
        # --------------------------------------------------------

        header = QHBoxLayout()
        header.setSpacing(12)

        heading = QVBoxLayout()
        heading.setSpacing(2)

        title = QLabel("Presentation Control")
        title.setObjectName("pageTitle")

        self.subtitle = QLabel(
            "Choose your slides, press Start presenting, then use your "
            "hand to move through them."
        )
        self.subtitle.setObjectName("pageSubtitle")
        self.subtitle.setWordWrap(True)

        heading.addWidget(title)
        heading.addWidget(self.subtitle)

        self.status_gesture = ToneLabel(
            "● Gestures off",
            [("on", "good"), ("annotating", "warn")],
        )
        self.status_gesture.setObjectName("gesturePill")
        self.status_gesture.setToolTip(
            "Hand gestures only work after you press Start presenting."
        )

        header.addLayout(heading, 1)
        header.addWidget(self.status_gesture, 0, Qt.AlignTop)

        main_layout.addLayout(header)

        # --------------------------------------------------------
        # FILE BAR
        # --------------------------------------------------------

        file_bar = QFrame()
        file_bar.setObjectName("fileBar")

        file_layout = QHBoxLayout(file_bar)
        file_layout.setContentsMargins(8, 8, 12, 8)
        file_layout.setSpacing(12)

        self.upload_button = QPushButton("📂  Choose file")
        self.upload_button.setObjectName("uploadButton")
        self.upload_button.setFixedHeight(38)
        self.upload_button.setCursor(Qt.PointingHandCursor)
        self.upload_button.setToolTip("Open a PDF or PowerPoint (.pptx) file")
        self.upload_button.clicked.connect(self.upload_file)

        self.file_status = QLabel(
            "No file yet. Choose a PDF or PowerPoint (.pptx) file to begin."
        )
        self.file_status.setObjectName("fileStatus")
        self.file_status.setProperty("loaded", False)
        self.file_status.setTextFormat(Qt.RichText)
        # Long file names clip instead of widening the page.
        self.file_status.setSizePolicy(
            QSizePolicy.Ignored, QSizePolicy.Preferred
        )

        self.file_type_label = QLabel("Show")
        self.file_type_label.setObjectName("fieldLabel")

        self.file_type_combo = QComboBox()
        self.file_type_combo.setFixedHeight(38)
        self.file_type_combo.setMinimumWidth(130)
        self.file_type_combo.setToolTip(
            "Which files the file picker lists"
        )
        self.file_type_combo.addItems([
            "All supported",
            "PDF",
            "PowerPoint",
        ])

        file_layout.addWidget(self.upload_button)
        file_layout.addWidget(self.file_status, 1)
        file_layout.addWidget(self.file_type_label)
        file_layout.addWidget(self.file_type_combo)

        main_layout.addWidget(file_bar)

        # --------------------------------------------------------
        # BODY  (stage | side column, drag the gap to resize)
        # --------------------------------------------------------

        self.body_splitter = GripSplitter(Qt.Horizontal)
        self.body_splitter.setObjectName("bodySplitter")
        self.body_splitter.setChildrenCollapsible(False)
        self.body_splitter.setHandleWidth(14)

        # ========================================================
        # STAGE  (slide preview + control deck)
        # ========================================================

        stage = QFrame()
        stage.setObjectName("panel")

        stage_layout = QVBoxLayout(stage)
        stage_layout.setContentsMargins(14, 14, 14, 12)
        stage_layout.setSpacing(12)

        preview_holder = QWidget()

        preview_layout = QGridLayout(preview_holder)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        # Slide + temporary transparent annotation overlay.
        self.slide_view = SlideView()
        self.preview_label = self.slide_view

        self.slide_counter = QLabel("")
        self.slide_counter.setObjectName("slideCounter")
        self.slide_counter.setAlignment(Qt.AlignCenter)
        self.slide_counter.hide()

        preview_layout.addWidget(self.slide_view, 0, 0)
        preview_layout.addWidget(
            self.slide_counter, 0, 0, Qt.AlignTop | Qt.AlignRight
        )

        # Floating annotation toolbar (shown only in Annotation Mode).
        self.annotation_toolbar = self._build_annotation_toolbar()

        preview_layout.addWidget(
            self.annotation_toolbar, 0, 0, Qt.AlignTop | Qt.AlignLeft
        )

        stage_layout.addWidget(preview_holder, 1)

        # Control deck, laid out like a presenter remote:
        #   ‹ Previous  |  ▶ Start presenting  |  Next ›     ■ Stop

        self.previous_button = QPushButton()
        self.previous_button.setObjectName("navButton")
        self.previous_button.setToolTip(
            "Go back one slide\nGesture: point left 👈"
        )
        self.previous_button.clicked.connect(self.manual_previous)

        self.start_button = QPushButton()
        self.start_button.setObjectName("startButton")
        self.start_button.clicked.connect(self.manual_start)

        self.next_button = QPushButton()
        self.next_button.setObjectName("navButton")
        self.next_button.setToolTip(
            "Go forward one slide\nGesture: point right 👉"
        )
        self.next_button.clicked.connect(self.manual_next)

        self.stop_button = QPushButton()
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setToolTip(
            "Close full screen and turn hand gestures off"
        )
        self.stop_button.clicked.connect(self.manual_stop)

        deck = QHBoxLayout()
        deck.setSpacing(8)

        for button, stretch in (
            (self.previous_button, 2),
            (self.start_button, 3),
            (self.next_button, 2),
        ):
            button.setFixedHeight(44)
            button.setMinimumWidth(0)
            button.setCursor(Qt.PointingHandCursor)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            deck.addWidget(button, stretch)

        deck.addSpacing(10)

        self.stop_button.setFixedHeight(44)
        self.stop_button.setMinimumWidth(0)
        self.stop_button.setCursor(Qt.PointingHandCursor)
        self.stop_button.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        deck.addWidget(self.stop_button, 1)

        stage_layout.addLayout(deck)

        # One line that always says what to do next.
        self.hint_label = QLabel()
        self.hint_label.setObjectName("hintLabel")
        self.hint_label.setWordWrap(True)

        stage_layout.addWidget(self.hint_label)

        self.body_splitter.addWidget(stage)

        # ========================================================
        # SIDE COLUMN  (camera | gesture guide, drag to resize)
        # ========================================================

        self.side_splitter = GripSplitter(Qt.Vertical)
        self.side_splitter.setObjectName("sideSplitter")
        self.side_splitter.setChildrenCollapsible(False)
        self.side_splitter.setHandleWidth(14)
        self.side_splitter.setMinimumWidth(290)

        # -------------------- Camera --------------------

        camera_frame = QFrame()
        camera_frame.setObjectName("panel")

        camera_layout = QVBoxLayout(camera_frame)
        camera_layout.setContentsMargins(14, 12, 14, 12)
        camera_layout.setSpacing(10)

        camera_head = QHBoxLayout()
        camera_head.setSpacing(8)

        camera_title = QLabel("Camera")
        camera_title.setObjectName("panelTitle")

        self.camera_status = ToneLabel(
            "● Connecting…",
            [
                ("hand detected", "good"),
                ("not available", "bad"),
                ("connected", "info"),
                ("shared", "info"),
            ],
        )
        self.camera_status.setObjectName("cameraStatus")

        camera_head.addWidget(camera_title)
        camera_head.addStretch()
        camera_head.addWidget(self.camera_status)

        camera_layout.addLayout(camera_head)

        # Scales with the panel; keeps the camera's aspect ratio.
        self.camera_label = CameraFeed()
        self.camera_label.setText("Starting camera…")

        camera_layout.addWidget(self.camera_label, 1)

        readout = QGridLayout()
        readout.setHorizontalSpacing(12)
        readout.setVerticalSpacing(4)
        readout.setColumnStretch(1, 1)

        self.detected_label = QLabel("No gesture")
        self.status_action = QLabel("Ready")

        for row, (name, value) in enumerate((
            ("Seeing", self.detected_label),
            ("Last action", self.status_action),
        )):
            name_label = QLabel(name)
            name_label.setObjectName("readoutName")

            value.setObjectName("readoutValue")
            value.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

            readout.addWidget(name_label, row, 0)
            readout.addWidget(value, row, 1)

        # Hidden on short windows; the hint line under the deck covers it.
        self._action_row = [name_label, self.status_action]

        camera_layout.addLayout(readout)

        self.side_splitter.addWidget(camera_frame)

        # -------------------- Gesture guide --------------------

        guide_frame = QFrame()
        guide_frame.setObjectName("panel")

        guide_layout = QVBoxLayout(guide_frame)
        guide_layout.setContentsMargins(14, 12, 14, 12)
        guide_layout.setSpacing(8)

        self.guide_title = QLabel("Hand gestures")
        self.guide_title.setObjectName("panelTitle")

        guide_layout.addWidget(self.guide_title)

        # Same gesture list the tutorial and Settings show, split into
        # its two groups behind a segmented switch so it never needs
        # to scroll.
        from gui.tutorial import STEPS

        groups = STEPS[0]["groups"]

        segment_row = QHBoxLayout()
        segment_row.setSpacing(0)

        self.guide_stack = QStackedWidget()
        self._guide_grids = []
        self._guide_icons = []
        self.guide_tabs = QButtonGroup(self)
        self.guide_tabs.setExclusive(True)

        for index, (group_title, items) in enumerate(groups):

            tab = QPushButton(group_title)
            tab.setObjectName("segment")
            tab.setCheckable(True)
            tab.setCursor(Qt.PointingHandCursor)
            tab.setFixedHeight(30)
            tab.setProperty(
                "edge",
                "left" if index == 0
                else "right" if index == len(groups) - 1
                else "mid",
            )
            self.guide_tabs.addButton(tab, index)
            segment_row.addWidget(tab, 1)

            page = QWidget()

            rows = QGridLayout(page)
            rows.setContentsMargins(0, 2, 0, 0)
            rows.setHorizontalSpacing(10)
            rows.setVerticalSpacing(5)
            rows.setColumnStretch(1, 1)
            self._guide_grids.append(rows)

            for row, (icon, gesture, action) in enumerate(items):

                icon_label = QLabel(icon)
                icon_label.setObjectName("gestureIcon")
                icon_label.setFixedSize(28, 24)
                icon_label.setAlignment(Qt.AlignCenter)
                self._guide_icons.append(icon_label)

                gesture_label = QLabel(gesture)
                gesture_label.setObjectName("gestureName")
                gesture_label.setWordWrap(True)

                action_label = QLabel(action)
                action_label.setObjectName("gestureAction")
                action_label.setWordWrap(True)
                action_label.setAlignment(
                    Qt.AlignRight | Qt.AlignVCenter
                )

                rows.addWidget(icon_label, row, 0)
                rows.addWidget(gesture_label, row, 1)
                rows.addWidget(action_label, row, 2)

            rows.setRowStretch(len(items), 1)

            self.guide_stack.addWidget(page)

        self.guide_tabs.buttonClicked[int].connect(
            self.guide_stack.setCurrentIndex
        )
        self.guide_tabs.button(0).setChecked(True)

        guide_layout.addLayout(segment_row)
        guide_layout.addWidget(self.guide_stack, 1)

        self.side_splitter.addWidget(guide_frame)
        self.side_splitter.setStretchFactor(0, 1)
        self.side_splitter.setStretchFactor(1, 0)

        self.body_splitter.addWidget(self.side_splitter)
        self.body_splitter.setStretchFactor(0, 1)
        self.body_splitter.setStretchFactor(1, 0)
        self.body_splitter.setSizes([900, 360])

        for splitter in (self.body_splitter, self.side_splitter):
            splitter.handle(1).setToolTip("Drag to resize")

        main_layout.addWidget(self.body_splitter, 1)

        self._refresh_controls()

    # ============================================================
    # RESPONSIVE LAYOUT
    # ============================================================

    def resizeEvent(self, event):

        super().resizeEvent(event)
        self._apply_density()

    def _apply_density(self):
        """Tighten spacing and shorten labels on small windows so the
        whole page always fits without scrolling."""

        narrow = self.width() < 980
        short = self.height() < 700

        if (narrow, short) == (self._narrow, self._short):
            return

        self._narrow, self._short = narrow, short

        side = 18 if narrow else 32
        top = 14 if short else 24

        self._main_layout.setContentsMargins(side, top, side, top)
        self._main_layout.setSpacing(10 if short else 14)

        self.subtitle.setVisible(not short)
        self.guide_title.setVisible(not short)

        for widget in self._action_row:
            widget.setVisible(not short)

        for grid in self._guide_grids:
            grid.setVerticalSpacing(1 if short else 5)

        for icon in self._guide_icons:
            icon.setFixedSize(28, 20 if short else 24)

        self.camera_label.setMinimumHeight(80 if short else 110)
        self.file_type_label.setVisible(not narrow)
        self.side_splitter.setMinimumWidth(250 if narrow else 290)

        self._refresh_controls()

    # ============================================================
    # CONTROL STATE  (buttons, hint line and gesture pill)
    # ============================================================

    def _has_slides(self):

        return bool(self.pdf_document) or bool(
            getattr(self, "ppt_slides", None)
        )

    def _refresh_controls(self):

        if not hasattr(self, "start_button"):
            return

        loaded = self._has_slides()
        presenting = self.gestures_enabled
        narrow = self._narrow

        self.previous_button.setText("‹  Prev" if narrow else "‹  Previous")
        self.next_button.setText("Next  ›")
        self.stop_button.setText("■  Stop")

        if presenting:
            self.start_button.setText(
                "⤢  Full screen" if narrow else "⤢  Back to full screen"
            )
            self.start_button.setToolTip(
                "Reopen the slides full screen\nGesture: thumbs up 👍"
            )
        else:
            self.start_button.setText(
                "▶  Start" if narrow else "▶  Start presenting"
            )
            self.start_button.setToolTip(
                "Show the slides full screen and turn hand gestures on"
            )

        self.start_button.setEnabled(loaded)
        self.previous_button.setEnabled(loaded)
        self.next_button.setEnabled(loaded)
        self.stop_button.setEnabled(presenting)

        if not loaded:
            hint = "Choose a file above. Your slides show up here."
        elif self.annotation_mode:
            hint = (
                "Annotation mode: hold index and middle fingers together "
                "to draw. Show three fingers again to finish."
            )
        elif presenting:
            hint = (
                "Hand gestures are on. Point right for the next slide, "
                "point left to go back."
            )
        else:
            hint = (
                "Hand gestures are off. Press Start presenting to turn "
                "them on, or use Previous and Next."
            )

        self.hint_label.setText(hint)

        if self.annotation_mode:
            self.status_gesture.setText("● Annotating")
        elif presenting:
            self.status_gesture.setText("● Gestures on")
        else:
            self.status_gesture.setText("● Gestures off")

    def _update_counter(self):

        if self._has_slides() and self.total_pages:
            self.slide_counter.setText(
                f"Slide {self.current_page + 1} of {self.total_pages}"
            )
            self.slide_counter.show()
        else:
            self.slide_counter.hide()

    # ============================================================
    # THEME
    #
    # Every colour on this page lives in this one stylesheet, so
    # MainWindow can re-apply it when the user switches light / dark.
    # ============================================================

    def apply_theme(self):

        from settings import theme as app_theme
        from widgets import page_background

        c = self._page_colors = page_background.page_colors()

        dark = app_theme.is_dark()
        field = c["input_bg"] if dark else "#F5F9FD"
        well = c["bg"] if dark else "#DCE7F3"
        focus = c["accent"] if dark else c["sidebar_hover"]

        if dark:
            ok_bg, ok_text, ok_border = "#173B2E", "#5FD39A", "#245A45"
            stop_bg, stop_text, stop_border = "#3A2230", "#F59A93", "#5A3040"
            warn_bg, warn_text = "#3A3220", "#F2C46B"
            info_text = "#8DB4F5"
            disabled_bg, disabled_text = "#132742", "#5A7396"
        else:
            ok_bg, ok_text, ok_border = "#E3F4EA", "#23804F", "#B7E1C7"
            stop_bg, stop_text, stop_border = "#F8E3E1", "#B83227", "#EBC3BF"
            warn_bg, warn_text = "#FBF0D9", "#8A5A00"
            info_text = "#1B4499"
            disabled_bg, disabled_text = "#E4ECF6", "#9AAACA"

        self.camera_label.set_colors(well, c["text_secondary"])

        for splitter in (self.body_splitter, self.side_splitter):
            splitter.setProperty("gripColor", c["input_border"])
            splitter.handle(1).update()

        self.setStyleSheet(
            page_background.LAYER_RULE
            + page_background.combo_rules(c, field)
            + f"""
            QWidget#presentationPage {{
                background: transparent;
            }}

            QLabel {{
                background: transparent;
                color: {c['text']};
            }}

            QLabel#pageTitle {{
                font-size: 28px;
                font-weight: 800;
            }}

            QLabel#pageSubtitle {{
                font-size: 14px;
                color: {c['text_secondary']};
            }}

            QFrame#panel, QFrame#fileBar {{
                background: {c['card']};
                border: 1px solid {c['card_border']};
                border-radius: 14px;
            }}

            QLabel#panelTitle {{
                font-size: 15px;
                font-weight: 700;
            }}

            QLabel#fieldLabel {{
                color: {c['text_secondary']};
                font-size: 12px;
            }}

            /* ---------- Gesture on/off pill ---------- */

            QLabel#gesturePill {{
                background: {c['card']};
                border: 1px solid {c['card_border']};
                color: {c['text_secondary']};
                border-radius: 15px;
                padding: 6px 14px;
                font-size: 13px;
                font-weight: 700;
            }}

            QLabel#gesturePill[tone="good"] {{
                background: {ok_bg};
                border-color: {ok_border};
                color: {ok_text};
            }}

            QLabel#gesturePill[tone="warn"] {{
                background: {warn_bg};
                border-color: {warn_text};
                color: {warn_text};
            }}

            /* ---------- Buttons ---------- */

            QPushButton {{
                background: {field};
                color: {c['text']};
                border: 1px solid {c['input_border']};
                border-radius: 10px;
                font-size: 13px;
                font-weight: 600;
                padding: 6px 14px;
            }}

            QPushButton:hover {{
                background: {c['button_hover']};
            }}

            QPushButton:focus {{
                outline: none;
                border: 2px solid {focus};
            }}

            QPushButton:disabled {{
                background: {disabled_bg};
                color: {disabled_text};
                border: 1px solid {c['card_border']};
            }}

            QPushButton#uploadButton {{
                background: {c['primary']};
                color: {c['primary_text']};
                border: none;
                font-weight: 700;
                padding: 6px 18px;
            }}

            QPushButton#uploadButton:hover {{
                background: {c['sidebar_hover']};
                color: {c['sidebar_text']};
            }}

            QPushButton#navButton {{
                font-size: 14px;
            }}

            QPushButton#startButton {{
                background: {c['primary']};
                color: {c['primary_text']};
                border: none;
                font-size: 14px;
                font-weight: 700;
            }}

            QPushButton#startButton:hover {{
                background: {c['sidebar_hover']};
                color: {c['sidebar_text']};
            }}

            QPushButton#startButton:focus {{
                border: 2px solid {c['accent']};
            }}

            QPushButton#startButton:disabled {{
                background: {disabled_bg};
                color: {disabled_text};
            }}

            QPushButton#stopButton {{
                background: {stop_bg};
                color: {stop_text};
                border: 1px solid {stop_border};
            }}

            QPushButton#stopButton:hover {{
                border: 1px solid {stop_text};
            }}

            QPushButton#stopButton:disabled {{
                background: transparent;
                color: {disabled_text};
                border: 1px dashed {c['card_border']};
            }}

            /* ---------- File status ---------- */

            QLabel#fileStatus {{
                color: {c['text_secondary']};
                font-size: 13px;
            }}

            QLabel#fileStatus[loaded="true"] {{
                color: {c['text']};
            }}

            /* ---------- Stage ---------- */

            QLabel#slideCounter {{
                background: rgba(11, 26, 48, 0.82);
                color: #FFFFFF;
                padding: 5px 12px;
                margin: 10px;
                border-radius: 12px;
                font-weight: 600;
                font-size: 12px;
            }}

            QLabel#hintLabel {{
                color: {c['text_secondary']};
                font-size: 12px;
                padding: 0 2px;
            }}

            /* ---------- Camera ---------- */

            QLabel#cameraStatus {{
                color: {c['text_secondary']};
                font-size: 12px;
                font-weight: 600;
            }}

            QLabel#cameraStatus[tone="good"] {{
                color: {ok_text};
            }}

            QLabel#cameraStatus[tone="info"] {{
                color: {info_text};
            }}

            QLabel#cameraStatus[tone="bad"] {{
                color: {stop_text};
            }}

            QLabel#readoutName {{
                color: {c['text_secondary']};
                font-size: 12px;
            }}

            QLabel#readoutValue {{
                font-size: 13px;
                font-weight: 700;
            }}

            /* ---------- Gesture guide ---------- */

            QPushButton#segment {{
                background: {field};
                color: {c['text_secondary']};
                border: 1px solid {c['input_border']};
                border-radius: 0;
                font-size: 12px;
                padding: 4px 8px;
            }}

            QPushButton#segment[edge="left"] {{
                border-top-left-radius: 8px;
                border-bottom-left-radius: 8px;
                border-right: none;
            }}

            QPushButton#segment[edge="right"] {{
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }}

            QPushButton#segment:checked {{
                background: {c['primary']};
                color: {c['primary_text']};
                border-color: {c['primary']};
                font-weight: 700;
            }}

            QLabel#gestureIcon {{
                background: {c['button_hover']};
                border-radius: 7px;
                font-family: "Segoe UI Emoji";
                font-size: 14px;
            }}

            QLabel#gestureName {{
                font-size: 12px;
                font-weight: 700;
            }}

            QLabel#gestureAction {{
                font-size: 12px;
                color: {c['text_secondary']};
            }}

            /* ---------- Annotation bar (over the slide) ---------- */

            QFrame#annotBar {{
                background: rgba(11, 26, 48, 0.94);
                border: 1px solid #2A5A9E;
                border-radius: 12px;
                margin: 10px;
            }}

            QFrame#annotBar QPushButton#annotTool,
            QFrame#annotBar QPushButton#annotAction {{
                background: transparent;
                color: #EAF2FF;
                border: 1px solid transparent;
                border-radius: 7px;
                padding: 4px 9px;
                font-size: 12px;
                font-weight: 600;
            }}

            QFrame#annotBar QPushButton#annotTool:hover,
            QFrame#annotBar QPushButton#annotAction:hover {{
                background: #1B3A63;
            }}

            QFrame#annotBar QPushButton#annotTool:checked {{
                background: #3E7CF7;
                color: #0B1A30;
            }}

            QFrame#annotBar QPushButton#annotSwatch {{
                border: 2px solid rgba(255, 255, 255, 0.35);
                border-radius: 11px;
                padding: 0;
            }}

            QFrame#annotBar QPushButton#annotSwatch:checked {{
                border: 3px solid #7FD3FF;
            }}

            QFrame#annotBar QLabel#annotLabel {{
                color: #AAC0E1;
                font-size: 12px;
            }}

            QFrame#annotBar QSlider {{
                background: transparent;
            }}

            QSplitter::handle {{
                background: transparent;
            }}
            """
        )

        self.update()

    def _set_file_loaded(self, loaded):

        self.file_status.setProperty("loaded", bool(loaded))
        self.file_status.style().unpolish(self.file_status)
        self.file_status.style().polish(self.file_status)

    def _file_summary(self, file_path, kind):

        count = self.total_pages
        slides = "slide" if count == 1 else "slides"
        name = html.escape(os.path.basename(file_path))

        return f"<b>{name}</b>&nbsp;&nbsp;&nbsp;{kind}, {count} {slides}"

    # ============================================================
    # BACKGROUND
    # ============================================================

    def paintEvent(self, event):

        from widgets import page_background

        page_background.paint_page_background(self, self._page_colors)

    # ============================================================
    # STATUS ROW
    # ============================================================

    def add_status_row(self, layout, row, title, value):

        title_label = QLabel(title)
        title_label.setObjectName("statusName")

        value.setObjectName("statusValue")

        layout.addWidget(title_label, row, 0)
        layout.addWidget(
            value,
            row,
            1,
            alignment=Qt.AlignRight
        )

    # ============================================================
    # UPLOAD FILE
    # ============================================================

    def upload_file(self):

        selected_type = self.file_type_combo.currentText()

        if selected_type == "PDF":
            filter_text = "PDF Files (*.pdf)"

        elif selected_type == "PowerPoint":
            filter_text = (
                "PowerPoint Files (*.ppt *.pptx)"
            )

        else:
            filter_text = (
                "Presentation Files "
                "(*.pdf *.ppt *.pptx)"
            )

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Presentation",
            "",
            filter_text
        )

        if not file_path:
            return

        self.file_path = file_path

        self.presentation_controller.set_file(
            file_path
        )

        extension = (
            os.path.splitext(file_path)[1]
            .lower()
        )

        if extension == ".pdf":
            self.load_pdf(file_path)

        elif extension == ".pptx":
            self.load_powerpoint(file_path)

        elif extension == ".ppt":
            # Legacy binary .ppt files cannot be rendered in-app (python-pptx
            # only reads the modern .pptx format). Give a clear message
            # instead of the cryptic "Package not found" error.
            QMessageBox.warning(
                self,
                "Unsupported PowerPoint Format",
                "Legacy .ppt files are not supported.\n\n"
                "Please open the file in PowerPoint and use "
                "\"Save As\" → PowerPoint Presentation (*.pptx), "
                "then upload the .pptx file."
            )

        else:
            QMessageBox.warning(
                self,
                "Unsupported File",
                "Please select a PDF or PowerPoint (.pptx) file."
            )

    # ============================================================
    # PDF
    # ============================================================

    def load_pdf(self, file_path):

        try:

            if self.pdf_document:
                self.pdf_document.close()

            self.pdf_document = fitz.open(
                file_path
            )

            self.total_pages = len(
                self.pdf_document
            )

            self.current_page = 0

            self.file_status.setText(
                self._file_summary(file_path, "PDF")
            )

            self._set_file_loaded(True)

            self.render_pdf_page()

            self.update_status()

        except Exception as e:

            QMessageBox.critical(
                self,
                "PDF Error",
                f"Unable to load PDF:\n\n{e}"
            )

    # ============================================================
    # POWERPOINT
    # ============================================================

    def load_powerpoint(self, file_path):

        if PptxPresentation is None:
            QMessageBox.warning(
                self,
                "PowerPoint Unavailable",
                "python-pptx is not installed. "
                "Please install it to view PowerPoint files in-app."
            )
            return

        try:
            prs = PptxPresentation(file_path)

            slides = [slide for slide in prs.slides]
            self.total_pages = len(slides)
            self.current_page = 0

            self.ppt_slides = [
                self.render_pptx_slide(slide, prs)
                for slide in slides
            ]

            self.file_status.setText(
                self._file_summary(file_path, "PowerPoint")
            )

            self._set_file_loaded(True)

            self.render_pdf_page()

            self.update_status()

        except Exception as e:

            QMessageBox.critical(
                self,
                "PowerPoint Error",
                f"Unable to load PowerPoint:\n\n{e}"
            )

    # ============================================================
    # PPTX RENDER (in-app)
    # ============================================================

    def render_pptx_slide(self, slide, prs):
        """Render a python-pptx slide into a QImage using QPainter."""

        # Use a consistent canvas size (16:9-ish) scaled for display.
        width = 1600
        height = 900

        img = QImage(
            width,
            height,
            QImage.Format_ARGB32
        )
        img.fill(QColor("#FFFFFF"))

        painter = QPainter(img)
        painter.setRenderHint(
            QPainter.Antialiasing,
            True
        )

        # Slide dimensions from the presentation (EMU -> px).
        try:
            slide_w = prs.slide_width
            slide_h = prs.slide_height
            scale = width / float(slide_w)
        except Exception:
            scale = 1.0

        # Draw text shapes (title & body placeholders / text boxes).
        for shape in slide.shapes:
            try:
                if not shape.has_text_frame:
                    continue
                text = shape.text_frame.text.strip()
                if not text:
                    continue
                if text == "Click to add title":
                    continue

                left = int(shape.left * scale)
                top = int(shape.top * scale)
                s_width = int(shape.width * scale)
                s_height = int(shape.height * scale)

                is_title = (
                    shape.name.lower().startswith(
                        ("title", "subtitle")
                    )
                )

                # Auto-fit font so the full text is visible without clipping.
                body_font = 24
                font_size = (
                    46
                    if is_title
                    else body_font
                )

                box_w = max(30, s_width)
                box_h = max(30, s_height)

                while font_size > 8:
                    painter.setFont(
                        QFont("Segoe UI", font_size)
                    )
                    metrics = painter.fontMetrics()
                    needed_w = metrics.horizontalAdvance(text)
                    # Rough estimate: add padding for wrapped lines.
                    est_lines = max(
                        1,
                        needed_w // max(1, box_w) + 1
                    )
                    total_h = est_lines * metrics.height()
                    if total_h <= box_h or font_size <= 10:
                        break
                    font_size -= 2

                painter.setPen(
                    QColor("#132B5C")
                )
                painter.setFont(
                    QFont("Segoe UI", font_size)
                )

                rect = (
                    left,
                    top,
                    box_w,
                    box_h
                )

                painter.drawText(
                    rect[0],
                    rect[1],
                    rect[2],
                    rect[3],
                    Qt.AlignTop
                    | Qt.AlignLeft
                    | Qt.TextWordWrap,
                    text,
                )

            except Exception:
                continue

        painter.end()

        return img

    # ============================================================
    # PDF RENDER
    # ============================================================

    def render_pdf_page(self):

        # PowerPoint slides render from the in-app image cache.
        if getattr(self, "ppt_slides", None):
            if self.current_page < 0:
                self.current_page = 0
            if self.current_page >= self.total_pages:
                self.current_page = self.total_pages - 1

            img = self.ppt_slides[self.current_page]

            # set_slide() clears any annotations -> every slide starts clean.
            self.slide_view.set_slide(
                QPixmap.fromImage(img)
            )

            self._update_counter()

            self.refresh_fullscreen()
            return

        if not self.pdf_document:
            return

        if self.current_page < 0:
            self.current_page = 0

        if self.current_page >= self.total_pages:
            self.current_page = (
                self.total_pages - 1
            )

        page = self.pdf_document.load_page(
            self.current_page
        )

        matrix = fitz.Matrix(
            1.4,
            1.4
        )

        pix = page.get_pixmap(
            matrix=matrix,
            alpha=False
        )

        image = QImage(
            pix.samples,
            pix.width,
            pix.height,
            pix.stride,
            QImage.Format_RGB888
        )

        pixmap = QPixmap.fromImage(
            image
        )

        # set_slide() clears any annotations -> every slide starts clean.
        self.slide_view.set_slide(
            pixmap
        )

        self._update_counter()

        self.refresh_fullscreen()

    # ============================================================
    # PDF THUMBNAILS
    # ============================================================

    def clear_thumbnails(self):

        # Thumbnail strip was removed from the layout; keep this a safe no-op.
        if not hasattr(self, "thumbnail_layout"):
            return

        while self.thumbnail_layout.count():

            item = self.thumbnail_layout.takeAt(0)

            widget = item.widget()

            if widget:
                widget.deleteLater()

    def create_pdf_thumbnails(self):

        # Thumbnail strip was removed from the layout; keep this a safe no-op.
        if not hasattr(self, "thumbnail_layout"):
            return

        self.clear_thumbnails()

        if not self.pdf_document:
            return

        max_thumbnails = min(
            self.total_pages,
            30
        )

        for index in range(max_thumbnails):

            page = self.pdf_document.load_page(
                index
            )

            pix = page.get_pixmap(
                matrix=fitz.Matrix(
                    0.35,
                    0.35
                ),
                alpha=False
            )

            image = QImage(
                pix.samples,
                pix.width,
                pix.height,
                pix.stride,
                QImage.Format_RGB888
            )

            thumbnail = QPixmap.fromImage(
                image
            ).scaled(
                110,
                70,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            button = QPushButton()

            button.setFixedSize(
                120,
                82
            )

            button.setIcon(
                thumbnail
            )

            button.setIconSize(
                thumbnail.size()
            )

            button.clicked.connect(
                lambda checked=False,
                page_index=index:
                self.select_page(page_index)
            )

            self.thumbnail_layout.addWidget(
                button
            )

    def select_page(self, page_index):

        if not self.pdf_document:
            return

        self.current_page = page_index

        self.render_pdf_page()
        self.update_status()

    # ============================================================
    # CAMERA
    # ============================================================

    def _running_vmouse(self):
        """Return the Virtual Mouse page if it is currently tracking."""

        vmouse = getattr(
            self.parent_window, "virtual_mouse", None
        )

        if vmouse is not None and getattr(
            vmouse, "camera_running", False
        ):
            return vmouse

        return None

    def start_camera(self):

        # Do not open a second handle to the same webcam.
        if self.camera is not None:
            return

        # The Virtual Mouse already owns the webcam: reuse its frames and
        # hand landmarks instead of opening the device a second time, so
        # both features keep working together.
        if self._running_vmouse() is not None:

            self._last_shared_frame = None

            if not self.camera_timer.isActive():
                self.camera_timer.start(30)

            self.camera_status.setText(
                "● Shared with Virtual Mouse"
            )

            return

        self.camera = cv2.VideoCapture(
            self.camera_index,
            cv2.CAP_DSHOW
        )

        if not self.camera.isOpened():

            self.camera.release()

            self.camera = cv2.VideoCapture(
                self.camera_index
            )

        if self.camera.isOpened():

            self.camera.set(
                cv2.CAP_PROP_FRAME_WIDTH,
                640
            )

            self.camera.set(
                cv2.CAP_PROP_FRAME_HEIGHT,
                480
            )

            self.camera_timer.start(30)

            self.camera_status.setText(
                "● Connected"
            )

        else:

            # Release the failed handle and clear it so a later
            # showEvent()/navigation can try again.
            self.camera.release()
            self.camera = None

            self.camera_status.setText(
                "● Camera not available"
            )

            self.camera_label.setText(
                "No camera found.\nPick one in Camera Setup."
            )

    # ============================================================
    # CAMERA SELECTION
    # ============================================================

    def setActiveCamera(self, index, name):

        if index is None or index == self.camera_index:
            return

        # Open on its own, or mirroring the Virtual Mouse (timer only).
        was_open = (
            self.camera is not None
            or self.camera_timer.isActive()
        )

        self.release_camera()

        self.camera_index = index

        # Reopen on the new device only if this page was using the camera.
        if was_open and self.isVisible():
            self.start_camera()

    def updateCameraName(self, name):

        self.camera_name = name

    # ============================================================
    # RELEASE CAMERA
    #
    # Called by MainWindow when navigating away from this page so the
    # single webcam is freed for other pages (e.g. Virtual Mouse). This
    # prevents two pages from fighting over the same camera device.
    # ============================================================

    def release_camera(self):

        if self.camera_timer.isActive():
            self.camera_timer.stop()

        if self.camera is not None:
            self.camera.release()
            self.camera = None

    # ============================================================
    # UPDATE CAMERA
    # ============================================================

    def update_camera(self):

        if not self.camera:
            self.update_shared_camera()
            return

        success, frame = self.camera.read()

        if not success:
            return

        # --------------------------------------------------------
        # MIRROR CAMERA
        # --------------------------------------------------------

        frame = cv2.flip(
            frame,
            1
        )

        self.process_frame(frame)

    # ============================================================
    # SHARED CAMERA (from the Virtual Mouse)
    # ============================================================

    def update_shared_camera(self):

        vmouse = self._running_vmouse()

        if vmouse is None:

            # The Virtual Mouse stopped and freed the webcam: take it
            # over so presentation gestures keep working.
            self.camera_timer.stop()

            if self.isVisible():
                self.start_camera()

            return

        frame = vmouse.get_latest_frame()

        # Only handle each Virtual Mouse frame once, so a gesture is
        # not triggered twice from the same image.
        if frame is None or frame is getattr(
            self, "_last_shared_frame", None
        ):
            return

        self._last_shared_frame = frame

        # The Virtual Mouse already ran MediaPipe and drew the
        # landmarks; reuse its result instead of tracking again.
        self.process_frame(
            frame.copy(),
            shared_hand=vmouse.get_latest_hand()
        )

    # ============================================================
    # PROCESS FRAME (gestures + preview)
    # ============================================================

    def process_frame(self, frame, shared_hand=None):

        shared = shared_hand is not None or self.camera is None

        # --------------------------------------------------------
        # MEDIAPIPE
        # --------------------------------------------------------

        gesture = "None"

        if shared:

            if shared_hand is not None:

                gesture = self.gesture_detector.detect(
                    shared_hand
                )

                self.process_gesture(
                    gesture,
                    shared_hand
                )

                self.camera_status.setText(
                    "● Hand detected"
                )

            else:

                self.camera_status.setText(
                    "● Shared with Virtual Mouse"
                )

        # If MediaPipe is unavailable, just show the raw camera feed.
        elif self.hands is not None:

            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            rgb.flags.writeable = False

            results = self.hands.process(
                rgb
            )

            rgb.flags.writeable = True

            # ----------------------------------------------------
            # DRAW LANDMARKS
            # ----------------------------------------------------

            if results.multi_hand_landmarks:

                hand = results.multi_hand_landmarks[0]

                self.mp_drawing.draw_landmarks(
                    frame,
                    hand,
                    self.mp_hands.HAND_CONNECTIONS
                )

                gesture = (
                    self.gesture_detector.detect(
                        hand
                    )
                )

                self.process_gesture(
                    gesture,
                    hand
                )

                self.camera_status.setText(
                    "● Hand detected"
                )

            else:

                self.camera_status.setText(
                    "● Connected"
                )

        if gesture in ("None", "Unknown"):
            seen = "No gesture"
        elif self.gestures_enabled:
            seen = gesture
        else:
            seen = gesture + " (gestures off)"

        self.detected_label.setText(seen)

        # --------------------------------------------------------
        # CAMERA IMAGE
        # --------------------------------------------------------

        frame_rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        height, width, channel = (
            frame_rgb.shape
        )

        bytes_per_line = (
            channel * width
        )

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

        # CameraFeed scales it to the panel size when painting.
        self.camera_label.setPixmap(
            pixmap
        )

    # ============================================================
    # ANNOTATION TOOLBAR (floating, temporary)
    # ============================================================

    def _build_annotation_toolbar(self):

        # Dark glass bar floating over the slide; styled by the page
        # stylesheet (QFrame#annotBar) so it matches in both themes.
        bar = QFrame()
        bar.setObjectName("annotBar")
        bar.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)

        layout = QVBoxLayout(bar)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Row 1: tool choice, then history actions
        tools_row = QHBoxLayout()
        tools_row.setSpacing(4)

        self.annot_tools = QButtonGroup(bar)
        self.annot_tools.setExclusive(True)

        for tool, label in (
            ("pen", "✎ Pen"),
            ("highlighter", "▍ Highlighter"),
            ("eraser", "⌫ Eraser"),
        ):
            button = QPushButton(label)
            button.setObjectName("annotTool")
            button.setCheckable(True)
            button.setChecked(tool == "pen")
            button.clicked.connect(
                lambda checked=False, t=tool: self._set_annotation_tool(t)
            )
            self.annot_tools.addButton(button)
            tools_row.addWidget(button)

        # Keep the old attribute names for anything that refers to them.
        self.pen_btn, self.highlighter_btn, self.eraser_btn = (
            self.annot_tools.buttons()
        )

        tools_row.addSpacing(8)

        for label, tip, slot in (
            ("Undo", "Undo the last stroke", self.slide_view.undo),
            ("Redo", "Bring back the last undone stroke", self.slide_view.redo),
            ("Clear", "Erase everything on this slide", self.slide_view.clear_annotations),
        ):
            button = QPushButton(label)
            button.setObjectName("annotAction")
            button.setToolTip(tip)
            button.clicked.connect(slot)
            tools_row.addWidget(button)

        layout.addLayout(tools_row)

        # Row 2: colour swatches and brush size
        style_row = QHBoxLayout()
        style_row.setSpacing(6)

        self.annot_colors = QButtonGroup(bar)
        self.annot_colors.setExclusive(True)

        for color, name in (
            ("#E81123", "Red"),
            ("#FFB020", "Yellow"),
            ("#28C76F", "Green"),
            ("#2876E8", "Blue"),
            ("#FFFFFF", "White"),
        ):
            swatch = QPushButton()
            swatch.setObjectName("annotSwatch")
            swatch.setCheckable(True)
            swatch.setChecked(color == "#E81123")
            swatch.setFixedSize(22, 22)
            swatch.setToolTip(name)
            swatch.setStyleSheet(
                f"QPushButton {{ background: {color}; }}"
            )
            swatch.clicked.connect(
                lambda checked=False, c=color:
                self._set_annotation_color(c)
            )
            self.annot_colors.addButton(swatch)
            style_row.addWidget(swatch)

        style_row.addSpacing(10)

        size_label = QLabel("Size")
        size_label.setObjectName("annotLabel")
        style_row.addWidget(size_label)

        size_slider = QSlider(Qt.Horizontal)
        size_slider.setObjectName("annotSize")
        size_slider.setRange(1, 20)
        size_slider.setValue(4)
        size_slider.setFixedWidth(96)
        size_slider.valueChanged.connect(
            lambda v: setattr(self.slide_view, "brush_size", v)
        )
        style_row.addWidget(size_slider)
        style_row.addStretch()

        layout.addLayout(style_row)

        bar.hide()

        return bar

    def _set_annotation_tool(self, tool):

        self.slide_view.tool = tool

    def _set_annotation_color(self, color):

        self.slide_view.color = QColor(color)

    # ============================================================
    # GESTURE PROCESSING
    # ============================================================

    def process_gesture(self, gesture, hand=None):

        if gesture in ("None", "Unknown"):
            return

        # Only act once the page has been opened at least once.
        if not self._page_opened:
            return

        if not self.gestures_enabled:
            self.detected_label.setText(
                gesture + " (gestures off)"
            )
            return

        # ====================================================
        # ANNOTATION MODE GESTURES
        # ====================================================
        if self.annotation_mode:

            # 🖖 Three Fingers toggles annotation mode OFF.
            if gesture == "Three Fingers":
                self.set_annotation_mode(False)
                self.detected_gesture = gesture
                return

            # ✌️ Index + Middle together -> DRAW (hold left button + move)
            if gesture == "Index + Middle":
                self.move_cursor_from_hand(hand)
                self.begin_annotation_draw()
                self._set_action("Drawing")
                self.detected_gesture = gesture
                return

            # Any other gesture stops drawing.
            self.end_annotation_draw()

            # ✋ Open Hand -> move cursor over the floating toolbar.
            if gesture == "Open Hand":
                self.move_cursor_from_hand(hand)
                self._set_action("Cursor (select tool)")
                self.detected_gesture = gesture
                return

            # ✊ Fist -> click the floating toolbar.
            if gesture == "Fist":
                if self.left_click_cooldown <= 0:
                    self._safe_click()
                    self.left_click_cooldown = 8
                else:
                    self.left_click_cooldown -= 1
                self._set_action("Click")
                self.detected_gesture = gesture
                return

            # ☝️ Index Finger also moves the cursor (convenience).
            if gesture == "Index Finger":
                self.move_cursor_from_hand(hand)
                self.detected_gesture = gesture
                return

            self.detected_gesture = gesture
            return

        # ====================================================
        # PRESENTATION MODE GESTURES
        # ====================================================

        # ☝️ Index Finger -> move the presentation pointer (continuous).
        if gesture == "Index Finger":
            self.move_cursor_from_hand(hand)
            self.detected_gesture = gesture
            self._set_action("Cursor / Pointer")
            return

        # Discrete gestures fire once.
        if gesture == self.detected_gesture:
            return

        self.detected_gesture = gesture

        actions = {
            "Rock & Roll": "Start Presentation",
            "Point Right": "Next Slide",
            "Point Left": "Previous Slide",
            "Thumbs Up": "Full Screen",
            "Thumbs Down": "Exit Full Screen",
            "Three Fingers": "Annotation Mode",
        }

        action = actions.get(gesture, "Ready")

        self._set_action(action)

        self.presentationAction.emit(action)

        if gesture == "Rock & Roll":

            self.enter_fullscreen()

        elif gesture == "Point Right":

            self.next_pdf_preview()

            if self.fullscreen_window is not None:
                self.refresh_fullscreen()

        elif gesture == "Point Left":

            self.previous_pdf_preview()

            if self.fullscreen_window is not None:
                self.refresh_fullscreen()

        elif gesture == "Thumbs Up":

            self.enter_fullscreen()

        elif gesture == "Thumbs Down":

            self.exit_fullscreen()

            self._set_action("Exit Full Screen")

        elif gesture == "Three Fingers":

            # Enter Annotation Mode (temporary overlay on the current slide).
            self.set_annotation_mode(True)

        self.update_status()

    # ============================================================
    # ANNOTATION HELPERS
    # ============================================================

    def _set_action(self, text):

        self.current_action = text

        if hasattr(self, "status_action"):
            self.status_action.setText(text)


    def set_annotation_mode(self, enabled):

        self.annotation_mode = bool(enabled)

        if self.annotation_toolbar is not None:
            self.annotation_toolbar.setVisible(self.annotation_mode)

        # Always start the overlay clean.
        self.slide_view.clear_annotations()

        self.end_annotation_draw()

        # Show the drawing gestures while annotating.
        if hasattr(self, "guide_tabs"):
            tab = self.guide_tabs.button(1 if self.annotation_mode else 0)
            if tab is not None:
                tab.click()

        self._set_action(
            "Annotation Mode" if enabled else "Presentation"
        )

        self.update_status()

    def begin_annotation_draw(self):

        if self._annot_drawing:
            return

        try:
            pyautogui.mouseDown()
        except Exception:
            pass

        self._annot_drawing = True

    def end_annotation_draw(self):

        if not self._annot_drawing:
            return

        try:
            pyautogui.mouseUp()
        except Exception:
            pass

        self._annot_drawing = False

    def _safe_click(self):

        try:
            pyautogui.click()
        except Exception:
            pass

    # ============================================================
    # INDEX FINGER CURSOR
    # ============================================================

    def move_cursor_from_hand(self, hand):

        if (
            hand is None
            or pyautogui is None
            or self.mp_hands is None
        ):
            return

        try:

            tip = hand.landmark[
                self.mp_hands.HandLandmark.INDEX_FINGER_TIP
            ]

            # The camera feed is mirrored, so x already matches the user's
            # on-screen left/right. Map normalized (0..1) to screen pixels.
            target_x = int(tip.x * self._screen_w)
            target_y = int(tip.y * self._screen_h)

            if self._cursor_prev_x is None:
                self._cursor_prev_x = target_x
                self._cursor_prev_y = target_y

            smooth_x = (
                self._cursor_prev_x
                + (target_x - self._cursor_prev_x)
                * self._cursor_smoothing
            )

            smooth_y = (
                self._cursor_prev_y
                + (target_y - self._cursor_prev_y)
                * self._cursor_smoothing
            )

            smooth_x = max(
                0,
                min(self._screen_w - 1, int(smooth_x))
            )
            smooth_y = max(
                0,
                min(self._screen_h - 1, int(smooth_y))
            )

            pyautogui.moveTo(
                smooth_x,
                smooth_y,
                duration=0
            )

            self._cursor_prev_x = smooth_x
            self._cursor_prev_y = smooth_y

        except Exception:
            pass

    # ============================================================
    # PDF NEXT
    # ============================================================

    def next_pdf_preview(self):

        # Works for both PDF and PowerPoint (PPTX) presentations.
        if not self.pdf_document and not getattr(
            self,
            "ppt_slides",
            None
        ):
            return

        if (
            self.current_page
            < self.total_pages - 1
        ):

            self.current_page += 1

            self.render_pdf_page()

    # ============================================================
    # PDF PREVIOUS
    # ============================================================

    def previous_pdf_preview(self):

        # Works for both PDF and PowerPoint (PPTX) presentations.
        if not self.pdf_document and not getattr(
            self,
            "ppt_slides",
            None
        ):
            return

        if self.current_page > 0:

            self.current_page -= 1

            self.render_pdf_page()

    # ============================================================
    # MANUAL CONTROLS
    # ============================================================

    def manual_start(self):

        # A presentation must be loaded before it can start.
        if not self.pdf_document and not getattr(
            self,
            "ppt_slides",
            None
        ):
            QMessageBox.information(
                self,
                "No Presentation",
                "Upload a PDF or PowerPoint file first, "
                "then press Start Presentation."
            )
            return

        # Enable gesture control ONLY here (explicit user action).
        self.gestures_enabled = True

        self.presentation_controller.start_presentation()

        self.enter_fullscreen()

        self.current_action = (
            "Presentation Started"
        )

        self.update_status()

    def manual_stop(self):

        # Turn OFF hand-gesture control until Start is pressed again.
        self.gestures_enabled = False

        self.presentation_controller.end_presentation()

        self.exit_fullscreen()

        self.current_action = (
            "Presentation Stopped"
        )

        self.update_status()

    def manual_next(self):

        self.presentation_controller.next_slide()

        self.next_pdf_preview()

        if self.fullscreen_window is not None:
            self.refresh_fullscreen()

        self.current_action = (
            "Next Slide"
        )

        self.update_status()

    def manual_previous(self):

        self.presentation_controller.previous_slide()

        self.previous_pdf_preview()

        if self.fullscreen_window is not None:
            self.refresh_fullscreen()

        self.current_action = (
            "Previous Slide"
        )

        self.update_status()

    # ============================================================
    # STATUS
    # ============================================================

    def update_status(self):

        self._update_counter()

        self.status_action.setText(
            self.current_action
        )

        self._refresh_controls()

    # ============================================================
    # FULLSCREEN VIEWER
    # ============================================================

    def _current_slide_image(self):
        """Return the current slide as a QImage (PDF or PPTX)."""

        if getattr(self, "ppt_slides", None):
            if -1 < self.current_page < len(self.ppt_slides):
                return self.ppt_slides[self.current_page]
            return None

        if self.pdf_document:

            page = self.pdf_document.load_page(
                self.current_page
            )

            pix = page.get_pixmap(
                matrix=fitz.Matrix(1.4, 1.4),
                alpha=False
            )

            return QImage(
                pix.samples,
                pix.width,
                pix.height,
                pix.stride,
                QImage.Format_RGB888
            )

        return None

    def enter_fullscreen(self):
        """Open (or refresh) the in-app fullscreen presentation view."""

        # If no file is loaded yet, silently do nothing (do not popup during
        # startup/splash or when the user is on another screen).
        if not self.pdf_document and not getattr(
            self,
            "ppt_slides",
            None
        ):
            return

        if self.fullscreen_window is None:
            self.fullscreen_window = FullscreenViewer(
                self,
                self
            )

        self.fullscreen_window.showFullScreen()

        self.refresh_fullscreen()

    def refresh_fullscreen(self):
        """Push the current slide into the fullscreen viewer."""

        if self.fullscreen_window is not None:
            image = self._current_slide_image()

            if image is not None:
                self.fullscreen_window.set_slide(
                    image,
                    self.current_page + 1,
                    self.total_pages,
                )

    def exit_fullscreen(self):
        """Close the fullscreen view."""

        if self.fullscreen_window is not None:
            self.fullscreen_window.close()
            self.fullscreen_window = None

    # ============================================================
    # CLEANUP
    # ============================================================

    def close_camera(self):

        if self.camera_timer.isActive():
            self.camera_timer.stop()

        if self.camera:

            self.camera.release()
            self.camera = None

        if self.hands:
            self.hands.close()

        if self.pdf_document:

            self.pdf_document.close()
            self.pdf_document = None

    def closeEvent(self, event):

        self.close_camera()

        if self.fullscreen_window is not None:
            self.fullscreen_window.close()
            self.fullscreen_window = None

        event.accept()


# ============================================================
# FULLSCREEN VIEWER
# ============================================================

class FullscreenViewer(QDialog):
    """Black fullscreen window that displays the current presentation slide.

    Created as a frameless, always-on-top, independent window (no parent) so
    it can still show fullscreen even if the main GestureBoard window is
    minimized or the user is working in another application.
    """

    def __init__(self, parent=None, page=None):
        super().__init__()
        self.page = page

        self.setWindowTitle("Presentation")
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Window
            | Qt.WindowStaysOnTopHint
        )
        self.setStyleSheet("""
            QDialog {
                background: #000000;
            }
            QLabel {
                background: transparent;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.slide_label = QLabel("Loading slide...")
        self.slide_label.setAlignment(Qt.AlignCenter)
        self.slide_label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 18px;
        """)
        layout.addWidget(self.slide_label, 1)

        info = QLabel("")
        info.setObjectName("infoLabel")
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet("""
            color: #888888;
            font-size: 12px;
            padding: 6px;
        """)
        self.info_label = info
        layout.addWidget(info)

        # Cache the current image so we can re-scale on resize.
        self._image = None

    def set_slide(self, image, page_number, total_pages):
        """Display a slide image fullscreen."""

        self._image = image
        self._render()

        self.info_label.setText(
            f"{page_number} / {total_pages}"
        )

    def _render(self):
        if self._image is None:
            return

        pixmap = QPixmap.fromImage(self._image)

        pixmap = pixmap.scaled(
            self.slide_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.slide_label.setPixmap(pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._render()

    def keyPressEvent(self, event):
        # Allow ESC / Q to exit fullscreen too.
        if event.key() in (Qt.Key_Escape, Qt.Key_Q):
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        # Clear the page's reference so Full Screen can be re-opened cleanly
        # (e.g. after the user closes the window directly).
        if self.page is not None:
            self.page.fullscreen_window = None
        super().closeEvent(event)