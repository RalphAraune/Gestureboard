"""GestureBoard Camera Setup and Live Hand Tracking Page."""

import cv2
import numpy as np

# ============================================================
# MEDIAPIPE
# ============================================================

try:
    import mediapipe as mp
except Exception as error:
    print("MediaPipe import error:", error)
    mp = None

# ============================================================
# PYQT5
# ============================================================

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# ============================================================
# OPTIONAL CAMERA ENUMERATION
# ============================================================

try:
    from cv2_enumerate_cameras import enumerate_cameras
except ImportError:
    enumerate_cameras = None


# ============================================================
# CAMERA DETECTION
# ============================================================

def find_named_cameras():
    """
    Detect available cameras.

    Returns:
        [
            (camera_index, camera_name),
            ...
        ]
    """

    if cv2 is None:
        return []

    cameras = []

    backend = (
        cv2.CAP_DSHOW
        if hasattr(cv2, "CAP_DSHOW")
        else cv2.CAP_ANY
    )

    # --------------------------------------------------------
    # Try cv2-enumerate-cameras first
    # --------------------------------------------------------

    if enumerate_cameras is not None:
        try:
            devices = enumerate_cameras(backend)

            for device in devices:
                try:
                    index = int(device.index)
                    name = str(device.name)

                    cameras.append((index, name))

                except Exception:
                    pass

            if cameras:
                return cameras

        except Exception as error:
            print("Camera enumeration warning:", error)

    # --------------------------------------------------------
    # OpenCV fallback
    # --------------------------------------------------------

    for index in range(10):

        camera = None

        try:
            camera = cv2.VideoCapture(
                index,
                backend
            )

            if camera.isOpened():

                cameras.append(
                    (
                        index,
                        f"Camera {index}"
                    )
                )

        except Exception as error:

            print(
                f"Camera {index} detection error:",
                error
            )

        finally:

            if camera is not None:

                try:
                    camera.release()
                except Exception:
                    pass

    return cameras


# ============================================================
# STATUS TEXT
#
# The page updates its status labels with inline styles that use
# tiny 10-11 px fonts. This label keeps only the colour from those
# styles and applies one readable size, so every status line looks
# consistent without touching each update.
# ============================================================

import re as _re


class StatusText(QLabel):

    _COLOR = _re.compile(r"color\s*:\s*([^;]+);")

    def __init__(self, text="", size=13, parent=None):
        super().__init__(text, parent)
        self._size = size

    def setStyleSheet(self, style):
        match = self._COLOR.search(style or "")
        color = match.group(1).strip() if match else "#5A6B93"
        super().setStyleSheet(
            f"color: {color}; font-size: {self._size}px; font-weight: 600;"
        )


class PreviewLabel(QLabel):
    """Camera preview area.

    While there is no feed it shows a camera icon above the message,
    centred together. Once frames arrive it shows the video instead.
    """

    def setText(self, text):

        if not text:
            super().setText("")
            return

        import html

        body = html.escape(text).replace("\n", "<br>")

        super().setText(
            '<div style="font-family: \'Segoe UI Emoji\'; font-size: 46px;">📷</div>'
            f'<div style="font-size: 14px;">{body}</div>'
        )


class _HiddenLabel(QLabel):
    """Stand-in for the old separate camera icon (now part of PreviewLabel)."""

    def show(self):
        pass

    def setVisible(self, visible):
        super().setVisible(False)


# ============================================================
# CAMERA SETUP PAGE
# ============================================================

