import cv2
import pyautogui

# MediaPipe may fail to load its DLL on some Python setups. Make it optional.
try:
    import mediapipe as mp
except Exception as e:
    print("MediaPipe import error:", e)
    mp = None

from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFrame,
    QSlider,
)


class VirtualMousePage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.parent_window = parent

        # ======================================================
        # CAMERA
        # ======================================================

        self.camera = None
        self.camera_index = 0

        self.camera_running = False
        self.camera_paused = False

        # ======================================================
        # MEDIAPIPE
        # ======================================================

        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,
            min_detection_confidence=0.55,
            min_tracking_confidence=0.55,
        )

        # ======================================================
        # PYAutoGUI
        # ======================================================

        pyautogui.PAUSE = 0.01

        self.screen_width, self.screen_height = (
            pyautogui.size()
        )

        # ======================================================
        # MOUSE SETTINGS
        # ======================================================

        self.sensitivity = 90

        self.previous_x = None
        self.previous_y = None

        self.smoothing = 0.6

        self.last_gesture = "None"

        # Prevent accidental repeated clicks
        self.left_click_cooldown = 0
        self.right_click_cooldown = 0

        # ======================================================
        # FPS
        # ======================================================

        self.frame_count = 0

        # ======================================================
        # TIMER
        # ======================================================

        self.timer = QTimer(self)
        self.timer.timeout.connect(
            self.update_camera
        )

        # ======================================================
        # BUILD UI
        # ======================================================

        self.build_ui()

    # ==========================================================
    # UI
    # ==========================================================

    def build_ui(self):

        main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(
            40,
            30,
            40,
            30
        )

        main_layout.setSpacing(18)

        # ======================================================
        # TITLE
        # ======================================================

        title = QLabel(
            "Virtual Mouse"
        )

        title.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: 700;
                color: #12377D;
            }
        """)

        subtitle = QLabel(
            "Control your computer cursor using hand gestures."
        )

        subtitle.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #7183A6;
            }
        """)

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # ======================================================
        # CONTENT
        # ======================================================

        content_layout = QHBoxLayout()

        content_layout.setSpacing(20)

        # ======================================================
        # LEFT PANEL
        # ======================================================

        left_panel = QVBoxLayout()

        left_panel.setSpacing(12)

        # ------------------------------------------------------
        # TRACKING FRAME
        # ------------------------------------------------------

        tracking_frame = QFrame()

        tracking_frame.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #D9E4F5;
                border-radius: 14px;
            }
        """)

        tracking_layout = QVBoxLayout(
            tracking_frame
        )

        tracking_layout.setContentsMargins(
            16,
            16,
            16,
            16
        )

        tracking_layout.setSpacing(12)

        # ------------------------------------------------------
        # TOP STATUS
        # ------------------------------------------------------

        status_row = QHBoxLayout()

        self.tracking_status = QLabel(
            "● Tracking Inactive"
        )

        self.tracking_status.setStyleSheet("""
            QLabel {
                background: #EAF2FF;
                color: #5574A8;
                padding: 7px 12px;
                border-radius: 15px;
                font-weight: 600;
            }
        """)

        self.fps_label = QLabel(
            "FPS: 0"
        )

        self.fps_label.setStyleSheet("""
            QLabel {
                background: #EAF2FF;
                color: #5574A8;
                padding: 7px 12px;
                border-radius: 15px;
                font-weight: 600;
            }
        """)

        status_row.addWidget(
            self.tracking_status
        )

        status_row.addWidget(
            self.fps_label
        )

        status_row.addStretch()

        tracking_layout.addLayout(
            status_row
        )

        # ------------------------------------------------------
        # CAMERA DISPLAY
        # ------------------------------------------------------

        self.camera_label = QLabel()

        self.camera_label.setMinimumSize(
            650,
            450
        )

        self.camera_label.setAlignment(
            Qt.AlignCenter
        )

        self.camera_label.setStyleSheet("""
            QLabel {
                background: #F8FCFF;
                border: 1px solid #C5D8EF;
                border-radius: 10px;
                color: #7890B5;
                font-size: 15px;
            }
        """)

        self.camera_label.setText(
            "Camera is stopped.\n\n"
            "Click Start to begin tracking."
        )

        tracking_layout.addWidget(
            self.camera_label
        )

        # ------------------------------------------------------
        # CURRENT GESTURE
        # ------------------------------------------------------

        gesture_box = QFrame()

        gesture_box.setStyleSheet("""
            QFrame {
                background: #EAF2FF;
                border: none;
                border-radius: 10px;
            }
        """)

        gesture_layout = QVBoxLayout(
            gesture_box
        )

        gesture_layout.setContentsMargins(
            14,
            10,
            14,
            10
        )

        gesture_title = QLabel(
            "GESTURE"
        )

        gesture_title.setStyleSheet("""
            QLabel {
                color: #7C9AC5;
                font-size: 10px;
                font-weight: 600;
            }
        """)

        self.gesture_action = QLabel(
            "Move Cursor"
        )

        self.gesture_action.setStyleSheet("""
            QLabel {
                color: #A7BFDF;
                font-size: 16px;
                font-weight: 700;
            }
        """)

        gesture_layout.addWidget(
            gesture_title
        )

        gesture_layout.addWidget(
            self.gesture_action
        )

        tracking_layout.addWidget(
            gesture_box
        )

        left_panel.addWidget(
            tracking_frame
        )

        content_layout.addLayout(
            left_panel,
            3
        )

        # ======================================================
        # RIGHT PANEL
        # ======================================================

        right_panel = QVBoxLayout()

        right_panel.setSpacing(15)

        # ======================================================
        # GESTURE STATUS
        # ======================================================

        status_frame = QFrame()

        status_frame.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #D9E4F5;
                border-radius: 12px;
            }
        """)

        status_layout = QGridLayout(
            status_frame
        )

        status_layout.setContentsMargins(
            16,
            16,
            16,
            16
        )

        status_layout.setVerticalSpacing(
            12
        )

        status_title = QLabel(
            "Gesture Status"
        )

        status_title.setStyleSheet("""
            QLabel {
                font-size: 15px;
                font-weight: 700;
                color: #12377D;
            }
        """)

        status_layout.addWidget(
            status_title,
            0,
            0,
            1,
            2
        )

        self.cursor_status = QLabel(
            "● Active"
        )

        self.left_status = QLabel(
            "● Ready"
        )

        self.right_status = QLabel(
            "● Ready"
        )

        self.scroll_status = QLabel(
            "● Ready"
        )

        self.add_status_row(
            status_layout,
            1,
            "Cursor",
            self.cursor_status
        )

        self.add_status_row(
            status_layout,
            2,
            "Left Click",
            self.left_status
        )

        self.add_status_row(
            status_layout,
            3,
            "Right Click",
            self.right_status
        )

        self.add_status_row(
            status_layout,
            4,
            "Scroll",
            self.scroll_status
        )

        right_panel.addWidget(
            status_frame
        )

        # ======================================================
        # GESTURE GUIDE
        # ======================================================

        guide_frame = QFrame()

        guide_frame.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #D9E4F5;
                border-radius: 12px;
            }
        """)

        guide_layout = QGridLayout(
            guide_frame
        )

        guide_layout.setContentsMargins(
            16,
            16,
            16,
            16
        )

        guide_layout.setVerticalSpacing(
            12
        )

        guide_title = QLabel(
            "Gesture Guide"
        )

        guide_title.setStyleSheet("""
            QLabel {
                font-size: 15px;
                font-weight: 700;
                color: #12377D;
            }
        """)

        guide_layout.addWidget(
            guide_title,
            0,
            0,
            1,
            3
        )

        self.add_guide_row(
            guide_layout,
            1,
            "Index Finger",
            "→",
            "Move Cursor"
        )

        self.add_guide_row(
            guide_layout,
            2,
            "Thumb + Index",
            "→",
            "Left Click"
        )

        self.add_guide_row(
            guide_layout,
            3,
            "Thumb + Middle",
            "→",
            "Right Click"
        )

        self.add_guide_row(
            guide_layout,
            4,
            "Open Palm",
            "→",
            "Scroll"
        )

        right_panel.addWidget(
            guide_frame
        )

        # ======================================================
        # SENSITIVITY
        # ======================================================

        sensitivity_frame = QFrame()

        sensitivity_frame.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #D9E4F5;
                border-radius: 12px;
            }
        """)

        sensitivity_layout = QVBoxLayout(
            sensitivity_frame
        )

        sensitivity_layout.setContentsMargins(
            16,
            14,
            16,
            14
        )

        sensitivity_title = QLabel(
            "Sensitivity"
        )

        sensitivity_title.setStyleSheet("""
            QLabel {
                color: #5574A8;
                font-size: 13px;
                font-weight: 600;
            }
        """)

        self.sensitivity_slider = QSlider(
            Qt.Horizontal
        )

        self.sensitivity_slider.setMinimum(
            10
        )

        self.sensitivity_slider.setMaximum(
            100
        )

        self.sensitivity_slider.setValue(
            90
        )

        self.sensitivity_slider.valueChanged.connect(
            self.change_sensitivity
        )

        self.sensitivity_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #DCE8F5;
                border-radius: 2px;
            }

            QSlider::handle:horizontal {
                width: 12px;
                height: 12px;
                margin: -4px 0;
                background: #12377D;
                border-radius: 6px;
            }
        """)

        sensitivity_layout.addWidget(
            sensitivity_title
        )

        sensitivity_layout.addWidget(
            self.sensitivity_slider
        )

        right_panel.addWidget(
            sensitivity_frame
        )

        # ======================================================
        # BUTTONS
        # ======================================================

        button_layout = QHBoxLayout()

        button_layout.setSpacing(8)

        self.start_button = QPushButton(
            "Start"
        )

        self.pause_button = QPushButton(
            "Pause"
        )

        self.stop_button = QPushButton(
            "Stop"
        )

        self.start_button.setFixedHeight(
            40
        )

        self.pause_button.setFixedHeight(
            40
        )

        self.stop_button.setFixedHeight(
            40
        )

        self.start_button.clicked.connect(
            self.start_tracking
        )

        self.pause_button.clicked.connect(
            self.pause_tracking
        )

        self.stop_button.clicked.connect(
            self.stop_tracking
        )

        self.start_button.setStyleSheet("""
            QPushButton {
                background: #A9C2E7;
                color: #12377D;
                border: none;
                border-radius: 8px;
                font-weight: 700;
            }

            QPushButton:hover {
                background: #91AFDA;
            }
        """)

        self.pause_button.setStyleSheet("""
            QPushButton {
                background: white;
                color: #12377D;
                border: 1px solid #C8DAEF;
                border-radius: 8px;
                font-weight: 600;
            }

            QPushButton:hover {
                background: #F0F6FC;
            }
        """)

        self.stop_button.setStyleSheet("""
            QPushButton {
                background: white;
                color: #12377D;
                border: 1px solid #C8DAEF;
                border-radius: 8px;
                font-weight: 600;
            }

            QPushButton:hover {
                background: #F0F6FC;
            }
        """)

        button_layout.addWidget(
            self.start_button
        )

        button_layout.addWidget(
            self.pause_button
        )

        button_layout.addWidget(
            self.stop_button
        )

        right_panel.addLayout(
            button_layout
        )

        right_panel.addStretch()

        content_layout.addLayout(
            right_panel,
            1
        )

        main_layout.addLayout(
            content_layout
        )

    # ==========================================================
    # STATUS ROW
    # ==========================================================

    def add_status_row(
        self,
        layout,
        row,
        title,
        value
    ):

        title_label = QLabel(
            title
        )

        title_label.setStyleSheet("""
            QLabel {
                color: #7183A6;
                font-size: 13px;
            }
        """)

        value.setStyleSheet("""
            QLabel {
                color: #5574A8;
                font-weight: 600;
                font-size: 13px;
            }
        """)

        layout.addWidget(
            title_label,
            row,
            0
        )

        layout.addWidget(
            value,
            row,
            1,
            alignment=Qt.AlignRight
        )

    # ==========================================================
    # GUIDE ROW
    # ==========================================================

    def add_guide_row(
        self,
        layout,
        row,
        gesture,
        arrow,
        action
    ):

        gesture_label = QLabel(
            gesture
        )

        gesture_label.setStyleSheet("""
            QLabel {
                color: #5574A8;
                font-size: 12px;
            }
        """)

        arrow_label = QLabel(
            arrow
        )

        arrow_label.setStyleSheet("""
            QLabel {
                color: #8EA9CA;
                font-size: 14px;
            }
        """)

        action_label = QLabel(
            action
        )

        action_label.setStyleSheet("""
            QLabel {
                color: #7183A6;
                font-size: 12px;
            }
        """)

        layout.addWidget(
            gesture_label,
            row,
            0
        )

        layout.addWidget(
            arrow_label,
            row,
            1
        )

        layout.addWidget(
            action_label,
            row,
            2
        )

    # ==========================================================
    # CAMERA
    # ==========================================================

    def open_camera(self):

        if self.camera is not None:
            return True

        self.camera = cv2.VideoCapture(
            self.camera_index,
            cv2.CAP_DSHOW
        )

        if not self.camera.isOpened():

            self.camera.release()

            self.camera = cv2.VideoCapture(
                self.camera_index
            )

        if not self.camera.isOpened():

            self.camera = None

            self.tracking_status.setText(
                "● Camera Not Available"
            )

            self.tracking_status.setStyleSheet("""
                QLabel {
                    background: #FFF0F0;
                    color: #B45A5A;
                    padding: 7px 12px;
                    border-radius: 15px;
                    font-weight: 600;
                }
            """)

            return False

        self.camera.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            640
        )

        self.camera.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            480
        )

        # Keep the camera label size fixed so the preview doesn't pop/zoom.
        # The displayed frame is scaled to fit the label, not the label to frame.
        self.camera_label.setMinimumSize(
            650,
            450
        )

        return True

    # ==========================================================
    # START TRACKING
    # ==========================================================

    def start_tracking(self):

        if not self.open_camera():
            return

        self.camera_running = True
        self.camera_paused = False

        self.tracking_status.setText(
            "● Tracking Active"
        )

        self.tracking_status.setStyleSheet("""
            QLabel {
                background: #EAF8EF;
                color: #2A9561;
                padding: 7px 12px;
                border-radius: 15px;
                font-weight: 600;
            }
        """)

        if not self.timer.isActive():

            self.timer.start(30)

    # ==========================================================
    # PAUSE
    # ==========================================================

    def pause_tracking(self):

        if not self.camera_running:
            return

        self.camera_paused = True

        self.tracking_status.setText(
            "● Tracking Paused"
        )

        self.tracking_status.setStyleSheet("""
            QLabel {
                background: #FFF6E5;
                color: #B47B32;
                padding: 7px 12px;
                border-radius: 15px;
                font-weight: 600;
            }
        """)

    # ==========================================================
    # STOP
    # ==========================================================

    def stop_tracking(self):

        self.camera_running = False
        self.camera_paused = False

        if self.timer.isActive():
            self.timer.stop()

        if self.camera:

            self.camera.release()
            self.camera = None

        self.previous_x = None
        self.previous_y = None

        self.last_gesture = "None"

        self.tracking_status.setText(
            "● Tracking Inactive"
        )

        self.tracking_status.setStyleSheet("""
            QLabel {
                background: #EAF2FF;
                color: #5574A8;
                padding: 7px 12px;
                border-radius: 15px;
                font-weight: 600;
            }
        """)

        self.fps_label.setText(
            "FPS: 0"
        )

        self.gesture_action.setText(
            "Move Cursor"
        )

        self.camera_label.clear()

        self.camera_label.setText(
            "Camera is stopped.\n\n"
            "Click Start to begin tracking."
        )

        self.reset_gesture_status()

    # ==========================================================
    # UPDATE CAMERA
    # ==========================================================

    def update_camera(self):

        if not self.camera:
            return

        if self.camera_paused:
            return

        success, frame = self.camera.read()

        if not success:
            return

        frame = cv2.flip(
            frame,
            1
        )

        # ------------------------------------------------------
        # MEDIAPIPE
        # ------------------------------------------------------

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

        # ------------------------------------------------------
        # HAND DETECTED
        # ------------------------------------------------------

        if results.multi_hand_landmarks:

            hand = results.multi_hand_landmarks[0]

            self.mp_drawing.draw_landmarks(
                frame,
                hand,
                self.mp_hands.HAND_CONNECTIONS
            )

            gesture = self.detect_gesture(
                hand
            )

            self.perform_gesture(
                gesture,
                hand
            )

        else:

            self.reset_gesture_status()

        # ------------------------------------------------------
        # FPS
        # ------------------------------------------------------

        self.frame_count += 1

        self.fps_label.setText(
            "FPS: 30"
        )

        # ------------------------------------------------------
        # CAMERA DISPLAY
        # ------------------------------------------------------

        self.display_frame(
            frame
        )

    # ==========================================================
    # GESTURE DETECTION
    # ==========================================================

    def detect_gesture(
        self,
        hand
    ):

        landmarks = hand.landmark

        # ------------------------------------------------------
        # LANDMARKS
        # ------------------------------------------------------

        thumb_tip = landmarks[
            self.mp_hands.HandLandmark.THUMB_TIP
        ]

        index_tip = landmarks[
            self.mp_hands.HandLandmark.INDEX_FINGER_TIP
        ]

        middle_tip = landmarks[
            self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP
        ]

        ring_tip = landmarks[
            self.mp_hands.HandLandmark.RING_FINGER_TIP
        ]

        pinky_tip = landmarks[
            self.mp_hands.HandLandmark.PINKY_TIP
        ]

        # ------------------------------------------------------
        # FINGER STATES
        # ------------------------------------------------------

        index_up = (
            index_tip.y
            <
            landmarks[
                self.mp_hands.HandLandmark.INDEX_FINGER_PIP
            ].y
        )

        middle_up = (
            middle_tip.y
            <
            landmarks[
                self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP
            ].y
        )

        ring_up = (
            ring_tip.y
            <
            landmarks[
                self.mp_hands.HandLandmark.RING_FINGER_PIP
            ].y
        )

        pinky_up = (
            pinky_tip.y
            <
            landmarks[
                self.mp_hands.HandLandmark.PINKY_PIP
            ].y
        )

        # ------------------------------------------------------
        # DISTANCES
        # ------------------------------------------------------

        thumb_index_distance = (
            (
                thumb_tip.x - index_tip.x
            ) ** 2
            +
            (
                thumb_tip.y - index_tip.y
            ) ** 2
        ) ** 0.5

        thumb_middle_distance = (
            (
                thumb_tip.x - middle_tip.x
            ) ** 2
            +
            (
                thumb_tip.y - middle_tip.y
            ) ** 2
        ) ** 0.5

        # ------------------------------------------------------
        # LEFT CLICK
        # ------------------------------------------------------

        if (
            thumb_index_distance < 0.075
            and index_up
        ):

            return "Thumb + Index"

        # ------------------------------------------------------
        # RIGHT CLICK
        # ------------------------------------------------------

        if (
            thumb_middle_distance < 0.075
            and middle_up
        ):

            return "Thumb + Middle"

        # ------------------------------------------------------
        # OPEN PALM
        # ------------------------------------------------------

        if (
            index_up
            and middle_up
            and ring_up
            and pinky_up
        ):

            return "Open Palm"

        # ------------------------------------------------------
        # INDEX FINGER
        # ------------------------------------------------------

        if (
            index_up
            and not middle_up
            and not ring_up
            and not pinky_up
        ):

            return "Index Finger"

        return "None"

    # ==========================================================
    # PERFORM GESTURE
    # ==========================================================

    def perform_gesture(
        self,
        gesture,
        hand
    ):

        if gesture == "None":

            return

        self.gesture_action.setText(
            self.get_action_name(
                gesture
            )
        )

        # ------------------------------------------------------
        # INDEX = MOVE CURSOR
        # ------------------------------------------------------

        if gesture == "Index Finger":

            self.move_cursor(
                hand
            )

            self.cursor_status.setText(
                "● Active"
            )

            self.cursor_status.setStyleSheet("""
                QLabel {
                    color: #2A9561;
                    font-weight: 600;
                }
            """)

        # ------------------------------------------------------
        # LEFT CLICK
        # ------------------------------------------------------

        elif gesture == "Thumb + Index":

            if self.left_click_cooldown <= 0:

                pyautogui.click()

                self.left_click_cooldown = 8

            else:

                self.left_click_cooldown -= 1

            self.left_status.setText(
                "● Active"
            )

            self.left_status.setStyleSheet("""
                QLabel {
                    color: #2A9561;
                    font-weight: 600;
                }
            """)

        # ------------------------------------------------------
        # RIGHT CLICK
        # ------------------------------------------------------

        elif gesture == "Thumb + Middle":

            if self.right_click_cooldown <= 0:

                pyautogui.rightClick()

                self.right_click_cooldown = 8

            else:

                self.right_click_cooldown -= 1

            self.right_status.setText(
                "● Active"
            )

            self.right_status.setStyleSheet("""
                QLabel {
                    color: #2A9561;
                }
            """)

        # ------------------------------------------------------
        # SCROLL
        # ------------------------------------------------------

        elif gesture == "Open Palm":

            self.scroll_mouse(
                hand
            )

            self.scroll_status.setText(
                "● Active"
            )

            self.scroll_status.setStyleSheet("""
                QLabel {
                    color: #2A9561;
                    font-weight: 600;
                }
            """)

        self.last_gesture = gesture

    # ==========================================================
    # MOVE CURSOR
    # ==========================================================

    def move_cursor(
        self,
        hand
    ):

        index_tip = hand.landmark[
            self.mp_hands.HandLandmark.INDEX_FINGER_TIP
        ]

        # Center of the visible tracking area. Normalized coordinates
        # (0..1) are remapped around 0.5 with a gain, so you only need to
        # move your hand a little to cover more of the screen — no need to
        # fully extend your arm toward the edges.
        center = 0.5
        gain = 1.6

        cx = (index_tip.x - center) * gain + center
        cy = (index_tip.y - center) * gain + center

        target_x = int(
            max(0.0, min(1.0, cx))
            * self.screen_width
        )

        target_y = int(
            max(0.0, min(1.0, cy))
            * self.screen_height
        )

        # Sensitivity adjustment
        sensitivity_factor = (
            self.sensitivity / 50
        )

        if self.previous_x is None:

            self.previous_x = target_x
            self.previous_y = target_y

        smooth_x = (
            self.previous_x
            +
            (
                target_x
                - self.previous_x
            )
            *
            self.smoothing
        )

        smooth_y = (
            self.previous_y
            +
            (
                target_y
                - self.previous_y
            )
            *
            self.smoothing
        )

        smooth_x = max(
            0,
            min(
                self.screen_width - 1,
                int(smooth_x)
            )
        )

        smooth_y = max(
            0,
            min(
                self.screen_height - 1,
                int(smooth_y)
            )
        )

        pyautogui.moveTo(
            smooth_x,
            smooth_y,
            duration=0
        )

        self.previous_x = smooth_x
        self.previous_y = smooth_y

    # ==========================================================
    # SCROLL
    # ==========================================================

    def scroll_mouse(
        self,
        hand
    ):

        wrist = hand.landmark[
            self.mp_hands.HandLandmark.WRIST
        ]

        middle_tip = hand.landmark[
            self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP
        ]

        difference = (
            wrist.y
            - middle_tip.y
        )

        if difference > 0.20:

            pyautogui.scroll(
                2
            )

        elif difference < -0.20:

            pyautogui.scroll(
                -2
            )

    # ==========================================================
    # ACTION NAME
    # ==========================================================

    def get_action_name(
        self,
        gesture
    ):

        actions = {

            "Index Finger":
                "Move Cursor",

            "Thumb + Index":
                "Left Click",

            "Thumb + Middle":
                "Right Click",

            "Open Palm":
                "Scroll",

        }

        return actions.get(
            gesture,
            "Ready"
        )

    # ==========================================================
    # RESET STATUS
    # ==========================================================

    def reset_gesture_status(self):

        self.cursor_status.setText(
            "● Ready"
        )

        self.left_status.setText(
            "● Ready"
        )

        self.right_status.setText(
            "● Ready"
        )

        self.scroll_status.setText(
            "● Ready"
        )

        self.cursor_status.setStyleSheet("""
            QLabel {
                color: #8EA9CA;
                font-weight: 600;
            }
        """)

        self.left_status.setStyleSheet("""
            QLabel {
                color: #8EA9CA;
                font-weight: 600;
            }
        """)

        self.right_status.setStyleSheet("""
            QLabel {
                color: #8EA9CA;
                font-weight: 600;
            }
        """)

        self.scroll_status.setStyleSheet("""
            QLabel {
                color: #8EA9CA;
                font-weight: 600;
            }
        """)

    # ==========================================================
    # DISPLAY FRAME
    # ==========================================================

    def display_frame(
        self,
        frame
    ):

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

        # Use a fixed target and FastTransformation: cheaper than
        # SmoothTransformation every frame (reduces lag) and stable size.
        target = self.camera_label.size()
        if target.width() < 40 or target.height() < 40:
            target = QSize(650, 450)

        pixmap = pixmap.scaled(
            target,
            Qt.KeepAspectRatio,
            Qt.FastTransformation
        )

        self.camera_label.setPixmap(
            pixmap
        )

    # ==========================================================
    # SENSITIVITY
    # ==========================================================

    def change_sensitivity(
        self,
        value
    ):

        self.sensitivity = value

    # ==========================================================
    # CAMERA SELECTION
    # ==========================================================

    def setActiveCamera(
        self,
        index,
        name
    ):

        was_running = self.camera_running

        self.stop_tracking()

        self.camera_index = index

        if was_running:

            self.start_tracking()

    # ==========================================================
    # CAMERA NAME
    # ==========================================================

    def updateCameraName(
        self,
        name
    ):

        self.camera_name = name

    # ==========================================================
    # CLEANUP
    # ==========================================================

    def close_camera(self):

        if self.timer.isActive():

            self.timer.stop()

        if self.camera:

            self.camera.release()

            self.camera = None

        self.camera_running = False

        self.camera_paused = False

    # ==========================================================
    # CLOSE EVENT
    # ==========================================================

    def closeEvent(
        self,
        event
    ):

        self.close_camera()

        if self.hands:

            self.hands.close()

        event.accept()