"""GestureBoard Camera Setup and Live Hand Tracking Page."""

import cv2
import numpy as np

# MediaPipe may fail to load its DLL on some Python setups. Make the import
# optional so the rest of the app still starts; initialize_mediapipe() guards
# against mp being None.
try:
    import mediapipe as mp
except Exception:
    mp = None

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
# CAMERA DETECTION
# ============================================================

try:
    from cv2_enumerate_cameras import enumerate_cameras
except ImportError:
    enumerate_cameras = None


def find_named_cameras():
    """
    Detect available cameras.

    Returns:
        list[tuple[int, str]]
        Example:
            [(0, "Integrated Camera")]
    """

    cameras = []

    # --------------------------------------------------------
    # Method 1: cv2-enumerate-cameras
    # --------------------------------------------------------

    if enumerate_cameras is not None:

        try:

            backend = (
                cv2.CAP_DSHOW
                if hasattr(cv2, "CAP_DSHOW")
                else cv2.CAP_ANY
            )

            devices = enumerate_cameras(backend)

            for device in devices:

                try:
                    cameras.append(
                        (
                            int(device.index),
                            str(device.name)
                        )
                    )
                except Exception:
                    pass

            if cameras:
                return cameras

        except Exception as error:

            print(
                "Camera enumeration warning:",
                error
            )

    # --------------------------------------------------------
    # Method 2: OpenCV fallback
    # --------------------------------------------------------

    backend = (
        cv2.CAP_DSHOW
        if hasattr(cv2, "CAP_DSHOW")
        else cv2.CAP_ANY
    )

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
# CAMERA SETUP PAGE
# ============================================================