class CameraSetupPage(QWidget):
    """
    GestureBoard Camera Setup.

    Features:
    - Camera selection
    - Resolution selection
    - Mirrored live camera preview
    - Automatic MediaPipe hand detection
    - Hand landmark dots
    - Hand connection lines
    - Camera status
    - Hand detection status
    - Continue button

    IMPORTANT:
    There is NO Start Tracking button.

    MediaPipe automatically starts processing when
    Test Camera is clicked.
    """

    def __init__(self, parent=None):

        super().__init__(parent)

        self.parent_window = parent

        # ====================================================
        # CAMERA
        # ====================================================

        self.capture = None
        self.camera_index = None

        # Camera has been successfully tested
        self.camera_tested = False

        # ====================================================
        # MEDIAPIPE
        # ====================================================

        self.mp_hands = None
        self.mp_draw = None
        self.mp_drawing_styles = None
        self.hands = None

        self.initialize_mediapipe()

        # ====================================================
        # TIMER
        # ====================================================

        self.timer = QTimer(self)

        self.timer.timeout.connect(
            self.update_preview
        )

        # ====================================================
        # UI
        # ====================================================

        self.build_ui()

        from widgets import page_background

        page_background.clear_layers(self)

        # ====================================================
        # CAMERA DETECTION
        # ====================================================

        self.refresh_cameras()


    # ========================================================
    # MEDIAPIPE INITIALIZATION
    # ========================================================

    def initialize_mediapipe(self):

        if mp is None:

            print(
                "MediaPipe is not available."
            )

            return

        try:

            self.mp_hands = mp.solutions.hands

            self.mp_draw = (
                mp.solutions.drawing_utils
            )

            self.mp_drawing_styles = (
                mp.solutions.drawing_styles
            )

            # ------------------------------------------------
            # Create MediaPipe Hands
            # ------------------------------------------------

            self.hands = self.mp_hands.Hands(

                static_image_mode=False,

                max_num_hands=2,

                model_complexity=1,

                min_detection_confidence=0.4,

                min_tracking_confidence=0.4
            )

            print(
                "MediaPipe Hands initialized successfully."
            )

        except Exception as error:

            print(
                "MediaPipe initialization error:",
                error
            )

            self.mp_hands = None
            self.mp_draw = None
            self.mp_drawing_styles = None
            self.hands = None


    # ========================================================
    # BACKGROUND
    # ========================================================

    def paintEvent(self, event):

        from widgets import page_background

        page_background.paint_page_background(self, self._page_colors)

    # ========================================================
    # BUILD UI
    # ========================================================

    def build_ui(self):

        from widgets import page_background

        c = self._page_colors = page_background.page_colors()

        self.setObjectName(
            "cameraSetup"
        )

        self.setStyleSheet(
            page_background.LAYER_RULE + f"""
            QWidget#cameraSetup {{
                background: transparent;
            }}

            QLabel {{
                background: transparent;
                color: {c['text']};
            }}

            QLabel#heading {{
                font-size: 28px;
                font-weight: 800;
                color: {c['text']};
            }}

            QLabel#subtitle {{
                color: {c['text_secondary']};
                font-size: 14px;
            }}

            QLabel#muted {{
                color: {c['text_secondary']};
                font-size: 14px;
            }}

            QLabel#panelTitle {{
                color: {c['text']};
                font-size: 16px;
                font-weight: 700;
            }}

            QLabel#fieldLabel {{
                color: {c['text']};
                font-size: 13px;
                font-weight: 600;
            }}

            QFrame#preview, QFrame#controlsPanel {{
                background: {c['card']};
                border: 1px solid {c['border']};
                border-radius: 16px;
            }}

            QFrame#cameraPlaceholder {{
                background: {c['bg']};
                border: 2px dashed {c['border']};
                border-radius: 12px;
            }}

            QFrame#status {{
                background: {c['bg']};
                border: 1px solid {c['border']};
                border-radius: 10px;
            }}

            QComboBox {{
                background: {c['input_bg']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 9px;
                padding: 8px 12px;
                font-size: 13px;
            }}

            QComboBox:hover {{
                border: 1px solid {c['primary']};
            }}

            QComboBox QAbstractItemView {{
                background: {c['input_bg']};
                color: {c['text']};
                selection-background-color: {c['button_hover']};
                selection-color: {c['text']};
            }}

            QPushButton {{
                background: {c['bg']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 9px;
                padding: 9px;
                font-size: 14px;
                font-weight: 600;
            }}

            QPushButton:hover {{
                background: {c['button_hover']};
                color: {c['text']};
            }}

            QPushButton#continue {{
                background: {c['primary']};
                color: {c['primary_text']};
                border: none;
                border-radius: 9px;
                font-weight: 700;
            }}

            QPushButton#continue:hover {{
                background: {c['sidebar_hover']};
            }}

            QPushButton#continue:disabled {{
                background: {c['border']};
                color: {c['bg']};
            }}

            QLabel#live {{
                background: #E5484D;
                color: #FFF4F4;
                border-radius: 10px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 700;
            }}
            """
        )

        # ====================================================
        # MAIN LAYOUT
        # ====================================================

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            36,
            28,
            36,
            28
        )

        layout.setSpacing(6)

        # ====================================================
        # HEADER
        # ====================================================

        title = QLabel(
            "Camera setup"
        )

        title.setObjectName(
            "heading"
        )

        subtitle = QLabel(
            "Choose a camera and test it. Hand tracking starts as soon as the feed appears."
        )

        subtitle.setObjectName(
            "subtitle"
        )

        subtitle.setWordWrap(True)

        layout.addWidget(title)

        layout.addWidget(subtitle)

        layout.addSpacing(18)

        # ====================================================
        # CONTENT
        # ====================================================

        content = QHBoxLayout()

        content.setSpacing(20)

        # ====================================================
        # PREVIEW PANEL
        # ====================================================

        preview_box = QFrame()

        preview_box.setObjectName(
            "preview"
        )

        preview_box.setMinimumSize(
            320,
            240
        )

        preview_box.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

        preview_layout = QVBoxLayout(
            preview_box
        )

        preview_layout.setContentsMargins(
            22,
            18,
            22,
            18
        )

        preview_layout.setSpacing(12)

        preview_header = QHBoxLayout()

        preview_title = QLabel("Live preview")
        preview_title.setObjectName("panelTitle")

        live = QLabel(
            "● Live"
        )

        live.setObjectName(
            "live"
        )

        preview_header.addWidget(preview_title)
        preview_header.addStretch()
        preview_header.addWidget(live)

        preview_layout.addLayout(preview_header)

        # ====================================================
        # CAMERA PLACEHOLDER
        # ====================================================

        self.camera_placeholder = QFrame()

        self.camera_placeholder.setObjectName(
            "cameraPlaceholder"
        )

        self.camera_placeholder.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

        placeholder_layout = QVBoxLayout(
            self.camera_placeholder
        )

        placeholder_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        placeholder_layout.setAlignment(
            Qt.AlignCenter
        )

        # The icon is drawn by PreviewLabel together with its message.
        self.cam_icon = _HiddenLabel(self.camera_placeholder)
        self.cam_icon.setVisible(False)

        self.preview_label = PreviewLabel()

        self.preview_label.setTextFormat(Qt.RichText)

        self.preview_label.setText(
            "Awaiting Camera Feed…\n\n"
            "Select a camera, then click Test Camera."
        )

        self.preview_label.setObjectName(
            "muted"
        )

        self.preview_label.setAlignment(
            Qt.AlignCenter
        )

        self.preview_label.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

        self.preview_label.setMinimumSize(
            280,
            200
        )

        placeholder_layout.addWidget(
            self.preview_label,
            1
        )

        preview_layout.addWidget(
            self.camera_placeholder,
            1
        )

        # ====================================================
        # TRACKING STATUS
        # ====================================================

        self.tracking_status = StatusText(
            "● Not Tracking",
            size=13
        )

        self.tracking_status.setStyleSheet(
            "color: #8A94A6;"
        )

        preview_layout.addWidget(
            self.tracking_status
        )

        # ====================================================
        # CONTROLS PANEL
        # ====================================================

        controls_panel = QFrame()

        controls_panel.setObjectName("controlsPanel")

        controls_panel.setFixedWidth(360)

        controls = QVBoxLayout(controls_panel)

        controls.setSpacing(8)

        controls.setContentsMargins(
            22,
            18,
            22,
            22
        )

        panel_title = QLabel("Settings")
        panel_title.setObjectName("panelTitle")
        controls.addWidget(panel_title)

        controls.addSpacing(6)

        # ----------------------------------------------------
        # Camera
        # ----------------------------------------------------

        controls.addWidget(
            self._caption("Camera")
        )

        camera_row = QHBoxLayout()

        camera_row.setSpacing(8)

        self.camera_combo = QComboBox()

        self.camera_combo.setMinimumWidth(
            200
        )

        self.camera_combo.setFixedHeight(
            42
        )

        self.camera_combo.currentIndexChanged.connect(
            self.camera_changed
        )

        camera_row.addWidget(
            self.camera_combo,
            1
        )

        self.refresh_button = QPushButton(
            "⟳"
        )

        self.refresh_button.setToolTip(
            "Refresh and detect cameras"
        )

        self.refresh_button.setFixedSize(
            42,
            42
        )

        self.refresh_button.setCursor(Qt.PointingHandCursor)

        self.refresh_button.clicked.connect(
            self.refresh_cameras
        )

        camera_row.addWidget(
            self.refresh_button
        )

        controls.addLayout(
            camera_row
        )

        # ----------------------------------------------------
        # Resolution
        # ----------------------------------------------------

        controls.addSpacing(8)

        controls.addWidget(
            self._caption("Resolution")
        )

        self.resolution_combo = QComboBox()

        self.resolution_combo.setFixedHeight(
            42
        )

        self.resolution_combo.addItems(
            [
                "1280 × 720",
                "1920 × 1080",
                "640 × 480"
            ]
        )

        controls.addWidget(
            self.resolution_combo
        )

        # ----------------------------------------------------
        # System check
        # ----------------------------------------------------

        controls.addSpacing(12)

        controls.addWidget(
            self._caption("System check")
        )

        status = QFrame()

        status.setObjectName(
            "status"
        )

        status_layout = QVBoxLayout(
            status
        )

        status_layout.setContentsMargins(
            14,
            12,
            14,
            12
        )

        status_layout.setSpacing(
            9
        )

        self.status_items = {
            "camera": StatusText("● Camera Not Tested"),
            "opencv": StatusText("● OpenCV Loaded"),
            "mediapipe": StatusText("● MediaPipe Ready"),
            "hand": StatusText("● Hand Model Ready"),
        }

        for key in [
            "camera",
            "opencv",
            "mediapipe",
            "hand"
        ]:

            item = self.status_items[key]

            item.setStyleSheet(
                "color: #2F9E62;"
            )

            status_layout.addWidget(
                item
            )

        # ----------------------------------------------------
        # MediaPipe unavailable
        # ----------------------------------------------------

        if self.hands is None:

            self.status_items["mediapipe"].setText(
                "● MediaPipe Not Ready"
            )

            self.status_items["mediapipe"].setStyleSheet(
                "color: #E04D5A;"
            )

            self.status_items["hand"].setText(
                "● Hand Model Not Ready"
            )

            self.status_items["hand"].setStyleSheet(
                "color: #E04D5A;"
            )

        controls.addWidget(
            status
        )

        controls.addStretch()

        # ----------------------------------------------------
        # Actions
        # ----------------------------------------------------

        self.test_button = QPushButton(
            "Test camera"
        )

        self.test_button.setFixedHeight(
            44
        )

        self.test_button.setCursor(Qt.PointingHandCursor)

        self.test_button.clicked.connect(
            self.start_preview
        )

        controls.addWidget(
            self.test_button
        )

        self.continue_button = QPushButton(
            "Continue"
        )

        self.continue_button.setObjectName(
            "continue"
        )

        self.continue_button.setFixedHeight(
            46
        )

        self.continue_button.setCursor(Qt.PointingHandCursor)

        # Disabled until camera test succeeds
        self.continue_button.setEnabled(
            False
        )

        self.continue_button.clicked.connect(
            self.continue_to_dashboard
        )

        controls.addWidget(
            self.continue_button
        )

        # ====================================================
        # ADD CONTENT
        # ====================================================

        content.addWidget(
            preview_box,
            1
        )

        content.addWidget(
            controls_panel
        )

        layout.addLayout(
            content,
            1
        )


    # ========================================================
    # CAPTION
    # ========================================================

    @staticmethod
    def _caption(text):

        label = QLabel(
            text
        )

        label.setObjectName(
            "fieldLabel"
        )

        return label


    # ========================================================
    # REFRESH CAMERAS
    # ========================================================

    def refresh_cameras(self):

        self.stop_preview()

        self.camera_tested = False

        self.continue_button.setEnabled(
            False
        )

        self.camera_combo.blockSignals(
            True
        )

        self.camera_combo.clear()

        cameras = find_named_cameras()

        if not cameras:

            self.camera_combo.addItem(
                "No camera detected",
                None
            )

            self.preview_label.setText(
                "No camera detected.\n\n"
                "Connect a webcam or start Iriun Webcam, "
                "then click Refresh."
            )

            self.status_items[
                "camera"
            ].setText(
                "● Camera Not Found"
            )

            self.status_items[
                "camera"
            ].setStyleSheet(
                """
                color: #E04D5A;
                font-size: 11px;
                font-weight: 600;
                """
            )

        else:

            for index, name in cameras:

                self.camera_combo.addItem(
                    name,
                    index
                )

            self.status_items[
                "camera"
            ].setText(
                "● Camera Found"
            )

            self.status_items[
                "camera"
            ].setStyleSheet(
                """
                color: #2F9E62;
                font-size: 11px;
                font-weight: 600;
                """
            )

            self.preview_label.setText(
                "Camera detected.\n\n"
                "Click Test Camera to show the live feed."
            )

        # Keep the app-wide active camera selected.
        if self.camera_index is not None:

            found = self.camera_combo.findData(
                self.camera_index
            )

            if found >= 0:

                self.camera_combo.setCurrentIndex(
                    found
                )

        self.camera_combo.blockSignals(
            False
        )


    # ========================================================
    # ACTIVE CAMERA (set by MainWindow)
    # ========================================================

    def setActiveCamera(self, index, name):

        self.camera_index = index

        found = self.camera_combo.findData(index)

        if found >= 0 and found != self.camera_combo.currentIndex():

            self.camera_combo.blockSignals(True)

            self.camera_combo.setCurrentIndex(found)

            self.camera_combo.blockSignals(False)


    # ========================================================
    # PLACEHOLDER TEXT
    # ========================================================

    def _placeholder_text(self):

        index = self.camera_combo.currentData()

        if index is None:

            return (
                "No camera detected.\n\n"
                "Connect a webcam or start Iriun Webcam, "
                "then click Refresh."
            )

        return (
            "Awaiting Camera Feed…\n\n"
            "Select a camera, then click Test Camera."
        )


    # ========================================================
    # CAMERA CHANGED
    # ========================================================

    def camera_changed(self):

        self.stop_preview()

        self.camera_tested = False

        self.continue_button.setEnabled(
            False
        )

        index = self.camera_combo.currentData()

        if index is not None:

            self.preview_label.setText(
                "Camera selected.\n\n"
                "Click Test Camera to show the live feed."
            )

            self.status_items[
                "camera"
            ].setText(
                "● Camera Selected"
            )

            self.status_items[
                "camera"
            ].setStyleSheet(
                """
                color: #E8A33D;
                font-size: 11px;
                font-weight: 600;
                """
            )


    # ========================================================
    # START PREVIEW
    # ========================================================

    def start_preview(self):

        index = self.camera_combo.currentData()

        if index is None:

            self.preview_label.setText(
                "Please select a camera first."
            )

            return

        self.stop_preview()

        # ----------------------------------------------------
        # Get resolution
        # ----------------------------------------------------

        resolution = (
            self.resolution_combo
            .currentText()
            .replace(" ", "")
        )

        try:

            width, height = map(
                int,
                resolution.split("×")
            )

        except Exception:

            width = 1280
            height = 720

        # ----------------------------------------------------
        # Windows camera backend
        # ----------------------------------------------------

        backend = (
            cv2.CAP_DSHOW
            if hasattr(cv2, "CAP_DSHOW")
            else cv2.CAP_ANY
        )

        self.capture = cv2.VideoCapture(
            index,
            backend
        )

        # ----------------------------------------------------
        # Camera settings
        # ----------------------------------------------------

        self.capture.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            width
        )

        self.capture.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            height
        )

        self.capture.set(
            cv2.CAP_PROP_FPS,
            30
        )

        # ----------------------------------------------------
        # Check camera
        # ----------------------------------------------------

        if not self.capture.isOpened():

            self.preview_label.setText(
                "Unable to open this camera.\n\n"
                "Close other apps using the camera "
                "and try again."
            )

            self.status_items[
                "camera"
            ].setText(
                "● Camera Failed"
            )

            self.status_items[
                "camera"
            ].setStyleSheet(
                """
                color: #E04D5A;
                font-size: 11px;
                font-weight: 600;
                """
            )

            self.stop_preview()

            return

        # ----------------------------------------------------
        # Read first frame
        # ----------------------------------------------------

        ok, frame = self.capture.read()

        if not ok or frame is None:

            self.preview_label.setText(
                "Camera opened but no video frame was received."
            )

            self.stop_preview()

            return

        # ----------------------------------------------------
        # Camera successfully tested
        # ----------------------------------------------------

        self.camera_tested = True

        # ----------------------------------------------------
        # Hide placeholder
        # ----------------------------------------------------

        self.cam_icon.hide()

        self.preview_label.setText(
            ""
        )

        # ----------------------------------------------------
        # Update status
        # ----------------------------------------------------

        self.status_items[
            "camera"
        ].setText(
            "● Camera Active"
        )

        self.status_items[
            "camera"
        ].setStyleSheet(
            """
            color: #2F9E62;
            font-size: 11px;
            font-weight: 600;
            """
        )

        # ====================================================
        # IMPORTANT
        # ====================================================
        #
        # Continue is enabled immediately after
        # successful camera testing.
        #
        # No Start Tracking button is required.
        #

        self.continue_button.setEnabled(
            True
        )

        # ----------------------------------------------------
        # Start automatic hand detection
        # ----------------------------------------------------

        self.tracking_status.setText(
            "● Camera Ready — Detecting hands automatically"
        )

        self.tracking_status.setStyleSheet(
            """
            color: #2F9E62;
            font-size: 10px;
            font-weight: 700;
            margin: 6px 0 0 0;
            """
        )

        # ----------------------------------------------------
        # Start preview timer
        # ----------------------------------------------------

        self.timer.start(
            30
        )


    # ========================================================
    # UPDATE PREVIEW
    # ========================================================

    def update_preview(self):

        if self.capture is None:
            return

        if not self.capture.isOpened():

            self.stop_preview()

            return

        # ----------------------------------------------------
        # Read frame
        # ----------------------------------------------------

        ok, frame = self.capture.read()

        if not ok or frame is None:

            self.preview_label.setText(
                "Camera feed was interrupted."
            )

            self.stop_preview()

            return

        # ====================================================
        # MIRROR CAMERA
        # ====================================================
        #
        # 1 = horizontal flip
        #
        # This makes the camera behave like a selfie camera.
        #

        frame = cv2.flip(
            frame,
            1
        )

        frame = np.ascontiguousarray(
            frame
        )

        hand_detected = False

        # ====================================================
        # MEDIAPIPE HAND DETECTION
        # ====================================================

        if (
            self.hands is not None
            and self.mp_hands is not None
            and self.mp_draw is not None
        ):

            try:

                # ------------------------------------------------
                # BGR → RGB
                # ------------------------------------------------

                rgb_frame = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGR2RGB
                )

                # ------------------------------------------------
                # MediaPipe doesn't need to modify the image
                # ------------------------------------------------

                rgb_frame.flags.writeable = False

                # ------------------------------------------------
                # PROCESS FRAME
                # ------------------------------------------------

                results = self.hands.process(
                    rgb_frame
                )

                rgb_frame.flags.writeable = True

                # ------------------------------------------------
                # HAND FOUND
                # ------------------------------------------------

                if (
                    results is not None
                    and results.multi_hand_landmarks
                ):

                    hand_detected = True

                    # ============================================
                    # DRAW EVERY DETECTED HAND
                    # ============================================

                    for hand_landmarks in (
                        results.multi_hand_landmarks
                    ):

                        # ------------------------------------------------
                        # Draw landmark lines and dots
                        # ------------------------------------------------

                        if self.mp_drawing_styles is not None:

                            self.mp_draw.draw_landmarks(

                                frame,

                                hand_landmarks,

                                self.mp_hands.HAND_CONNECTIONS,

                                self.mp_drawing_styles
                                .get_default_hand_landmarks_style(),

                                self.mp_drawing_styles
                                .get_default_hand_connections_style()
                            )

                        else:

                            self.mp_draw.draw_landmarks(

                                frame,

                                hand_landmarks,

                                self.mp_hands.HAND_CONNECTIONS
                            )

            except Exception as error:

                print(
                    "MediaPipe preview error:",
                    error
                )

        # ====================================================
        # UPDATE TRACKING STATUS
        # ====================================================

        if hand_detected:

            self.tracking_status.setText(
                "● Hand Detected — Tracking"
            )

            self.tracking_status.setStyleSheet(
                """
                color: #2F9E62;
                font-size: 10px;
                font-weight: 700;
                margin: 6px 0 0 0;
                """
            )

        else:

            self.tracking_status.setText(
                "● Camera Active — Show your hand"
            )

            self.tracking_status.setStyleSheet(
                """
                color: #E8A33D;
                font-size: 10px;
                font-weight: 700;
                margin: 6px 0 0 0;
                """
            )

        # ====================================================
        # BGR → RGB FOR QT
        # ====================================================

        frame_rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        height, width, channels = (
            frame_rgb.shape
        )

        bytes_per_line = (
            channels * width
        )

        # ====================================================
        # CREATE QIMAGE
        # ====================================================

        image = QImage(

            frame_rgb.data,

            width,

            height,

            bytes_per_line,

            QImage.Format_RGB888
        )

        # ----------------------------------------------------
        # Copy image so Qt owns the data
        # ----------------------------------------------------

        image = image.copy()

        # ====================================================
        # SCALE PREVIEW
        # ====================================================

        target = self.preview_label.size()

        if (
            target.width() < 40
            or target.height() < 40
        ):

            target = (
                self.camera_placeholder.size()
            )

        pixmap = QPixmap.fromImage(
            image
        )

        pixmap = pixmap.scaled(

            target,

            Qt.KeepAspectRatio,

            Qt.SmoothTransformation
        )

        self.preview_label.setPixmap(
            pixmap
        )


    # ========================================================
    # COMPATIBILITY METHOD
    # ========================================================
    #
    # Other parts of the application may still call
    # start_tracking().
    #
    # We keep the method so old code won't crash.
    #
    # However, tracking is already automatic.
    #

    def start_tracking(self):

        if self.capture is None:
            return

        if not self.capture.isOpened():
            return

        camera_index = (
            self.camera_combo.currentData()
        )

        camera_name = (
            self.camera_combo.currentText()
        )

        # ----------------------------------------------------
        # Inform MainWindow if supported
        # ----------------------------------------------------

        if self.parent_window is not None:

            if hasattr(
                self.parent_window,
                "setActiveCamera"
            ):

                try:

                    self.parent_window.setActiveCamera(
                        camera_index,
                        camera_name
                    )

                except Exception as error:

                    print(
                        "setActiveCamera error:",
                        error
                    )

        # ----------------------------------------------------
        # Continue is already allowed
        # ----------------------------------------------------

        self.camera_tested = True

        self.continue_button.setEnabled(
            True
        )


    # ========================================================
    # STOP PREVIEW
    # ========================================================

    def stop_preview(self):

        try:

            self.timer.stop()

        except Exception:
            pass

        # ----------------------------------------------------
        # Release camera
        # ----------------------------------------------------

        if self.capture is not None:

            try:

                self.capture.release()

            except Exception:
                pass

            self.capture = None

        # ----------------------------------------------------
        # Restore placeholder
        # ----------------------------------------------------

        if hasattr(
            self,
            "cam_icon"
        ):

            self.cam_icon.show()

        if hasattr(
            self,
            "preview_label"
        ):

            self.preview_label.setPixmap(
                QPixmap()
            )

            self.preview_label.setText(
                self._placeholder_text()
            )

        # ----------------------------------------------------
        # Tracking status
        # ----------------------------------------------------

        if hasattr(
            self,
            "tracking_status"
        ):

            self.tracking_status.setText(
                "● Not Tracking"
            )

            self.tracking_status.setStyleSheet(
                """
                color: #8A94A6;
                font-size: 10px;
                font-weight: 700;
                margin: 6px 0 0 0;
                """
            )


    # ========================================================
    # CONTINUE TO DASHBOARD
    # ========================================================

    def continue_to_dashboard(self):

        # ----------------------------------------------------
        # Make sure camera was tested
        # ----------------------------------------------------

        if not self.camera_tested:

            return

        # ----------------------------------------------------
        # Save camera information
        # ----------------------------------------------------

        camera_index = (
            self.camera_combo.currentData()
        )

        camera_name = (
            self.camera_combo.currentText()
        )

        if self.parent_window is not None:

            if hasattr(
                self.parent_window,
                "setActiveCamera"
            ):

                try:

                    self.parent_window.setActiveCamera(
                        camera_index,
                        camera_name
                    )

                except Exception as error:

                    print(
                        "setActiveCamera error:",
                        error
                    )

        # ----------------------------------------------------
        # Stop preview
        # ----------------------------------------------------

        self.stop_preview()

        # ----------------------------------------------------
        # Save tutorial preference
        # ----------------------------------------------------

        try:

            import settings.preferences as prefs

            if hasattr(
                prefs,
                "set_tutorial_completed"
            ):

                prefs.set_tutorial_completed(
                    True
                )

        except Exception as error:

            print(
                "Preference save error:",
                error
            )

        # ====================================================
        # GO TO DASHBOARD
        # ====================================================

        if self.parent_window is not None:

            # ------------------------------------------------
            # Preferred method
            # ------------------------------------------------

            if hasattr(
                self.parent_window,
                "showDashboard"
            ):

                try:

                    self.parent_window.showDashboard()

                    return

                except Exception as error:

                    print(
                        "showDashboard error:",
                        error
                    )

            # ------------------------------------------------
            # Fallback
            # ------------------------------------------------

            if hasattr(
                self.parent_window,
                "dashboard"
            ):

                try:

                    self.parent_window.stack.setCurrentWidget(
                        self.parent_window.dashboard
                    )

                except Exception as error:

                    print(
                        "Dashboard fallback error:",
                        error
                    )


    # ========================================================
    # HIDE EVENT
    # ========================================================

    def hideEvent(self, event):

        self.stop_preview()

        super().hideEvent(
            event
        )


    # ========================================================
    # CLOSE EVENT
    # ========================================================

    def closeEvent(self, event):

        self.stop_preview()

        # ----------------------------------------------------
        # Close MediaPipe
        # ----------------------------------------------------

        if self.hands is not None:

            try:

                self.hands.close()

            except Exception:
                pass

            self.hands = None

        event.accept()


