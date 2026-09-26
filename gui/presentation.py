# gui/presentation.py

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

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint, QRect
from PyQt5.QtGui import QImage, QPixmap, QPainter, QFont, QColor, QBrush, QPen
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
    QScrollArea,
    QDialog,
    QDialogButtonBox,
    QProgressDialog,
    QSlider,
    QSizePolicy,
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

        self.setMinimumSize(360, 240)
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
                "Upload a PDF or PowerPoint file\n\n"
                "Your presentation preview will appear here."
            )

        if self.layer is not None:

            painter.drawImage(0, 0, self.layer)

        painter.end()


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

        # Debounce for discrete gestures so one gesture never fires twice.
        self._last_gesture_time = 0.0
        self._gesture_cooldown = 1.0

        # Whether the floating annotation toolbar is expanded.
        self.annotation_expanded = False

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

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 25, 30, 25)
        main_layout.setSpacing(18)

        # --------------------------------------------------------
        # TITLE
        # --------------------------------------------------------

        title = QLabel("Presentation Control")
        title.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: 700;
                color: #12377D;
            }
        """)

        subtitle = QLabel(
            "Control your presentation using hand gestures."
        )

        subtitle.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #7183A6;
            }
        """)

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # --------------------------------------------------------
        # UPLOAD BAR
        # --------------------------------------------------------

        upload_layout = QHBoxLayout()
        upload_layout.setSpacing(10)

        self.upload_button = QPushButton("📄  Upload File")
        self.upload_button.setFixedHeight(42)
        self.upload_button.clicked.connect(self.upload_file)

        self.file_type_combo = QComboBox()
        self.file_type_combo.setFixedHeight(42)
        self.file_type_combo.setFixedWidth(180)

        self.file_type_combo.addItems([
            "Auto Detect",
            "PDF",
            "PowerPoint",
        ])

        self.file_status = QLabel("● No File Loaded")

        self.file_status.setStyleSheet("""
            QLabel {
                background: #EAF2FF;
                color: #5574A8;
                padding: 10px 16px;
                border-radius: 8px;
                font-weight: 600;
            }
        """)

        upload_layout.addWidget(self.upload_button)
        upload_layout.addWidget(self.file_type_combo)
        upload_layout.addWidget(self.file_status)
        upload_layout.addStretch()

        main_layout.addLayout(upload_layout)

        # --------------------------------------------------------
        # CONTENT
        # --------------------------------------------------------

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # ========================================================
        # CENTER COLUMN  (presentation preview + buttons)
        # ========================================================

        center_column = QVBoxLayout()
        center_column.setSpacing(12)

        # --------------------------------------------------------
        # PRESENTATION PREVIEW  (slide counter at upper-right)
        # --------------------------------------------------------

        preview_frame = QFrame()
        preview_frame.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #D9E4F5;
                border-radius: 12px;
            }
        """)

        preview_layout = QGridLayout(preview_frame)
        preview_layout.setContentsMargins(16, 16, 16, 16)

        # Slide + temporary transparent annotation overlay.
        self.slide_view = SlideView()

        self.preview_label = self.slide_view

        # Slide counter overlaid at the preview's upper-right corner.
        self.slide_counter = QLabel("Slide 0 / 0")

        self.slide_counter.setAlignment(Qt.AlignCenter)

        self.slide_counter.setStyleSheet("""
            QLabel {
                background: rgba(18, 55, 125, 0.88);
                color: #FFFFFF;
                padding: 5px 12px;
                border-radius: 12px;
                font-weight: 600;
                font-size: 12px;
            }
        """)

        preview_layout.addWidget(self.preview_label, 0, 0)
        preview_layout.addWidget(
            self.slide_counter,
            0,
            0,
            Qt.AlignTop | Qt.AlignRight
        )

        # --------------------------------------------------------
        # FLOATING ANNOTATION TOOLBAR (shown only in Annotation Mode)
        # --------------------------------------------------------

        self.annotation_toolbar = self._build_annotation_toolbar()

        preview_layout.addWidget(
            self.annotation_toolbar,
            0,
            0,
            Qt.AlignTop | Qt.AlignLeft
        )

        # Small camera feed in the lower-right of the preview (used to aim
        # the annotation cursor / clicks).
        self.slide_camera = QLabel()
        self.slide_camera.setFixedSize(180, 135)
        self.slide_camera.setAlignment(Qt.AlignCenter)
        self.slide_camera.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.slide_camera.setStyleSheet(
            "QLabel { background: rgba(5,11,22,0.85); color: #AAC0E1;"
            " border: 2px solid #2A5A9E; border-radius: 8px; font-size: 11px; }"
        )
        self.slide_camera.setText("Camera")

        preview_layout.addWidget(
            self.slide_camera,
            0,
            0,
            Qt.AlignBottom | Qt.AlignRight
        )

        center_column.addWidget(preview_frame, 1)

        # --------------------------------------------------------
        # PRESENTATION BUTTONS  (directly under the preview)
        #   1 - 2 - 1 layout
        # --------------------------------------------------------

        self.start_button = QPushButton("Start Presentation")
        self.start_button.setFixedHeight(42)
        self.start_button.clicked.connect(
            self.manual_start
        )

        self.stop_button = QPushButton("Stop Presentation")
        self.stop_button.setFixedHeight(42)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background: #EAF8EF;
                color: #2A9561;
                border: 1px solid #B7E1C7;
                border-radius: 6px;
                font-weight: 600;
                padding: 8px;
            }
            QPushButton:hover {
                background: #D8F0E1;
            }
        """)
        self.stop_button.clicked.connect(
            self.manual_stop
        )

        self.previous_button = QPushButton("Previous Slide")
        self.previous_button.setFixedHeight(42)
        self.previous_button.clicked.connect(
            self.manual_previous
        )

        self.next_button = QPushButton("Next Slide")
        self.next_button.setFixedHeight(42)
        self.next_button.clicked.connect(
            self.manual_next
        )

        nav_row = QHBoxLayout()
        nav_row.setSpacing(10)
        nav_row.addWidget(self.previous_button)
        nav_row.addWidget(self.next_button)

        center_column.addWidget(self.start_button)
        center_column.addLayout(nav_row)
        center_column.addWidget(self.stop_button)

        content_layout.addLayout(center_column, 1)

        # ========================================================
        # RIGHT PANEL
        # ========================================================

        # Fixed-width container keeps the Gesture Controls, Presentation
        # Status and Camera panels the same size and prevents overlap.
        right_container = QWidget()
        right_container.setFixedWidth(370)

        right_panel = QVBoxLayout(right_container)
        right_panel.setContentsMargins(0, 0, 0, 0)
        right_panel.setSpacing(12)

        # --------------------------------------------------------
        # GESTURE CONTROLS
        # --------------------------------------------------------

        gesture_frame = QFrame()
        gesture_frame.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #D9E4F5;
                border-radius: 12px;
            }
        """)

        gesture_layout = QVBoxLayout(gesture_frame)
        gesture_layout.setContentsMargins(14, 12, 14, 12)
        gesture_layout.setSpacing(7)

        gesture_title = QLabel("Gesture Controls")

        gesture_title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: 700;
                color: #12377D;
            }
        """)

        gesture_layout.addWidget(gesture_title)

        gestures = [
            ("🤘", "Rock & Roll", "Start Presentation"),
            ("👉", "Point Right", "Next Slide"),
            ("👈", "Point Left", "Previous Slide"),
            ("👍", "Thumbs Up", "Full Screen"),
            ("✋", "Open Hand", "Exit Full Screen"),
            ("☝️", "Index Finger", "Cursor / Pointer"),
        ]

        for icon, gesture, action in gestures:

            row = QHBoxLayout()
            row.setSpacing(8)

            icon_label = QLabel(icon)
            icon_label.setFixedSize(30, 26)
            icon_label.setAlignment(Qt.AlignCenter)

            icon_label.setStyleSheet("""
                QLabel {
                    background: #E8F0FA;
                    border-radius: 6px;
                    font-size: 15px;
                }
            """)

            gesture_label = QLabel(gesture)

            gesture_label.setStyleSheet("""
                QLabel {
                    color: #5273A9;
                    font-weight: 600;
                    font-size: 12px;
                }
            """)

            action_label = QLabel(action)

            action_label.setStyleSheet("""
                QLabel {
                    color: #7183A6;
                    font-size: 12px;
                }
            """)

            row.addWidget(icon_label)
            row.addWidget(gesture_label)
            row.addStretch()
            row.addWidget(action_label)

            gesture_layout.addLayout(row)

        right_panel.addWidget(gesture_frame)

        # --------------------------------------------------------
        # PRESENTATION STATUS
        # --------------------------------------------------------

        status_frame = QFrame()

        status_frame.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #D9E4F5;
                border-radius: 12px;
            }
        """)

        status_layout = QGridLayout(status_frame)
        status_layout.setContentsMargins(14, 12, 14, 12)
        status_layout.setVerticalSpacing(8)

        status_title = QLabel("Presentation Status")

        status_title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: 700;
                color: #12377D;
            }
        """)

        status_layout.addWidget(status_title, 0, 0, 1, 2)

        self.status_slide = QLabel("0 / 0")
        self.status_mode = QLabel("Waiting")
        self.status_gesture = QLabel("● Inactive")
        self.status_action = QLabel("Ready")

        self.add_status_row(
            status_layout,
            1,
            "Current Slide",
            self.status_slide,
        )

        self.add_status_row(
            status_layout,
            2,
            "Mode",
            self.status_mode,
        )

        self.add_status_row(
            status_layout,
            3,
            "Gesture Recognition",
            self.status_gesture,
        )

        self.add_status_row(
            status_layout,
            4,
            "Current Action",
            self.status_action,
        )

        right_panel.addWidget(status_frame)

        # --------------------------------------------------------
        # CAMERA
        # --------------------------------------------------------

        camera_frame = QFrame()

        camera_frame.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #D9E4F5;
                border-radius: 12px;
            }
        """)

        camera_layout = QVBoxLayout(camera_frame)

        camera_layout.setContentsMargins(
            15, 15, 15, 15
        )

        camera_title = QLabel("Camera")

        camera_title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: 700;
                color: #12377D;
            }
        """)

        camera_layout.addWidget(camera_title)

        self.camera_label = QLabel()

        self.camera_label.setFixedSize(330, 190)

        self.camera_label.setAlignment(Qt.AlignCenter)

        self.camera_label.setStyleSheet("""
            QLabel {
                background: #E8EEF7;
                border-radius: 8px;
                color: #7890B5;
            }
        """)

        self.camera_label.setText("Starting Camera...")

        camera_layout.addWidget(
            self.camera_label,
            alignment=Qt.AlignCenter
        )

        # Separate status block placed BELOW the feed so it never covers it.
        status_block = QFrame()
        status_block.setStyleSheet("""
            QFrame {
                background: #F2F6FC;
                border: 1px solid #D9E4F5;
                border-radius: 8px;
            }
            QLabel {
                background: transparent;
            }
        """)

        status_block_layout = QVBoxLayout(status_block)
        status_block_layout.setContentsMargins(
            10, 8, 10, 8
        )
        status_block_layout.setSpacing(4)

        self.camera_status = QLabel(
            "● Camera Connecting..."
        )

        self.camera_status.setStyleSheet("""
            QLabel {
                color: #5273A9;
                font-weight: 600;
            }
        """)

        status_block_layout.addWidget(self.camera_status)

        self.detected_label = QLabel(
            "Detected: None"
        )

        self.detected_label.setStyleSheet("""
            QLabel {
                color: #12377D;
                font-weight: 600;
            }
        """)

        status_block_layout.addWidget(self.detected_label)

        camera_layout.addWidget(status_block)

        right_panel.addWidget(camera_frame)

        right_panel.addStretch()

        # Wrap the right column in a scroll area so the page can shrink
        # vertically (responsive) instead of forcing a tall minimum height.
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.NoFrame)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        right_scroll.setFixedWidth(390)
        right_scroll.setWidget(right_container)

        content_layout.addWidget(right_scroll)

        main_layout.addLayout(content_layout)

    # ============================================================
    # STATUS ROW
    # ============================================================

    def add_status_row(self, layout, row, title, value):

        title_label = QLabel(title)

        title_label.setStyleSheet("""
            QLabel {
                color: #7183A6;
            }
        """)

        value.setStyleSheet("""
            QLabel {
                color: #12377D;
                font-weight: 600;
            }
        """)

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

            self.status_mode.setText("PDF")

            self.file_status.setText(
                "● "
                + os.path.basename(file_path)
                + " — PDF Loaded"
            )

            self.file_status.setStyleSheet("""
                QLabel {
                    background: #EAF8EF;
                    color: #2A9561;
                    padding: 10px 16px;
                    border-radius: 8px;
                    font-weight: 600;
                }
            """)

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

            self.status_mode.setText("PowerPoint")

            self.file_status.setText(
                "● "
                + os.path.basename(file_path)
                + " — PowerPoint Loaded"
            )

            self.file_status.setStyleSheet("""
                QLabel {
                    background: #EAF8EF;
                    color: #2A9561;
                    padding: 10px 16px;
                    border-radius: 8px;
                    font-weight: 600;
                }
            """)

            self.render_pdf_page()

            self.slide_counter.setText(
                f"Slide {self.current_page + 1} / "
                f"{self.total_pages}"
            )

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

            self.slide_counter.setText(
                f"Slide {self.current_page + 1} / "
                f"{self.total_pages}"
            )

            self.status_slide.setText(
                f"{self.current_page + 1} / "
                f"{self.total_pages}"
            )

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

        self.slide_counter.setText(
            f"Slide {self.current_page + 1} / "
            f"{self.total_pages}"
        )

        self.status_slide.setText(
            f"{self.current_page + 1} / "
            f"{self.total_pages}"
        )

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

    def start_camera(self):

        # Presentation Control does NOT open the webcam itself. It mirrors the
        # Virtual Mouse camera (frame + hand landmarks) so one camera serves
        # both presentation gestures and the annotation cursor / clicks.
        self.camera = None

        if not self.camera_timer.isActive():
            self.camera_timer.start(30)

        self.camera_status.setText(
            "● Camera (Virtual Mouse)"
        )

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

        # No own camera: use the Virtual Mouse's shared camera + hand.
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

        # --------------------------------------------------------
        # MEDIAPIPE
        # --------------------------------------------------------

        gesture = "None"

        # If MediaPipe is unavailable, just show the raw camera feed.
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
                    "● Hand Detected"
                )

            else:

                self.camera_status.setText(
                    "● Camera Connected"
                )

        self.detected_label.setText(
            "Detected: "
            + gesture
        )

        # --------------------------------------------------------
        # CAMERA IMAGE
        # --------------------------------------------------------

        self._display_frame(frame)

    # ============================================================
    # SHARED CAMERA (from the Virtual Mouse)
    # ============================================================

    def update_shared_camera(self):

        vm = getattr(self.parent_window, "virtual_mouse", None)

        if vm is None or not hasattr(vm, "get_latest_frame"):
            return

        frame = vm.get_latest_frame()

        if frame is None:

            self.camera_status.setText("● Waiting for Virtual Mouse…")
            return

        # Use the Virtual Mouse's detected hand for our own gesture logic.
        hand = (
            vm.get_latest_hand()
            if hasattr(vm, "get_latest_hand")
            else None
        )

        if hand is not None:

            gesture = self.gesture_detector.detect(hand)

            self.process_gesture(gesture, hand)

            self.camera_status.setText("● Hand Detected")

            self.detected_label.setText("Detected: " + gesture)

        else:

            self.camera_status.setText("● Camera Connected")

            self.detected_label.setText("Detected: None")

        self._display_frame(frame)

    def _display_frame(self, frame):

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

        pixmap = pixmap.scaled(
            self.camera_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.camera_label.setPixmap(
            pixmap
        )

        # Mirror the same feed into the small lower-right preview over the
        # slide, so the user can aim the annotation cursor / clicks.
        if hasattr(self, "slide_camera"):

            self.slide_camera.setPixmap(
                pixmap.scaled(
                    self.slide_camera.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )

        # And into the fullscreen viewer's lower-right camera feed.
        if self.fullscreen_window is not None:

            try:
                self.fullscreen_window.set_camera_frame(pixmap)
            except Exception:
                pass

    # ============================================================
    # ANNOTATION TOOLBAR (floating, temporary)
    # ============================================================

    def _build_annotation_toolbar(self):

        container = QFrame()
        container.setStyleSheet("QFrame { background: transparent; }")

        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)
        outer.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        # --------------------------------------------------
        # Floating pen button (upper-left)
        # --------------------------------------------------
        self.pen_toggle = QPushButton("✎")
        self.pen_toggle.setToolTip("Annotation tools")
        self.pen_toggle.setFixedSize(40, 40)
        self.pen_toggle.setCursor(Qt.PointingHandCursor)
        self.pen_toggle.setStyleSheet(
            "QPushButton { background: rgba(10,22,40,0.94); color: #EAF2FF;"
            " border: 1px solid #2A5A9E; border-radius: 10px;"
            " font-size: 18px; }"
            "QPushButton:hover { background: #1B3A63; }"
        )
        self.pen_toggle.clicked.connect(self._toggle_annotation_tools)
        outer.addWidget(self.pen_toggle)

        # --------------------------------------------------
        # Tools row (hidden until the pen button is clicked)
        # --------------------------------------------------
        self.annotation_tools = QFrame()
        self.annotation_tools.setStyleSheet(
            "QFrame { background: rgba(10,22,40,0.94);"
            " border: 1px solid #2A5A9E; border-radius: 10px; }"
            "QLabel { color: #AAC0E1; font-size: 12px; }"
            "QPushButton { background: transparent; color: #EAF2FF;"
            " border: none; padding: 6px 10px; border-radius: 6px;"
            " font-size: 13px; }"
            "QPushButton:hover { background: #1B3A63; }"
        )

        layout = QHBoxLayout(self.annotation_tools)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(6)

        self.pen_btn = QPushButton("Pen")
        self.highlighter_btn = QPushButton("Highlighter")
        self.eraser_btn = QPushButton("Eraser")

        self.pen_btn.clicked.connect(
            lambda: self._set_annotation_tool("pen")
        )
        self.highlighter_btn.clicked.connect(
            lambda: self._set_annotation_tool("highlighter")
        )
        self.eraser_btn.clicked.connect(
            lambda: self._set_annotation_tool("eraser")
        )

        layout.addWidget(self.pen_btn)
        layout.addWidget(self.highlighter_btn)
        layout.addWidget(self.eraser_btn)

        layout.addWidget(QLabel("Colour:"))

        for color in (
            "#E81123",
            "#FFB020",
            "#28C76F",
            "#2876E8",
            "#FFFFFF",
        ):

            swatch = QPushButton()
            swatch.setFixedSize(20, 20)
            swatch.setStyleSheet(
                f"QPushButton {{ background:{color};"
                " border:2px solid #FFFFFF; border-radius:10px; }}"
            )
            swatch.clicked.connect(
                lambda checked=False, c=color:
                self._set_annotation_color(c)
            )
            layout.addWidget(swatch)

        layout.addWidget(QLabel("Size:"))

        size_slider = QSlider(Qt.Horizontal)
        size_slider.setRange(1, 20)
        size_slider.setValue(4)
        size_slider.setFixedWidth(90)
        size_slider.valueChanged.connect(
            lambda v: setattr(self.slide_view, "brush_size", v)
        )
        layout.addWidget(size_slider)

        undo_btn = QPushButton("Undo")
        redo_btn = QPushButton("Redo")
        clear_btn = QPushButton("Clear")

        undo_btn.clicked.connect(self.slide_view.undo)
        redo_btn.clicked.connect(self.slide_view.redo)
        clear_btn.clicked.connect(self.slide_view.clear_annotations)

        layout.addWidget(undo_btn)
        layout.addWidget(redo_btn)
        layout.addWidget(clear_btn)

        self.annotation_tools.hide()

        container.hide()

        return container

    def _toggle_annotation_tools(self):

        self.annotation_expanded = not self.annotation_expanded

        self.annotation_tools.setVisible(self.annotation_expanded)

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

            # Even while gestures are inactive, the START gesture is allowed
            # so the user can begin the presentation with a hand gesture.
            if gesture == "Rock & Roll" and self._debounce_ok():
                self.manual_start()
            else:
                self.detected_label.setText("Detected: " + gesture)
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

        # Discrete gestures fire once (and are debounced). Pointing gestures
        # may repeat while held so the user can advance several slides.
        repeatable = ("Point Right", "Point Left")

        if gesture == self.detected_gesture and gesture not in repeatable:
            return

        self.detected_gesture = gesture

        if not self._debounce_ok():
            return

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

        if hasattr(self, "status_gesture"):
            self.status_gesture.setText("● " + text)

    def set_annotation_mode(self, enabled):

        self.annotation_mode = bool(enabled)

        if self.annotation_toolbar is not None:
            self.annotation_toolbar.setVisible(self.annotation_mode)

        # Collapse the tools back to just the floating pen button and
        # always start the overlay clean.
        self.annotation_expanded = False

        if hasattr(self, "annotation_tools"):
            self.annotation_tools.setVisible(False)

        self.slide_view.clear_annotations()

        self.end_annotation_draw()

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

    def _debounce_ok(self):
        """True at most once per cooldown window (debounce gestures)."""

        now = time.time()

        if now - self._last_gesture_time < self._gesture_cooldown:
            return False

        self._last_gesture_time = now
        return True

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

            # While writing, smooth a lot more so the line is steady (less
            # shaky). Moving the pointer uses lighter smoothing.
            smoothing = 0.35 if self._annot_drawing else self._cursor_smoothing

            smooth_x = (
                self._cursor_prev_x
                + (target_x - self._cursor_prev_x)
                * smoothing
            )

            smooth_y = (
                self._cursor_prev_y
                + (target_y - self._cursor_prev_y)
                * smoothing
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

        self.status_gesture.setText(
            "● Active"
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

        self.status_gesture.setText(
            "● Inactive"
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

        if self.pdf_document:

            self.status_slide.setText(
                f"{self.current_page + 1} / "
                f"{self.total_pages}"
            )

        elif self.file_path:

            self.status_slide.setText(
                "PowerPoint"
            )

        else:

            self.status_slide.setText(
                "0 / 0"
            )

        self.status_mode.setText(
            self.file_type_combo.currentText()
        )

        self.status_action.setText(
            self.current_action
        )

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
    """Fullscreen presentation window WITH temporary annotation support.

    A frameless, always-on-top, independent window so it can show fullscreen
    even if the main GestureBoard window is minimized. It uses a SlideView so
    the user can draw a temporary overlay directly on the slide (cleared on
    every slide change). A small floating pen button opens the tools.
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
        self.setStyleSheet("QDialog { background: #000000; }")

        root = QGridLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.slide_view = SlideView()
        root.addWidget(self.slide_view, 0, 0)

        # Floating pen button (upper-left) + expandable tools.
        self.pen_button = QPushButton("\u270e")
        self.pen_button.setToolTip("Annotation tools")
        self.pen_button.setFixedSize(40, 40)
        self.pen_button.setCursor(Qt.PointingHandCursor)
        self.pen_button.setStyleSheet(
            "QPushButton { background: rgba(10,22,40,0.94); color: #EAF2FF;"
            " border: 1px solid #2A5A9E; border-radius: 10px;"
            " font-size: 18px; }"
            "QPushButton:hover { background: #1B3A63; }"
        )
        self.pen_button.clicked.connect(self._toggle_tools)

        self.tools = self._build_tools()
        self.tools.hide()

        overlay = QWidget()
        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.setContentsMargins(12, 12, 12, 12)
        overlay_layout.setSpacing(6)
        overlay_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        overlay_layout.addWidget(self.pen_button)
        overlay_layout.addWidget(self.tools)

        root.addWidget(
            overlay,
            0,
            0,
            Qt.AlignTop | Qt.AlignLeft
        )

        # Small camera feed in the lower-right (shows the presentation camera
        # so the user can aim the gesture cursor / annotation).
        self.camera_feed = QLabel()
        self.camera_feed.setFixedSize(200, 150)
        self.camera_feed.setAlignment(Qt.AlignCenter)
        self.camera_feed.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.camera_feed.setStyleSheet(
            "QLabel { background: rgba(5,11,22,0.85); color: #AAC0E1;"
            " border: 2px solid #2A5A9E; border-radius: 8px; font-size: 11px; }"
        )
        self.camera_feed.setText("Camera")

        root.addWidget(
            self.camera_feed,
            0,
            0,
            Qt.AlignBottom | Qt.AlignRight
        )

    def set_camera_frame(self, pixmap):
        """Update the small fullscreen camera feed."""

        if hasattr(self, "camera_feed"):

            self.camera_feed.setPixmap(
                pixmap.scaled(
                    self.camera_feed.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )

    def _toggle_tools(self):
        self.tools.setVisible(not self.tools.isVisible())

    def _build_tools(self):
        bar = QFrame()
        bar.setStyleSheet(
            "QFrame { background: rgba(10,22,40,0.94);"
            " border: 1px solid #2A5A9E; border-radius: 10px; }"
            "QLabel { color: #AAC0E1; font-size: 12px; }"
            "QPushButton { background: transparent; color: #EAF2FF;"
            " border: none; padding: 6px 10px; border-radius: 6px;"
            " font-size: 13px; }"
            "QPushButton:hover { background: #1B3A63; }"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(6)

        for name, tool in (
            ("Pen", "pen"),
            ("Highlighter", "highlighter"),
            ("Eraser", "eraser"),
        ):
            button = QPushButton(name)
            button.clicked.connect(
                lambda checked=False, t=tool:
                setattr(self.slide_view, "tool", t)
            )
            layout.addWidget(button)

        layout.addWidget(QLabel("Colour:"))
        for color in ("#E81123", "#FFB020", "#28C76F", "#2876E8", "#FFFFFF"):
            swatch = QPushButton()
            swatch.setFixedSize(20, 20)
            swatch.setStyleSheet(
                "QPushButton { background: " + color + ";"
                " border: 2px solid #FFFFFF; border-radius: 10px; }"
            )
            swatch.clicked.connect(
                lambda checked=False, c=color:
                setattr(self.slide_view, "color", QColor(c))
            )
            layout.addWidget(swatch)

        layout.addWidget(QLabel("Size:"))
        slider = QSlider(Qt.Horizontal)
        slider.setRange(1, 20)
        slider.setValue(4)
        slider.setFixedWidth(90)
        slider.valueChanged.connect(
            lambda v: setattr(self.slide_view, "brush_size", v)
        )
        layout.addWidget(slider)

        undo_btn = QPushButton("Undo")
        redo_btn = QPushButton("Redo")
        clear_btn = QPushButton("Clear")
        undo_btn.clicked.connect(self.slide_view.undo)
        redo_btn.clicked.connect(self.slide_view.redo)
        clear_btn.clicked.connect(self.slide_view.clear_annotations)
        layout.addWidget(undo_btn)
        layout.addWidget(redo_btn)
        layout.addWidget(clear_btn)

        return bar

    def set_slide(self, image, page_number, total_pages):
        """Display a slide image fullscreen (clears annotations)."""

        pixmap = (
            QPixmap.fromImage(image)
            if isinstance(image, QImage)
            else image
        )

        self.slide_view.set_slide(pixmap)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Escape, Qt.Key_Q):
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        if self.page is not None:
            self.page.fullscreen_window = None
        super().closeEvent(event)