class CameraSetupPage(QWidget):
    """
    Camera setup page.

    Features:
    - Camera selection
    - Resolution selection
    - Mirrored live camera preview
    - MediaPipe hand detection
    - Hand landmark dots
    - Hand connection lines
    - Camera status
    - Tracking status
    - Continue to dashboard
    """

    def __init__(self, parent=None):

        super().__init__(parent)

        self.parent_window = parent

        # ----------------------------------------------------
        # Camera
        # ----------------------------------------------------

        self.capture = None

        self.camera_index = None

        self._tracking_active = False

        # ----------------------------------------------------
        # MediaPipe
        # ----------------------------------------------------

        self.mp_hands = None
        self.mp_draw = None
        self.mp_drawing_styles = None
        self.hands = None

        self.initialize_mediapipe()

        # ----------------------------------------------------
        # Timer
        # ----------------------------------------------------

        self.timer = QTimer(self)

        self.timer.timeout.connect(
            self.update_preview
        )

        # ----------------------------------------------------
        # UI
        # ----------------------------------------------------

        self.build_ui()

        # ----------------------------------------------------
        # Detect cameras
        # ----------------------------------------------------

        self.refresh_cameras()

    # ========================================================
    # MEDIAPIPE INITIALIZATION
    # ========================================================

    def initialize_mediapipe(self):

        try:

            self.mp_hands = mp.solutions.hands

            self.mp_draw = mp.solutions.drawing_utils

            self.mp_drawing_styles = (
                mp.solutions.drawing_styles
            )

            # ------------------------------------------------
            # Create MediaPipe Hands directly.
            #
            # This avoids depending on HandTracker during
            # camera preview.
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
    # BUILD UI
    # ========================================================

    def build_ui(self):

        self.setObjectName(
            "cameraSetup"
        )

        self.setStyleSheet(
            """

            QWidget#cameraSetup {
                background: #F4F6FB;
            }

            QLabel {
                background: transparent;
                color: #1F2430;
            }

            QLabel#heading {
                font-size: 26px;
                font-weight: 800;
                color: #1F2430;
            }

            QLabel#muted {
                color: #7B87A0;
                font-size: 12px;
            }

            QFrame#preview {
                background: #FFFFFF;
                border: 1px solid #E4E8F2;
                border-radius: 12px;
            }

            QFrame#cameraPlaceholder {
                background: #FAFBFE;
                border: 2px dashed #CDD6EA;
                border-radius: 10px;
            }

            QFrame#status {
                background: #EFF2F9;
                border: 1px solid #E4E8F2;
                border-radius: 8px;
            }

            QComboBox {
                background: #FFFFFF;
                color: #1F2430;
                border: 1px solid #D7DEEB;
                border-radius: 8px;
                padding: 8px 10px;
            }

            QComboBox QAbstractItemView {
                background: #FFFFFF;
                color: #1F2430;
                selection-background-color: #3E7CF7;
            }

            QPushButton {
                background: #FFFFFF;
                color: #5A6470;
                border: 1px solid #D7DEEB;
                border-radius: 8px;
                padding: 9px;
            }

            QPushButton:hover {
                background: #F0F3FA;
                color: #1F2430;
            }

            QPushButton#continue {
                background: #3E7CF7;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 700;
            }

            QPushButton#continue:hover {
                background: #5790FF;
            }

            QLabel#live {
                background: #EA4D5A;
                color: white;
                border-radius: 8px;
                padding: 3px 8px;
                font-size: 10px;
                font-weight: 700;
            }

            """
        )

        # ====================================================
        # MAIN LAYOUT
        # ====================================================

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            30,
            24,
            30,
            24
        )

        layout.setSpacing(
            6
        )

        # ====================================================
        # HEADER
        # ====================================================

        title = QLabel(
            "Camera Setup"
        )

        title.setObjectName(
            "heading"
        )

        subtitle = QLabel(
            "Select and verify a camera before starting gesture tracking."
        )

        subtitle.setObjectName(
            "muted"
        )

        layout.addWidget(
            title
        )

        layout.addWidget(
            subtitle
        )

        layout.addSpacing(
            6
        )

        # ====================================================
        # CONTENT
        # ====================================================

        content = QHBoxLayout()

        content.setSpacing(
            28
        )

        # ====================================================
        # PREVIEW BOX
        # ====================================================

        preview_box = QFrame()

        preview_box.setObjectName(
            "preview"
        )

        preview_box.setMinimumSize(
            420,
            380
        )

        preview_box.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

        preview_layout = QVBoxLayout(
            preview_box
        )

        preview_layout.setContentsMargins(
            28,
            22,
            28,
            18
        )

        # ====================================================
        # LIVE LABEL
        # ====================================================

        live = QLabel(
            "● LIVE"
        )

        live.setObjectName(
            "live"
        )

        preview_layout.addWidget(
            live,
            0,
            Qt.AlignLeft
        )

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

        # ----------------------------------------------------
        # Camera icon
        # ----------------------------------------------------

        self.cam_icon = QLabel(
            "📷"
        )

        self.cam_icon.setAlignment(
            Qt.AlignCenter
        )

        self.cam_icon.setStyleSheet(
            """
            font-size: 42px;
            color: #B9C2D4;
            """
        )

        # ----------------------------------------------------
        # Preview label
        # ----------------------------------------------------

        self.preview_label = QLabel(
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
            400,
            300
        )

        placeholder_layout.addWidget(
            self.cam_icon
        )

        placeholder_layout.addSpacing(
            10
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

        self.tracking_status = QLabel(
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

        self.tracking_status.setAlignment(
            Qt.AlignLeft
        )

        preview_layout.addWidget(
            self.tracking_status,
            0,
            Qt.AlignBottom
        )

        # ====================================================
        # CONTROLS
        # ====================================================

        controls = QVBoxLayout()

        controls.setSpacing(
            7
        )

        controls.setContentsMargins(
            0,
            0,
            0,
            0
        )

        # ====================================================
        # CAMERA
        # ====================================================

        controls.addWidget(
            self._caption(
                "CAMERA"
            )
        )

        camera_row = QHBoxLayout()

        camera_row.setSpacing(
            6
        )

        self.camera_combo = QComboBox()

        self.camera_combo.setMinimumWidth(
            240
        )

        self.camera_combo.setFixedHeight(
            40
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
            44,
            40
        )

        self.refresh_button.clicked.connect(
            self.refresh_cameras
        )

        camera_row.addWidget(
            self.refresh_button
        )

        controls.addLayout(
            camera_row
        )

        # ====================================================
        # RESOLUTION
        # ====================================================

        controls.addSpacing(
            6
        )

        controls.addWidget(
            self._caption(
                "RESOLUTION"
            )
        )

        self.resolution_combo = QComboBox()

        self.resolution_combo.setMinimumWidth(
            300
        )

        self.resolution_combo.setFixedHeight(
            40
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

        # ====================================================
        # STATUS
        # ====================================================

        controls.addSpacing(
            10
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
            8
        )

        self.status_items = {}

        # Camera
        self.status_items["camera"] = QLabel(
            "● Camera Not Tested"
        )

        self.status_items["opencv"] = QLabel(
            "● OpenCV Loaded"
        )

        self.status_items["mediapipe"] = QLabel(
            "● MediaPipe Ready"
        )

        self.status_items["hand"] = QLabel(
            "● Hand Model Ready"
        )

        for key in [
            "camera",
            "opencv",
            "mediapipe",
            "hand"
        ]:

            item = self.status_items[key]

            item.setStyleSheet(
                """
                color: #2F9E62;
                font-size: 11px;
                font-weight: 600;
                """
            )

            status_layout.addWidget(
                item
            )

        # ----------------------------------------------------
        # Update MediaPipe status
        # ----------------------------------------------------

        if self.hands is None:

            self.status_items[
                "mediapipe"
            ].setText(
                "● MediaPipe Not Ready"
            )

            self.status_items[
                "mediapipe"
            ].setStyleSheet(
                """
                color: #E04D5A;
                font-size: 11px;
                font-weight: 600;
                """
            )

            self.status_items[
                "hand"
            ].setText(
                "● Hand Model Not Ready"
            )

            self.status_items[
                "hand"
            ].setStyleSheet(
                """
                color: #E04D5A;
                font-size: 11px;
                font-weight: 600;
                """
            )

        controls.addWidget(
            status
        )

        controls.addStretch()

        # ====================================================
        # TEST CAMERA
        # ====================================================

        self.test_button = QPushButton(
            "Test Camera"
        )

        self.test_button.setMinimumWidth(
            300
        )

        self.test_button.setFixedHeight(
            40
        )

        self.test_button.clicked.connect(
            self.start_preview
        )

        controls.addWidget(
            self.test_button
        )

        # ====================================================
        # START TRACKING
        # ====================================================

        self.track_button = QPushButton(
            "Start Tracking"
        )

        self.track_button.setMinimumWidth(
            300
        )

        self.track_button.setFixedHeight(
            40
        )

        self.track_button.setEnabled(
            False
        )

        self.track_button.clicked.connect(
            self.start_tracking
        )

        controls.addWidget(
            self.track_button
        )

        # ====================================================
        # CONTINUE
        # ====================================================

        self.continue_button = QPushButton(
            "Continue"
        )

        self.continue_button.setObjectName(
            "continue"
        )

        self.continue_button.setMinimumWidth(
            300
        )

        self.continue_button.setFixedHeight(
            44
        )

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
        # ADD TO CONTENT
        # ====================================================

        content.addWidget(
            preview_box,
            1
        )

        content.addLayout(
            controls
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
            "muted"
        )

        label.setStyleSheet(
            """
            font-size: 10px;
            font-weight: 700;
            """
        )

        return label

    # ========================================================
    # REFRESH CAMERAS
    # ========================================================

    def refresh_cameras(self):

        self.stop_preview()

        self.track_button.setEnabled(
            False
        )

        self.continue_button.setEnabled(
            False
        )

        self.track_button.setText(
            "Start Tracking"
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

        self.camera_combo.blockSignals(
            False
        )

    # ========================================================
    # PLACEHOLDER
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

        self.track_button.setEnabled(
            False
        )

        self.continue_button.setEnabled(
            False
        )

        self.track_button.setText(
            "Start Tracking"
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
        # Open camera
        #
        # CAP_DSHOW is used on Windows.
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
        # Verify camera
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
        # Hide placeholder
        # ----------------------------------------------------

        self.cam_icon.hide()

        self.preview_label.setText("")

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

        # ----------------------------------------------------
        # Start timer
        # ----------------------------------------------------

        self.timer.start(
            30
        )

        self.track_button.setEnabled(
            True
        )

        self.tracking_status.setText(
            "● Camera Ready — Show your hand"
        )

        self.tracking_status.setStyleSheet(
            """
            color: #E8A33D;
            font-size: 10px;
            font-weight: 700;
            margin: 6px 0 0 0;
            """
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
        # This makes the preview behave like a selfie camera.
        #
        # ====================================================

        frame = cv2.flip(
            frame,
            1
        )

        # ----------------------------------------------------
        # Ensure contiguous memory
        # ----------------------------------------------------

        frame = np.ascontiguousarray(
            frame
        )

        frame_height, frame_width = (
            frame.shape[:2]
        )

        hand_detected = False

        # ====================================================
        # MEDIAPIPE HAND TRACKING
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
                # Make frame read-only for MediaPipe
                # ------------------------------------------------

                rgb_frame.flags.writeable = False

                # ------------------------------------------------
                # IMPORTANT:
                # process() receives RGB image
                # ------------------------------------------------

                results = self.hands.process(
                    rgb_frame
                )

                # ------------------------------------------------
                # Draw landmarks
                # ------------------------------------------------

                if (
                    results is not None
                    and results.multi_hand_landmarks
                ):

                    hand_detected = True

                    for hand_landmarks in (
                        results.multi_hand_landmarks
                    ):

                        # ----------------------------------------
                        # Draw lines and dots
                        # ----------------------------------------

                        if (
                            self.mp_drawing_styles
                            is not None
                        ):

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

                # ------------------------------------------------
                # Restore writeable state
                # ------------------------------------------------

                rgb_frame.flags.writeable = True

            except Exception as error:

                print(
                    "MediaPipe preview error:",
                    error
                )

        # ====================================================
        # TRACKING STATUS
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
                "● Camera Ready — Show your hand"
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

        # ====================================================
        # QIMAGE
        # ====================================================

        bytes_per_line = (
            channels * width
        )

        image = QImage(

            frame_rgb.data,

            width,

            height,

            bytes_per_line,

            QImage.Format_RGB888

        )

        # ----------------------------------------------------
        # Copy image.
        #
        # This prevents QImage from referencing memory
        # that may change after this function.
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
    # START TRACKING
    # ========================================================

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
        # Inform MainWindow
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
        # Activate tracking
        # ----------------------------------------------------

        self._tracking_active = True

        # ----------------------------------------------------
        # Button
        # ----------------------------------------------------

        self.track_button.setText(
            "Tracking Ready"
        )

        self.track_button.setEnabled(
            False
        )

        # ----------------------------------------------------
        # Enable Continue
        # ----------------------------------------------------

        self.continue_button.setEnabled(
            True
        )

        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------

        self.tracking_status.setText(
            "● Tracking Active"
        )

        self.tracking_status.setStyleSheet(
            """
            color: #2F9E62;
            font-size: 10px;
            font-weight: 700;
            margin: 6px 0 0 0;
            """
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

        self._tracking_active = False

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
        # Stop camera
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

        # ----------------------------------------------------
        # Go to dashboard
        # ----------------------------------------------------

        if self.parent_window is not None:

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
    Simple dialog for selecting a camera.
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
                background: #F4F6FB;
            }

            QLabel {
                background: transparent;
                color: #1F2430;
            }

            QLabel#heading {
                font-size: 20px;
                font-weight: 800;
            }

            QLabel#muted {
                color: #7B87A0;
                font-size: 12px;
            }

            QComboBox {
                background: #FFFFFF;
                color: #1F2430;
                border: 1px solid #D7DEEB;
                border-radius: 7px;
                padding: 8px;
                min-width: 200px;
            }

            QComboBox QAbstractItemView {
                background: #FFFFFF;
                color: #1F2430;
                selection-background-color: #3E7CF7;
            }

            QPushButton {
                background: #FFFFFF;
                color: #5A6470;
                border: 1px solid #D7DEEB;
                border-radius: 7px;
                padding: 9px;
                min-width: 100px;
            }

            QPushButton:hover {
                background: #F0F3FA;
                color: #1F2430;
            }

            QPushButton#accept {
                background: #3E7CF7;
                color: white;
                border: none;
                border-radius: 7px;
                padding: 9px;
                font-weight: 700;
            }

            QPushButton#accept:hover {
                background: #5790FF;
            }

            QPushButton#cancel {
                background: #FFFFFF;
                color: #7B87A0;
                border: 1px solid #D7DEEB;
                border-radius: 7px;
                padding: 9px;
                min-width: 100px;
            }

            """
        )

        # ----------------------------------------------------
        # Layout
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Title
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Subtitle
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Camera Combo
        # ----------------------------------------------------

        self.camera_combo = QComboBox()

        layout.addWidget(
            self.camera_combo
        )

        # ----------------------------------------------------
        # Buttons
        # ----------------------------------------------------

        self.button_box = QDialogButtonBox(

            QDialogButtonBox.Ok
            | QDialogButtonBox.Cancel

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

        # ----------------------------------------------------
        # Selected camera
        # ----------------------------------------------------

        self.selected_index = None

        self.selected_name = None

        # ----------------------------------------------------
        # Detect cameras
        # ----------------------------------------------------

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