# ============================================================
# CAMERA PICKER DIALOG
# ============================================================

class CameraPickerDialog(QDialog):
    """
    Simple camera selection dialog.

    Kept for compatibility with the rest of GestureBoard.
    """

    def __init__(self, parent=None):

        super().__init__(
            parent
        )

        self.setWindowTitle(
            "Select Camera"
        )

        self.setMinimumSize(
            400,
            300
        )

        self.setStyleSheet(
            """
            QWidget {
                background: #F2F8FC;
            }

            QLabel {
                background: transparent;
                color: #0E2F76;
            }

            QLabel#heading {
                font-size: 20px;
                font-weight: 800;
            }

            QLabel#muted {
                color: #5A6B93;
                font-size: 12px;
            }

            QComboBox {
                background: #EAF3FA;
                color: #0E2F76;
                border: 1px solid #AAC0E1;
                border-radius: 7px;
                padding: 8px;
                min-width: 200px;
            }

            QComboBox QAbstractItemView {
                background: #EAF3FA;
                color: #0E2F76;
                selection-background-color: #AAC0E1;
            }

            QPushButton {
                background: #EAF3FA;
                color: #5A6B93;
                border: 1px solid #AAC0E1;
                border-radius: 7px;
                padding: 9px;
                min-width: 100px;
            }

            QPushButton:hover {
                background: #EFF4FC;
                color: #0E2F76;
            }

            QPushButton#accept {
                background: #0E2F76;
                color: #F5FEFF;
                border: none;
                border-radius: 7px;
                padding: 9px;
                font-weight: 700;
            }

            QPushButton#accept:hover {
                background: #1B4499;
            }

            QPushButton#cancel {
                background: #EAF3FA;
                color: #5A6B93;
                border: 1px solid #AAC0E1;
                border-radius: 7px;
                padding: 9px;
                min-width: 100px;
            }
            """
        )

        # ====================================================
        # LAYOUT
        # ====================================================

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            20,
            20,
            20,
            20
        )

        layout.setSpacing(
            12
        )

        # ====================================================
        # TITLE
        # ====================================================

        title = QLabel(
            "Select Camera"
        )

        title.setObjectName(
            "heading"
        )

        title.setAlignment(
            Qt.AlignCenter
        )

        layout.addWidget(
            title
        )

        # ====================================================
        # SUBTITLE
        # ====================================================

        subtitle = QLabel(
            "Choose a camera to use with GestureBoard"
        )

        subtitle.setObjectName(
            "muted"
        )

        subtitle.setAlignment(
            Qt.AlignCenter
        )

        layout.addWidget(
            subtitle
        )

        # ====================================================
        # CAMERA COMBO
        # ====================================================

        self.camera_combo = QComboBox()

        layout.addWidget(
            self.camera_combo
        )

        # ====================================================
        # BUTTONS
        # ====================================================

        self.button_box = QDialogButtonBox(

            QDialogButtonBox.Ok
            |
            QDialogButtonBox.Cancel
        )

        self.button_box.setObjectName(
            "buttonBox"
        )

        self.button_box.button(
            QDialogButtonBox.Ok
        ).setObjectName(
            "accept"
        )

        self.button_box.button(
            QDialogButtonBox.Cancel
        ).setObjectName(
            "cancel"
        )

        self.button_box.accepted.connect(
            self.accepted
        )

        self.button_box.rejected.connect(
            self.reject
        )

        layout.addWidget(
            self.button_box
        )

        # ====================================================
        # SELECTED CAMERA
        # ====================================================

        self.selected_index = None

        self.selected_name = None

        # ====================================================
        # DETECT CAMERAS
        # ====================================================

        self.refresh_cameras()


    # ========================================================
    # REFRESH CAMERAS
    # ========================================================

    def refresh_cameras(self):

        self.camera_combo.clear()

        cameras = find_named_cameras()

        if not cameras:

            self.camera_combo.addItem(
                "No camera detected",
                None
            )

            return

        for index, name in cameras:

            self.camera_combo.addItem(
                name,
                index
            )


    # ========================================================
    # ACCEPT
    # ========================================================

    def accepted(self):

        index = (
            self.camera_combo.currentData()
        )

        name = (
            self.camera_combo.currentText()
        )

        self.selected_index = index

        self.selected_name = name

        super().accept()