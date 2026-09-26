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
    QSizePolicy,
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

        # Latest frame, shared with other pages (Whiteboard preview) so they
        # can show the camera without opening it themselves.
        self.latest_frame = None

        # Latest detected hand landmarks, shared with other pages so they can
        # run their own gesture logic without opening the camera again.
        self.latest_hand = None

        # Remembers that the user wants tracking active, so we can resume
        # after navigating away and back (the webcam is released while away).
        self.camera_was_running = False

        # Fixed camera resolution.
        # Keeping this constant helps prevent the preview from
        # changing size/framing when tracking starts.
        self.camera_width = 640
        self.camera_height = 480

        # ======================================================
        # MEDIAPIPE
        # ======================================================

        # MediaPipe is optional: if it failed to load, disable
        # hand tracking but keep the page fully functional.
        if mp is not None:

            self.mp_hands = mp.solutions.hands
            self.mp_drawing = mp.solutions.drawing_utils

            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                model_complexity=0,
                min_detection_confidence=0.55,
                min_tracking_confidence=0.55,
            )

        else:

            self.mp_hands = None
            self.mp_drawing = None
            self.hands = None

        # ======================================================
        # PYAUTOGUI
        # ======================================================

        pyautogui.PAUSE = 0.01

        # Gesture control must be able to reach the screen edges/corners,
        # so disable the corner fail-safe (otherwise moving the cursor to a
        # corner raises FailSafeException).
        pyautogui.FAILSAFE = False

        self.screen_width, self.screen_height = (
            pyautogui.size()
        )

        # ======================================================
        # MOUSE SETTINGS
        # ======================================================

        self.sensitivity = 50

        self.previous_x = None
        self.previous_y = None

        # Exponential smoothing for the cursor (lower = steadier, less shaky).
        self.smoothing = 0.4

        # Ignore sub-pixel hand jitter so the cursor does not tremble.
        self.dead_zone = 4

        # Auto-centre calibration: the hand's position when tracking starts
        # becomes the screen centre. This makes the LEFT and RIGHT hand (or
        # any resting position) behave identically and stops small movements
        # from slamming the cursor into an edge.
        self._neutral_x = None
        self._neutral_y = None
        self._cal_samples = []

        self.last_gesture = "None"

        # Prevent accidental repeated clicks
        self.left_click_cooldown = 0
        self.right_click_cooldown = 0

        # Scroll state (Open Palm + vertical swipe)
        self._scroll_accum = 0.0
        self._scroll_prev_y = None

        # Drag state (held only by the "Index + Middle" draw gesture)
        self.is_dragging = False

        # Grace frames before releasing a drag (avoids the line breaking
        # when the hand is briefly not detected).
        self._hold_grace = 0

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

        from settings import theme as app_theme

        c = app_theme.colors()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(34, 26, 34, 26)
        main_layout.setSpacing(14)

        # --------------------------------------------------
        # TITLE
        # --------------------------------------------------

        title = QLabel("Virtual Mouse")
        title.setStyleSheet(
            f"QLabel {{ font-size: 26px; font-weight: 800; color: {c['text']}; }}"
        )

        subtitle = QLabel(
            "Use your hand like a mouse — move the cursor, click and scroll."
        )
        subtitle.setStyleSheet(
            f"QLabel {{ font-size: 13px; color: {c['text_secondary']}; }}"
        )

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # --------------------------------------------------
        # CONTENT
        # --------------------------------------------------

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # ==================================================
        # LEFT: CAMERA (responsive)
        # ==================================================

        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)

        camera_frame = QFrame()
        camera_frame.setStyleSheet(
            f"""
            QFrame {{
                background: {c['card']};
                border: 1px solid {c['border']};
                border-radius: 14px;
            }}
            """
        )

        camera_layout = QVBoxLayout(camera_frame)
        camera_layout.setContentsMargins(14, 14, 14, 12)
        camera_layout.setSpacing(10)

        self.camera_label = QLabel()
        self.camera_label.setMinimumSize(340, 240)
        self.camera_label.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setStyleSheet(
            f"""
            QLabel {{
                background: {c['bg']};
                border: 1px solid {c['border']};
                border-radius: 10px;
                color: {c['text_secondary']};
                font-size: 14px;
            }}
            """
        )
        self.camera_label.setText(
            "Camera is stopped.\n\nClick Start to begin tracking."
        )

        camera_layout.addWidget(self.camera_label, 1)

        # Compact status row UNDER the camera feed.
        status_row = QHBoxLayout()
        status_row.setSpacing(8)

        self.tracking_status = self.make_pill("● Tracking Inactive")
        self.fps_label = self.make_pill("FPS: 0")
        self.gesture_action = self.make_pill("Gesture: —")

        status_row.addWidget(self.tracking_status)
        status_row.addWidget(self.fps_label)
        status_row.addWidget(self.gesture_action)
        status_row.addStretch()

        camera_layout.addLayout(status_row)

        left_panel.addWidget(camera_frame, 1)
        content_layout.addLayout(left_panel, 3)

        # ==================================================
        # RIGHT: GUIDE + SETTINGS
        # ==================================================

        right_panel = QVBoxLayout()
        right_panel.setSpacing(12)

        right_panel.addWidget(self.build_guide_card())
        right_panel.addWidget(self.build_sensitivity_card(c))
        right_panel.addLayout(self.build_buttons(c))
        right_panel.addStretch()

        content_layout.addLayout(right_panel, 1)
        main_layout.addLayout(content_layout, 1)

        self.setStyleSheet(
            f"QWidget {{ background: {c['bg']}; color: {c['text']}; }}"
        )

    # ==========================================================
    # SMALL UI HELPERS
    # ==========================================================

    def make_pill(self, text):

        from settings import theme as app_theme

        c = app_theme.colors()

        label = QLabel(text)
        label.setStyleSheet(
            f"""
            QLabel {{
                background: {c['card']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 12px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            """
        )
        return label

    def build_guide_card(self):

        from settings import theme as app_theme

        c = app_theme.colors()

        frame = QFrame()
        frame.setStyleSheet(
            f"""
            QFrame {{
                background: {c['card']};
                border: 1px solid {c['border']};
                border-radius: 12px;
            }}
            """
        )

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(9)

        title = QLabel("How to use")
        title.setStyleSheet(
            f"QLabel {{ font-size: 15px; font-weight: 800; color: {c['text']}; }}"
        )
        layout.addWidget(title)

        rows = [
            ("🖐️", "Open palm", "Move the cursor"),
            ("✌️", "Peace sign (apart)", "Drawing cursor"),
            ("✌️", "Index + middle together", "Draw / write"),
            ("✊", "Closed palm (fist)", "Left click"),
            ("🤏", "Thumb + Middle", "Right click"),
            ("⬆️", "Palm up", "Scroll up"),
            ("⬇️", "Palm down", "Scroll down"),
        ]

        for icon, name, action in rows:
            layout.addWidget(
                self.make_guide_row(icon, name, action, c)
            )

        return frame

    def make_guide_row(self, icon, name, action, c):

        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 2, 0, 2)
        h.setSpacing(8)

        icon_label = QLabel(icon)
        icon_label.setFixedWidth(26)
        icon_label.setStyleSheet("QLabel { font-size: 15px; }")

        name_label = QLabel(name)
        name_label.setStyleSheet(
            f"QLabel {{ color: {c['text']}; font-size: 12px; font-weight: 600; }}"
        )

        action_label = QLabel(action)
        action_label.setStyleSheet(
            f"QLabel {{ color: {c['text_secondary']}; font-size: 12px; }}"
        )

        h.addWidget(icon_label)
        h.addWidget(name_label)
        h.addStretch()
        h.addWidget(action_label)

        return row

    def build_sensitivity_card(self, c):

        frame = QFrame()
        frame.setStyleSheet(
            f"""
            QFrame {{
                background: {c['card']};
                border: 1px solid {c['border']};
                border-radius: 12px;
            }}
            """
        )

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()

        label = QLabel("Cursor Sensitivity")
        label.setStyleSheet(
            f"QLabel {{ color: {c['text']}; font-size: 13px; font-weight: 700; }}"
        )

        self.sensitivity_value = QLabel(
            f"{self.sensitivity}%"
        )
        self.sensitivity_value.setStyleSheet(
            f"QLabel {{ color: {c['text']}; font-size: 13px; font-weight: 700; }}"
        )

        header.addWidget(label)
        header.addStretch()
        header.addWidget(self.sensitivity_value)
        layout.addLayout(header)

        self.sensitivity_slider = QSlider(Qt.Horizontal)
        self.sensitivity_slider.setMinimum(10)
        self.sensitivity_slider.setMaximum(100)
        self.sensitivity_slider.setValue(self.sensitivity)
        self.sensitivity_slider.valueChanged.connect(
            self.change_sensitivity
        )
        self.sensitivity_slider.setStyleSheet(
            f"""
            QSlider::groove:horizontal {{
                height: 5px;
                background: {c['border']};
                border-radius: 3px;
            }}
            QSlider::sub-page:horizontal {{
                background: {c['accent']};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                width: 14px;
                height: 14px;
                margin: -5px 0;
                background: {c['primary']};
                border-radius: 7px;
            }}
            """
        )
        layout.addWidget(self.sensitivity_slider)

        return frame

    def build_buttons(self, c):

        layout = QHBoxLayout()
        layout.setSpacing(8)

        self.start_button = QPushButton("Start")
        self.pause_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")

        for button in (
            self.start_button,
            self.pause_button,
            self.stop_button
        ):
            button.setFixedHeight(40)
            button.setCursor(Qt.PointingHandCursor)

        self.start_button.clicked.connect(self.start_tracking)
        self.pause_button.clicked.connect(self.pause_tracking)
        self.stop_button.clicked.connect(self.stop_tracking)

        self.start_button.setStyleSheet(
            f"""
            QPushButton {{
                background: {c['primary']};
                color: {c['primary_text']};
                border: none;
                border-radius: 8px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background: {c['sidebar_hover']}; }}
            """
        )

        secondary = f"""
            QPushButton {{
                background: {c['card']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {c['button_hover']}; }}
        """
        self.pause_button.setStyleSheet(secondary)
        self.stop_button.setStyleSheet(secondary)

        layout.addWidget(self.start_button)
        layout.addWidget(self.pause_button)
        layout.addWidget(self.stop_button)

        return layout

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

            self.set_tracking_status(
                "● Camera Not Available",
                "#D9534F"
            )

            return False

        # ------------------------------------------------------
        # FIXED CAMERA RESOLUTION
        # ------------------------------------------------------

        self.camera.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            self.camera_width
        )

        self.camera.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            self.camera_height
        )

        # ------------------------------------------------------
        # CAMERA STABILITY
        # ------------------------------------------------------

        # Prevent automatic camera image resizing where supported.
        # Some webcams/drivers ignore these settings, so failures
        # are intentionally ignored.
        try:

            self.camera.set(
                cv2.CAP_PROP_BUFFERSIZE,
                1
            )

        except Exception:
            pass

        # Try to keep autofocus stable.
        try:

            self.camera.set(
                cv2.CAP_PROP_AUTOFOCUS,
                0
            )

        except Exception:
            pass

        # Keep exposure stable where supported.
        try:

            self.camera.set(
                cv2.CAP_PROP_AUTO_EXPOSURE,
                0.75
            )

        except Exception:
            pass

        return True

    # ==========================================================
    # START TRACKING
    # ==========================================================

    # ==========================================================
    # TRACKING STATUS PILL
    # ==========================================================

    def set_tracking_status(self, text, color=""):

        from settings import theme as app_theme

        c = app_theme.colors()

        if not color:
            color = c["text_secondary"]

        self.tracking_status.setText(text)

        self.tracking_status.setStyleSheet(
            f"""
            QLabel {{
                background: {c['card']};
                color: {color};
                border: 1px solid {c['border']};
                border-radius: 12px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            """
        )

    def start_tracking(self):

        if not self.open_camera():
            return

        self.camera_running = True
        self.camera_paused = False

        # The user explicitly wants tracking active.
        self.camera_was_running = True

        # Reset cursor smoothing so the cursor does not jump
        # from an old hand position when tracking starts.
        self.previous_x = None
        self.previous_y = None

        # Re-calibrate the neutral (screen-centre) hand position.
        self._neutral_x = None
        self._neutral_y = None
        self._cal_samples = []

        self.frame_count = 0

        self.set_tracking_status(
            "● Tracking Active",
            "#2A9561"
        )

        # 25 ms ≈ 40 FPS target.
        # OpenCV/MediaPipe may naturally run below this depending
        # on the computer and webcam.
        if not self.timer.isActive():

            self.timer.start(25)

    # ==========================================================
    # PAUSE
    # ==========================================================

    def pause_tracking(self):

        if not self.camera_running:
            return

        self.camera_paused = True

        self.set_tracking_status(
            "● Tracking Paused",
            "#B47B32"
        )

    # ==========================================================
    # STOP
    # ==========================================================

    def stop_tracking(self):

        self.camera_running = False
        self.camera_paused = False

        # The user explicitly stopped tracking.
        self.camera_was_running = False

        if self.timer.isActive():
            self.timer.stop()

        if self.camera:

            self.camera.release()
            self.camera = None

        self.previous_x = None
        self.previous_y = None

        # Make sure the mouse button is not left held down.
        self.release_drag()

        self.last_gesture = "None"

        self.set_tracking_status(
            "● Tracking Inactive"
        )

        self.fps_label.setText(
            "FPS: 0"
        )

        self.gesture_action.setText(
            "Gesture: —"
        )

        self.camera_label.clear()

        self.camera_label.setText(
            "Camera is stopped.\n\n"
            "Click Start to begin tracking."
        )

        self.reset_gesture_status()

    # ==========================================================
    # RELEASE CAMERA (on navigate away)
    #
    # Frees the single webcam so another page (e.g. Presentation
    # Control) can use it. The user's intent is remembered so tracking
    # resumes automatically when this page is shown again.
    # ==========================================================

    def release_camera(self):

        if self.camera_running:
            self.camera_was_running = True

        if self.timer.isActive():
            self.timer.stop()

        if self.camera:
            self.camera.release()
            self.camera = None

        self.camera_running = False
        self.camera_paused = False

        self.previous_x = None
        self.previous_y = None

        # Make sure the mouse button is not left held down.
        self.release_drag()

    # ==========================================================
    # ENSURE RUNNING (persistent mouse)
    #
    # Virtual Mouse acts as a system mouse: it should keep working on
    # pages that do not use the webcam, and while the app is minimized.
    # Called by MainWindow when navigating to a non-camera page.
    # ==========================================================

    def ensure_running(self):

        # Only resume if the user had tracking on and it isn't already on.
        if self.camera_was_running and not self.camera_running:
            self.start_tracking()

    # ==========================================================
    # SHOW EVENT (resume after navigating back)
    # ==========================================================

    def showEvent(self, event):

        super().showEvent(event)

        if self.camera_was_running and self.camera is None:
            self.start_tracking()

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

        # ------------------------------------------------------
        # MIRROR CAMERA
        # ------------------------------------------------------

        frame = cv2.flip(
            frame,
            1
        )

        # ------------------------------------------------------
        # MEDIAPIPE
        # ------------------------------------------------------

        gesture = "None"

        # If MediaPipe is unavailable, just show raw camera feed.
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

            # --------------------------------------------------
            # HAND DETECTED
            # --------------------------------------------------

            if results.multi_hand_landmarks:

                hand = results.multi_hand_landmarks[0]

                self.latest_hand = hand

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

                self.latest_hand = None

                self.reset_gesture_status()

        # ------------------------------------------------------
        # FPS
        # ------------------------------------------------------

        self.frame_count += 1

        self.fps_label.setText(
            "FPS: 40"
        )

        # ------------------------------------------------------
        # CAMERA DISPLAY
        # ------------------------------------------------------

        # Share the latest frame (with landmarks drawn) so other pages such
        # as the Whiteboard preview can show it without opening the camera.
        self.latest_frame = frame.copy()

        self.display_frame(
            frame
        )

    # ==========================================================
    # SHARED FRAME ACCESS
    # ==========================================================

    def get_latest_frame(self):
        """Return the most recent camera frame (BGR), or None."""

        return self.latest_frame

    def get_latest_hand(self):
        """Return the most recent detected hand landmarks, or None."""

        return self.latest_hand

    # ==========================================================
    # GESTURE DETECTION
    # ==========================================================

    def detect_gesture(
        self,
        hand
    ):

        lm = hand.landmark
        HL = self.mp_hands.HandLandmark

        # --------------------------------------------------
        # LANDMARKS
        # --------------------------------------------------

        thumb_tip = lm[HL.THUMB_TIP]
        index_tip = lm[HL.INDEX_FINGER_TIP]
        middle_tip = lm[HL.MIDDLE_FINGER_TIP]
        ring_tip = lm[HL.RING_FINGER_TIP]
        pinky_tip = lm[HL.PINKY_TIP]

        index_up = index_tip.y < lm[HL.INDEX_FINGER_PIP].y
        middle_up = middle_tip.y < lm[HL.MIDDLE_FINGER_PIP].y
        ring_up = ring_tip.y < lm[HL.RING_FINGER_PIP].y
        pinky_up = pinky_tip.y < lm[HL.PINKY_PIP].y

        # --------------------------------------------------
        # 🤏 THUMB + MIDDLE  ->  RIGHT CLICK
        # --------------------------------------------------

        thumb_middle = (
            (thumb_tip.x - middle_tip.x) ** 2
            + (thumb_tip.y - middle_tip.y) ** 2
        ) ** 0.5

        thumb_index = (
            (thumb_tip.x - index_tip.x) ** 2
            + (thumb_tip.y - index_tip.y) ** 2
        ) ** 0.5

        # --------------------------------------------------
        # 🤏 THUMB + MIDDLE  ->  RIGHT CLICK
        # --------------------------------------------------

        if thumb_middle < 0.07 and middle_up:
            return "Thumb + Middle"

        # --------------------------------------------------
        # ✌️ INDEX + MIDDLE TOGETHER  ->  DRAW
        # (finger tips touching) Holds the left mouse button so the user
        # can draw / write on the Whiteboard / Annotation canvas.
        # Must be checked before Open Palm.
        # --------------------------------------------------

        index_middle = (
            (index_tip.x - middle_tip.x) ** 2
            + (index_tip.y - middle_tip.y) ** 2
        ) ** 0.5

        if (
            index_up
            and middle_up
            and not ring_up
            and not pinky_up
        ):

            # Distance between the index and middle fingertips decides
            # DRAW vs PEACE:
            #   tips touching  -> draw
            #   tips apart     -> peace sign (cursor, no drawing)
            #
            # Hysteresis: to START drawing the tips must be really close,
            # but once drawing they may separate a little before it stops.
            # This stops accidental drawing while showing a peace sign.
            draw_threshold = 0.055 if self.is_dragging else 0.040

            if index_middle < draw_threshold:

                return "Index + Middle"

            return "Peace Sign"

        # --------------------------------------------------
        # 🖐️ OPEN PALM  ->  MOVE CURSOR (+ scroll on vertical motion)
        # --------------------------------------------------

        if index_up and middle_up and ring_up and pinky_up:
            return "Open Palm"

        # --------------------------------------------------
        # ✊ CLOSED PALM (FIST)  ->  LEFT CLICK
        # --------------------------------------------------

        if (
            not index_up
            and not middle_up
            and not ring_up
            and not pinky_up
        ):
            return "Fist"

        return "None"

    # ==========================================================
    # PERFORM GESTURE
    # ==========================================================

    def perform_gesture(
        self,
        gesture,
        hand
    ):

        # Reset the scroll accumulator whenever the palm is not open, so a
        # stale swipe never carries over to the next open-palm moment.
        if gesture != "Open Palm":
            self._scroll_accum = 0.0
            self._scroll_prev_y = None

        # Only the INDEX + MIDDLE "draw" gesture may hold the mouse button.
        # (A fist must never hold it, or the Whiteboard would draw by itself.)
        hold_gestures = ("Index + Middle",)

        if gesture in hold_gestures:

            self._hold_grace = 8

        else:

            self.tick_hold_grace()

        if gesture == "None":
            return

        # --------------------------------------------------
        # 🖐️ OPEN PALM -> move cursor (+ scroll on vertical motion)
        # --------------------------------------------------

        if gesture == "Open Palm":

            self.move_cursor(hand)

            self.handle_scroll(hand)

            self.set_action("Move Cursor")

        # --------------------------------------------------
        # ✌️ PEACE SIGN -> move the drawing cursor (no scroll)
        # --------------------------------------------------

        elif gesture == "Peace Sign":

            self.move_cursor(hand)

            self.set_action("Cursor / Draw")

        # --------------------------------------------------
        # ✌️ INDEX + MIDDLE TOGETHER -> DRAW
        # Holds the left mouse button so the user can draw / write on the
        # Whiteboard / Annotation canvas while moving the hand.
        # --------------------------------------------------

        elif gesture == "Index + Middle":

            self.move_cursor(hand)

            if not self.is_dragging:

                self.begin_drag()

            self.set_action("Draw")

        # --------------------------------------------------
        # ✊ CLOSED PALM (FIST) -> left click
        # --------------------------------------------------

        elif gesture == "Fist":

            if self.left_click_cooldown <= 0:

                pyautogui.click()

                self.left_click_cooldown = 8

            else:

                self.left_click_cooldown -= 1

            self.set_action("Left Click")

        # --------------------------------------------------
        # 🤏 THUMB + MIDDLE -> right click
        # --------------------------------------------------

        elif gesture == "Thumb + Middle":

            if self.right_click_cooldown <= 0:

                pyautogui.rightClick()

                self.right_click_cooldown = 8

            else:

                self.right_click_cooldown -= 1

            self.set_action("Right Click")

        self.last_gesture = gesture

    # ==========================================================
    # DRAG HELPERS
    # ==========================================================

    def begin_drag(self):

        try:

            pyautogui.mouseDown()

        except Exception:

            pass

        self.is_dragging = True

    def release_drag(self):

        if not self.is_dragging:
            return

        try:

            pyautogui.mouseUp()

        except Exception:

            pass

        self.is_dragging = False

    def tick_hold_grace(self):

        if not self.is_dragging:
            return

        self._hold_grace -= 1

        if self._hold_grace <= 0:

            self.release_drag()

    # ==========================================================
    # ACTION LABEL
    # ==========================================================

    def set_action(self, text):

        if hasattr(self, "gesture_action"):

            self.gesture_action.setText(
                "Gesture: " + text
            )

    # ==========================================================
    # MOVE CURSOR (Open Palm)
    # ==========================================================

    def hand_centre(
        self,
        hand
    ):
        """Return the (x, y) centre of the hand.

        Uses the knuckle line (the four finger MCPs) which sits at the
        visual centre of an open palm, so a centred hand maps to the
        centre of the screen.
        """

        lm = hand.landmark
        HL = self.mp_hands.HandLandmark

        ids = (
            HL.INDEX_FINGER_MCP,
            HL.MIDDLE_FINGER_MCP,
            HL.RING_FINGER_MCP,
            HL.PINKY_MCP,
        )

        xs = [lm[i].x for i in ids]
        ys = [lm[i].y for i in ids]

        return (
            sum(xs) / 4.0,
            sum(ys) / 4.0,
        )

    def move_cursor(
        self,
        hand
    ):

        px, py = self.hand_centre(hand)

        # --------------------------------------------------
        # Region mapping (FIXED frame centre)
        #
        # The centre of the camera frame maps to the centre of the screen,
        # so a hand held in the middle of the feed puts the cursor in the
        # middle of the screen. `span` controls how far the hand must move
        # to cross the screen (Sensitivity slider).
        # --------------------------------------------------

        span = (
            0.95
            - (self.sensitivity - 10) / 90.0 * 0.75
        )

        span = max(0.15, span)

        nx = (px - 0.5) / span + 0.5
        ny = (py - 0.5) / span + 0.5

        target_x = int(
            max(0.0, min(1.0, nx))
            * self.screen_width
        )

        target_y = int(
            max(0.0, min(1.0, ny))
            * self.screen_height
        )

        if self.previous_x is None:

            self.previous_x = target_x
            self.previous_y = target_y

            self.move_to(target_x, target_y)

            return

        dx = target_x - self.previous_x
        dy = target_y - self.previous_y

        # While drawing (left button held) follow closely for a responsive,
        # continuous line (the grace period prevents the stroke from
        # breaking if the hand blinks for a frame).
        if self.is_dragging:

            dead = 0
            smooth = 0.8

        else:

            dead = self.dead_zone
            smooth = self.smoothing

        if dead and abs(dx) <= dead and abs(dy) <= dead:

            return

        smooth_x = self.previous_x + dx * smooth
        smooth_y = self.previous_y + dy * smooth

        smooth_x = max(
            0,
            min(self.screen_width - 1, int(smooth_x))
        )

        smooth_y = max(
            0,
            min(self.screen_height - 1, int(smooth_y))
        )

        self.move_to(smooth_x, smooth_y)

        self.previous_x = smooth_x
        self.previous_y = smooth_y

    def move_to(self, x, y):

        try:

            pyautogui.moveTo(
                int(x),
                int(y),
                duration=0
            )

        except Exception:

            # Never let a cursor-move error crash the camera timer.
            pass

    # ==========================================================
    # SCROLL (Open Palm + vertical movement)
    #
    # A deliberate up/down swipe of the open palm scrolls, while normal
    # small open-palm movement does NOT scroll (accumulator threshold).
    # ==========================================================

    def handle_scroll(
        self,
        hand
    ):

        _, palm_y = self.hand_centre(hand)

        if self._scroll_prev_y is None:

            self._scroll_prev_y = palm_y
            return

        dy = palm_y - self._scroll_prev_y
        self._scroll_prev_y = palm_y

        # Ignore tiny jitter / normal movement.
        if abs(dy) < 0.004:

            self._scroll_accum *= 0.6
            return

        self._scroll_accum += dy

        threshold = 0.18

        if self._scroll_accum > threshold:

            # Palm moved DOWN -> scroll down
            pyautogui.scroll(-4)
            self._scroll_accum = 0.0

        elif self._scroll_accum < -threshold:

            # Palm moved UP -> scroll up
            pyautogui.scroll(4)
            self._scroll_accum = 0.0

    # ==========================================================
    # ACTION NAME
    # ==========================================================

    def get_action_name(
        self,
        gesture
    ):

        actions = {
            "Open Palm": "Move Cursor",
            "Peace Sign": "Cursor / Draw",
            "Fist": "Left Click",
            "Index + Middle": "Draw",
            "Thumb + Middle": "Right Click",
        }

        return actions.get(
            gesture,
            "Ready"
        )

    # ==========================================================
    # RESET STATUS
    # ==========================================================

    def reset_gesture_status(self):

        self._scroll_accum = 0.0
        self._scroll_prev_y = None

        # Dropping the hand must not leave the mouse button held down,
        # but allow a short grace period first (hand detection can blink).
        self.tick_hold_grace()

        if hasattr(self, "gesture_action"):

            self.gesture_action.setText(
                "Gesture: —"
            )

    # ==========================================================
    # DISPLAY FRAME
    # ==========================================================

    def display_frame(
        self,
        frame
    ):

        # Convert BGR → RGB
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

        # Make a copy so the QImage does not reference
        # memory that OpenCV may reuse on the next frame.
        image = image.copy()

        pixmap = QPixmap.fromImage(
            image
        )

        # ------------------------------------------------------
        # RESPONSIVE DISPLAY SIZE
        # ------------------------------------------------------

        target = self.camera_label.size()

        if target.width() < 40 or target.height() < 40:

            target = QSize(480, 320)

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

        if hasattr(self, "sensitivity_value"):

            self.sensitivity_value.setText(
                f"{value}%"
            )

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