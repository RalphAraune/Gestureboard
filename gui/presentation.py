# gui/presentation.py

import os
import sys

import cv2
import fitz

# MediaPipe may fail to load its DLL on some Python setups. Make it optional so
# the rest of the app still starts; feature code guards against mp being None.
try:
    import mediapipe as mp
except Exception:
    print("MediaPipe import error:", sys.exc_info()[1])
    mp = None

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
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
)

from core.gesture_detector import GestureDetector
from core.presentation_controller import PresentationController


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

        # ---------------------------------------------------------
        # CAMERA
        # ---------------------------------------------------------

        self.camera = None
        self.camera_index = 0

        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=1,
            min_detection_confidence=0.55,
            min_tracking_confidence=0.55,
        )

        self.gesture_detector = GestureDetector()
        self.presentation_controller = PresentationController()

        self.detected_gesture = "None"
        self.current_action = "Ready"

        # ---------------------------------------------------------
        # BUILD UI
        # ---------------------------------------------------------

        self.build_ui()

        # ---------------------------------------------------------
        # CAMERA TIMER
        # ---------------------------------------------------------

        self.camera_timer = QTimer(self)
        self.camera_timer.timeout.connect(self.update_camera)

        self.start_camera()

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
        # LEFT
        # ========================================================

        left_panel = QVBoxLayout()
        left_panel.setSpacing(12)

        # --------------------------------------------------------
        # PRESENTATION PREVIEW
        # --------------------------------------------------------

        preview_frame = QFrame()
        preview_frame.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #D9E4F5;
                border-radius: 12px;
            }
        """)

        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(20, 20, 20, 15)

        self.preview_label = QLabel()

        self.preview_label.setMinimumSize(700, 430)
        self.preview_label.setAlignment(Qt.AlignCenter)

        self.preview_label.setStyleSheet("""
            QLabel {
                background: #EAF1F8;
                border: 1px solid #C9D7E8;
                border-radius: 6px;
                color: #7890B5;
                font-size: 16px;
            }
        """)

        self.preview_label.setText(
            "Upload a PDF or PowerPoint file\n\n"
            "Your presentation preview will appear here."
        )

        preview_layout.addWidget(self.preview_label)

        # --------------------------------------------------------
        # SLIDE INFO
        # --------------------------------------------------------

        self.slide_counter = QLabel("Slide 0 / 0")

        self.slide_counter.setAlignment(Qt.AlignRight)

        self.slide_counter.setStyleSheet("""
            QLabel {
                background: #EAF1F8;
                color: #5574A8;
                padding: 6px 12px;
                border-radius: 15px;
                font-weight: 600;
            }
        """)

        preview_layout.addWidget(self.slide_counter)

        left_panel.addWidget(preview_frame)

        # --------------------------------------------------------
        # THUMBNAILS
        # --------------------------------------------------------

        self.thumbnail_scroll = QScrollArea()
        self.thumbnail_scroll.setFixedHeight(105)
        self.thumbnail_scroll.setWidgetResizable(True)
        self.thumbnail_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOn
        )
        self.thumbnail_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.thumbnail_container = QWidget()
        self.thumbnail_layout = QHBoxLayout(
            self.thumbnail_container
        )

        self.thumbnail_layout.setSpacing(10)
        self.thumbnail_layout.setContentsMargins(5, 5, 5, 5)

        self.thumbnail_scroll.setWidget(
            self.thumbnail_container
        )

        left_panel.addWidget(self.thumbnail_scroll)

        content_layout.addLayout(left_panel, 3)

        # ========================================================
        # RIGHT PANEL
        # ========================================================

        right_panel = QVBoxLayout()
        right_panel.setSpacing(15)

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
        gesture_layout.setContentsMargins(18, 18, 18, 18)
        gesture_layout.setSpacing(12)

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
            ("✊", "Fist", "Start Presentation"),
            ("✌️", "Peace Sign", "Next Slide"),
            ("🖖", "Three Fingers", "Previous Slide"),
            ("🤟", "Thumb + Pinky", "Full Screen"),
            ("✋", "Open Hand", "Exit Full Screen"),
            ("☝️", "Index Finger", "Cursor / Pointer"),
        ]

        for icon, gesture, action in gestures:

            row = QHBoxLayout()

            icon_label = QLabel(icon)
            icon_label.setFixedWidth(35)

            icon_label.setStyleSheet("""
                QLabel {
                    background: #E8F0FA;
                    border-radius: 8px;
                    padding: 8px;
                    font-size: 18px;
                }
            """)

            gesture_label = QLabel(gesture)

            gesture_label.setStyleSheet("""
                QLabel {
                    color: #5273A9;
                    font-weight: 600;
                }
            """)

            action_label = QLabel(action)

            action_label.setStyleSheet("""
                QLabel {
                    color: #7183A6;
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
        status_layout.setContentsMargins(18, 18, 18, 18)
        status_layout.setVerticalSpacing(10)

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

        self.camera_status = QLabel(
            "● Camera Connecting..."
        )

        self.camera_status.setStyleSheet("""
            QLabel {
                color: #5273A9;
                font-weight: 600;
            }
        """)

        camera_layout.addWidget(self.camera_status)

        self.detected_label = QLabel(
            "Detected: None"
        )

        self.detected_label.setStyleSheet("""
            QLabel {
                color: #12377D;
                font-weight: 600;
            }
        """)

        camera_layout.addWidget(self.detected_label)

        self.action_label = QLabel(
            "Action: Ready"
        )

        self.action_label.setStyleSheet("""
            QLabel {
                color: #7183A6;
            }
        """)

        camera_layout.addWidget(self.action_label)

        right_panel.addWidget(camera_frame)

        # --------------------------------------------------------
        # CONTROL BUTTONS
        # --------------------------------------------------------

        self.start_button = QPushButton("Start Presentation")
        self.start_button.setFixedHeight(42)
        self.start_button.clicked.connect(
            self.manual_start
        )

        self.next_button = QPushButton("Next Slide")
        self.next_button.setFixedHeight(42)
        self.next_button.clicked.connect(
            self.manual_next
        )

        self.previous_button = QPushButton("Previous Slide")
        self.previous_button.setFixedHeight(42)
        self.previous_button.clicked.connect(
            self.manual_previous
        )

        right_panel.addWidget(self.start_button)
        right_panel.addWidget(self.next_button)
        right_panel.addWidget(self.previous_button)

        right_panel.addStretch()

        content_layout.addLayout(right_panel, 1)

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

        elif extension in [".ppt", ".pptx"]:
            self.load_powerpoint(file_path)

        else:
            QMessageBox.warning(
                self,
                "Unsupported File",
                "Please select a PDF or PowerPoint file."
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
            self.create_pdf_thumbnails()

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

        self.total_pages = 0
        self.current_page = 0

        self.status_mode.setText(
            "PowerPoint"
        )

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

        self.preview_label.setText(
            "PowerPoint Presentation Loaded\n\n"
            + os.path.basename(file_path)
            + "\n\n"
            "Click Start Presentation or use ✊ Fist."
        )

        self.slide_counter.setText(
            "PowerPoint"
        )

        self.clear_thumbnails()

        self.update_status()

    # ============================================================
    # PDF RENDER
    # ============================================================

    def render_pdf_page(self):

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

        pixmap = pixmap.scaled(
            self.preview_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.preview_label.setPixmap(
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

    # ============================================================
    # PDF THUMBNAILS
    # ============================================================

    def clear_thumbnails(self):

        while self.thumbnail_layout.count():

            item = self.thumbnail_layout.takeAt(0)

            widget = item.widget()

            if widget:
                widget.deleteLater()

    def create_pdf_thumbnails(self):

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

        self.camera = cv2.VideoCapture(
            self.camera_index,
            cv2.CAP_DSHOW
        )

        if not self.camera.isOpened():

            self.camera = cv2.VideoCapture(
                self.camera_index
            )

        if self.camera.isOpened():

            self.camera.set(
                cv2.CAP_PROP_FRAME_WIDTH,
                1280
            )

            self.camera.set(
                cv2.CAP_PROP_FRAME_HEIGHT,
                720
            )

            self.camera_timer.start(30)

            self.camera_status.setText(
                "● Camera Connected"
            )

        else:

            self.camera_status.setText(
                "● Camera Not Available"
            )

    # ============================================================
    # UPDATE CAMERA
    # ============================================================

    def update_camera(self):

        if not self.camera:
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

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        rgb.flags.writeable = False

        results = self.hands.process(
            rgb
        )

        rgb.flags.writeable = True

        gesture = "None"

        # --------------------------------------------------------
        # DRAW LANDMARKS
        # --------------------------------------------------------

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
                gesture
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

    # ============================================================
    # GESTURE PROCESSING
    # ============================================================

    def process_gesture(self, gesture):

        if gesture in [
            "None",
            "Unknown"
        ]:
            return

        # --------------------------------------------------------
        # PREVENT SAME GESTURE FROM FIRING EVERY FRAME
        # --------------------------------------------------------

        if gesture == self.detected_gesture:

            # Don't repeatedly trigger.
            return

        self.detected_gesture = gesture

        # --------------------------------------------------------
        # EXECUTE
        # --------------------------------------------------------

        action_success = (
            self.presentation_controller
            .handle_gesture(
                gesture
            )
        )

        # --------------------------------------------------------
        # ACTION TEXT
        # --------------------------------------------------------

        actions = {
            "Fist":
                "Start Presentation",

            "Peace Sign":
                "Next Slide",

            "Three Fingers":
                "Previous Slide",

            "Thumb + Pinky":
                "Full Screen",

            "Open Hand":
                "Exit Full Screen",

            "Index Finger":
                "Cursor / Pointer",
        }

        action = actions.get(
            gesture,
            "Ready"
        )

        self.current_action = action

        self.action_label.setText(
            "Action: " + action
        )

        self.status_gesture.setText(
            "● Active — " + gesture
        )

        self.status_action.setText(
            action
        )

        self.presentationAction.emit(
            action
        )

        # --------------------------------------------------------
        # UPDATE PDF PREVIEW
        # --------------------------------------------------------

        if gesture == "Peace Sign":

            self.next_pdf_preview()

        elif gesture == "Three Fingers":

            self.previous_pdf_preview()

        self.update_status()

    # ============================================================
    # PDF NEXT
    # ============================================================

    def next_pdf_preview(self):

        if not self.pdf_document:
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

        if not self.pdf_document:
            return

        if self.current_page > 0:

            self.current_page -= 1

            self.render_pdf_page()

    # ============================================================
    # MANUAL CONTROLS
    # ============================================================

    def manual_start(self):

        self.presentation_controller.start_presentation()

        self.current_action = (
            "Presentation Started"
        )

        self.action_label.setText(
            "Action: Presentation Started"
        )

        self.update_status()

    def manual_next(self):

        self.presentation_controller.next_slide()

        self.next_pdf_preview()

        self.current_action = (
            "Next Slide"
        )

        self.action_label.setText(
            "Action: Next Slide"
        )

        self.update_status()

    def manual_previous(self):

        self.presentation_controller.previous_slide()

        self.previous_pdf_preview()

        self.current_action = (
            "Previous Slide"
        )

        self.action_label.setText(
            "Action: Previous Slide"
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

        event.accept()