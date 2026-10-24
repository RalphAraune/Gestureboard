import math
import sys
import threading
import time
from collections import deque

import cv2
import pyautogui

# MediaPipe may fail to load its DLL on some Python setups. Make it optional.
try:
    import mediapipe as mp
except Exception as e:
    print("MediaPipe import error:", e)
    mp = None

from PyQt5.QtCore import (
    Qt, QSize, QRectF, QPointF, QObject, pyqtSignal
)
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QSlider,
    QSizePolicy,
    QSplitter,
    QSplitterHandle,
    QScrollArea,
)


# ==============================================================
# NATIVE MOUSE INPUT (Windows)
#
# pyautogui.click() sends button-down and button-up in ONE
# mouse_event call with zero time between them and silently
# swallows errors, so many apps never register the click.
# Sending a real press, a short hold, then a release is reliable.
# ==============================================================

if sys.platform == "win32":

    import ctypes

    _user32 = ctypes.windll.user32

    _MOUSE_FLAGS = {
        "left": (0x0002, 0x0004),   # LEFTDOWN, LEFTUP
        "right": (0x0008, 0x0010),  # RIGHTDOWN, RIGHTUP
    }

    _MOUSEEVENTF_WHEEL = 0x0800

else:

    _user32 = None


def native_click(x=None, y=None, button="left"):
    """Press and release a mouse button, optionally at (x, y)."""

    if _user32 is None:

        if x is not None:
            pyautogui.moveTo(int(x), int(y), duration=0)

        pyautogui.mouseDown(button=button)
        time.sleep(0.03)
        pyautogui.mouseUp(button=button)

        return

    down, up = _MOUSE_FLAGS[button]

    if x is not None:
        _user32.SetCursorPos(int(x), int(y))

    _user32.mouse_event(down, 0, 0, 0, 0)
    time.sleep(0.03)
    _user32.mouse_event(up, 0, 0, 0, 0)


def native_scroll(clicks):
    """Scroll the window under the cursor (positive = up)."""

    if _user32 is None:

        pyautogui.scroll(int(clicks))

        return

    _user32.mouse_event(
        _MOUSEEVENTF_WHEEL, 0, 0, int(clicks * 120), 0
    )


def native_move(x, y):
    """Move the cursor instantly.

    pyautogui.moveTo() sleeps for pyautogui.PAUSE after every call,
    which on its own adds a visible delay to every camera frame.
    """

    if _user32 is None:

        pyautogui.moveTo(int(x), int(y), duration=0, _pause=False)

        return

    _user32.SetCursorPos(int(x), int(y))


# ==============================================================
# GESTURES
#
# One table drives the detector, the action label and the guide,
# so the guide always matches what the mouse actually does.
# ==============================================================

GESTURE_GUIDE = (
    # key,          icon,  name,                    action
    ("move",        "🖐️", "Open palm",              "Move the cursor"),
    ("left",        "✊",  "Close your hand",        "Left click"),
    ("right",       "🤏",  "Touch thumb and index",  "Right click"),
    ("scroll_up",   "↑",  "Hold cursor top-centre",  "Scroll up after 1 s"),
    ("scroll_down", "↓",  "Hold cursor bottom-centre", "Scroll down after 1 s"),
)

# Seconds the cursor must stay inside a scroll zone before scrolling.
SCROLL_DWELL_SECONDS = 1.0

# Seconds between scroll steps once scrolling has started.
SCROLL_REPEAT_SECONDS = 0.12

# Scroll zones as fractions of the screen: the middle 40% horizontally,
# and the top / bottom 18% vertically.
ZONE_X = (0.30, 0.70)
ZONE_TOP = 0.18
ZONE_BOTTOM = 0.82


# ==============================================================
# STATUS COLOURS (per theme)
# ==============================================================

STATE_COLORS = {
    "Light": {
        "live": "#24855A",
        "paused": "#A06A22",
        "error": "#C2413B",
    },
    "Dark": {
        "live": "#4CC38A",
        "paused": "#E0A458",
        "error": "#F07470",
    },
}

# Warm amber for the Start / Pause / Stop button that is in use.
# It is the complement of the navy / blue buttons around it.
BUTTON_ACTIVE = {
    "Light": "#D9822B",
    "Dark": "#F2A65A",
}


# ==============================================================
# PAGE PALETTE
#
# Shared soft-blue page surfaces (same as Saved Files), plus a
# slightly deeper "well" for the empty camera area.
# ==============================================================

def page_colors():
    """Shared page surfaces with this page's camera well."""

    from settings import theme as app_theme
    from widgets import page_background

    c = page_background.page_colors()
    c["well"] = c["bg"] if app_theme.is_dark() else "#CFDFF0"

    return c


# ==============================================================
# RESIZE HANDLE
#
# The divider between the camera and the side panel. It draws a
# visible grip so it is obvious the camera can be resized.
# ==============================================================

class GripHandle(QSplitterHandle):

    def __init__(self, orientation, parent):

        super().__init__(orientation, parent)

        self.grip_color = QColor("#8FA3C4")
        self.hover_color = QColor("#0E2F76")
        self._hover = False

        self.setToolTip("Drag to resize the camera. Double-click to reset.")

    def enterEvent(self, event):

        self._hover = True
        self.update()

        super().enterEvent(event)

    def leaveEvent(self, event):

        self._hover = False
        self.update()

        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event):

        page = self.splitter().parent()

        if hasattr(page, "reset_splitter"):
            page.reset_splitter()

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(
            self.hover_color if self._hover else self.grip_color
        )

        cx = self.width() / 2.0
        cy = self.height() / 2.0

        # A short rounded bar along the handle
        if self.orientation() == Qt.Horizontal:
            bar = QRectF(cx - 2, cy - 22, 4, 44)
        else:
            bar = QRectF(cx - 22, cy - 2, 44, 4)

        painter.drawRoundedRect(bar, 2, 2)

        painter.end()


class GripSplitter(QSplitter):

    def createHandle(self):

        return GripHandle(self.orientation(), self)


class EdgeTrigger:
    """Fires once when a gesture has been held for `hold` frames.

    It re-arms only after the gesture has been gone for `release`
    frames, so one flickering frame never causes a double click.
    """

    def __init__(self, hold=2, release=3):

        self.hold = hold
        self.release = release

        self.on_frames = 0
        self.off_frames = 0
        self.fired = False

    def update(self, active):

        if active:

            self.on_frames += 1
            self.off_frames = 0

            if self.on_frames >= self.hold and not self.fired:

                self.fired = True

                return True

        else:

            self.on_frames = 0
            self.off_frames += 1

            if self.off_frames >= self.release:
                self.fired = False

        return False


# ==============================================================
# ONE EURO FILTER
#
# Adaptive smoothing (Casiez et al. 2012): heavy smoothing while the
# hand is almost still (no jitter), almost none while it moves fast
# (no lag). A fixed exponential filter can only trade one for the other.
# ==============================================================

class OneEuroFilter:

    def __init__(self, min_cutoff=1.0, beta=0.01, d_cutoff=1.0):

        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff

        self.reset()

    def reset(self):

        self.x = None
        self.dx = 0.0
        self.t = None

    @staticmethod
    def _alpha(cutoff, dt):

        tau = 1.0 / (2.0 * math.pi * cutoff)

        return 1.0 / (1.0 + tau / dt)

    def __call__(self, value, t):

        # self.t is None when x was snapped (after a click) with no
        # earlier sample, so there is no time step to filter over yet.
        if self.x is None or self.t is None:

            self.x = value
            self.t = t

            return value

        dt = max(1e-3, t - self.t)
        self.t = t

        dx = (value - self.x) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        self.dx = self.dx + a_d * (dx - self.dx)

        cutoff = self.min_cutoff + self.beta * abs(self.dx)
        a = self._alpha(cutoff, dt)
        self.x = self.x + a * (value - self.x)

        return self.x


# ==============================================================
# HAND CHECKS
#
# MediaPipe sometimes "finds" a hand in a face, a sleeve, a mug or
# a patterned background. A detection is only used when:
#   * MediaPipe is confident it is a hand (HAND_MIN_SCORE),
#   * its 21 points have the proportions of a real hand, and
#   * it passes for HAND_CONFIRM_FRAMES frames in a row, so a
#     one-frame false detection can never move or click.
# ==============================================================

# MediaPipe's confidence that the detection is a hand (0..1). Real
# hands sit well above this; most false detections fall below it.
HAND_MIN_SCORE = 0.8

# Frames in a row a NEW hand must pass every check before it is used
# (2 frames is about 0.07 s at 30 fps). A hand already being tracked
# is checked every frame but needs no new confirmation.
HAND_CONFIRM_FRAMES = 2

# Smallest palm (wrist -> middle knuckle) accepted, as a fraction of
# the frame. Tiny "hands" are almost always background noise.
HAND_MIN_PALM = 0.04

# Landmark indexes (MediaPipe hand model).
_WRIST = 0
_THUMB = (1, 2, 3, 4)
_FINGERS = (
    (5, 6, 7, 8),       # index:  knuckle, middle joint, end joint, tip
    (9, 10, 11, 12),    # middle
    (13, 14, 15, 16),   # ring
    (17, 18, 19, 20),   # pinky
)


def _gap(a, b):

    return math.hypot(a.x - b.x, a.y - b.y)


def looks_like_hand(landmarks):
    """Return True when the 21 points have real hand proportions.

    Every length is compared with the palm (wrist -> middle knuckle),
    so the test works at any distance from the camera. The limits
    are wide enough for any pose a user makes, including a fist, a
    pinch and a hand turned sideways, but a face, a shirt pattern or
    an object rarely fits all of them at once.
    """

    lm = landmarks

    wrist = lm[_WRIST]

    palm = _gap(wrist, lm[9])

    if palm < HAND_MIN_PALM:
        return False

    # The palm is rigid: wrist -> each knuckle is about one palm long
    # (pinky a little shorter), whatever the fingers are doing.
    for finger in _FINGERS:

        ratio = _gap(wrist, lm[finger[0]]) / palm

        if not 0.45 <= ratio <= 1.6:
            return False

    # Knuckles sit side by side across the palm, in order, evenly
    # spaced. Turned sideways the row narrows, so only an upper limit
    # applies to its width.
    knuckles = [lm[finger[0]] for finger in _FINGERS]

    width = _gap(knuckles[0], knuckles[3]) / palm

    if width > 1.4:
        return False

    steps = [_gap(knuckles[i], knuckles[i + 1]) for i in range(3)]

    if max(steps) > 0.8 * palm:
        return False

    if sum(steps) > 0 and max(steps) > 0.85 * sum(steps):
        return False

    # Finger bones: about half a palm each, so none is much longer
    # than the palm and a whole finger is under about 2.5 palms, even
    # when the palm is tilted away and looks short. (Pointing at the
    # camera makes bones look very short, so there is no lower limit.)
    for finger in _FINGERS + (_THUMB,):

        bones = [
            _gap(lm[finger[i]], lm[finger[i + 1]]) / palm
            for i in range(3)
        ]

        if max(bones) > 1.3 or sum(bones) > 2.6:
            return False

    # Thumb base sits near the wrist, not out past the fingers.
    if _gap(wrist, lm[_THUMB[0]]) / palm > 0.9:
        return False

    return True


def hand_score(results):
    """MediaPipe's confidence for the first hand, or 1.0 if unknown."""

    try:
        return results.multi_handedness[0].classification[0].score
    except (AttributeError, IndexError, TypeError):
        return 1.0


# ==============================================================
# CAMERA WORKER
#
# Two background threads keep the UI thread free:
#   * the grabber reads the webcam as fast as it delivers, keeping
#     only the newest frame, so the driver never queues stale ones;
#   * the detector runs MediaPipe on the newest frame and hands the
#     result to the UI thread.
# Results are dropped (not queued) while the UI is still busy with
# the previous one, so the cursor always follows the current hand.
# ==============================================================

class _Bridge(QObject):

    ready = pyqtSignal()


class CameraWorker:

    def __init__(self, camera, hands, mp_hands, mp_drawing):

        self.camera = camera
        self.hands = hands
        self.mp_hands = mp_hands
        self.mp_drawing = mp_drawing

        self.bridge = _Bridge()
        self.ready = self.bridge.ready

        self.paused = False

        self._stop = threading.Event()
        self._new_frame = threading.Condition()

        self._frame = None
        self._frame_time = 0.0
        self._frame_seq = 0

        self._result_lock = threading.Lock()
        self._result = None
        self._pending = False

        # Frames in a row that passed the hand checks.
        self._hand_streak = 0

        self._threads = [
            threading.Thread(target=self._grab_loop, daemon=True),
            threading.Thread(target=self._detect_loop, daemon=True),
        ]

    def start(self):

        for thread in self._threads:
            thread.start()

    def stop(self):

        self._stop.set()

        with self._new_frame:
            self._new_frame.notify_all()

        for thread in self._threads:
            thread.join(timeout=1.0)

    def take(self):
        """Return the newest (frame, hand, time) result, or None."""

        with self._result_lock:

            result = self._result
            self._result = None
            self._pending = False

        return result

    def _checked_hand(self, results):
        """Return the detected hand if it passes every check, else None."""

        hand = None

        if results is not None and results.multi_hand_landmarks:

            candidate = results.multi_hand_landmarks[0]

            if (
                hand_score(results) >= HAND_MIN_SCORE
                and looks_like_hand(candidate.landmark)
            ):
                hand = candidate

        if hand is None:

            self._hand_streak = 0

            return None

        self._hand_streak += 1

        # A new hand waits until it has passed several frames in a
        # row; after that it is used on every frame that passes.
        if self._hand_streak < HAND_CONFIRM_FRAMES:
            return None

        return hand

    def _grab_loop(self):

        while not self._stop.is_set():

            ok, frame = self.camera.read()

            if not ok:
                time.sleep(0.01)
                continue

            with self._new_frame:

                self._frame = frame
                self._frame_time = time.monotonic()
                self._frame_seq += 1

                self._new_frame.notify()

    def _detect_loop(self):

        seen = 0

        while not self._stop.is_set():

            with self._new_frame:

                while self._frame_seq == seen and not self._stop.is_set():
                    self._new_frame.wait(0.2)

                if self._stop.is_set():
                    return

                frame = self._frame
                stamp = self._frame_time
                seen = self._frame_seq

            if self.paused:
                continue

            frame = cv2.flip(frame, 1)

            hand = None

            if self.hands is not None:

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                rgb.flags.writeable = False

                try:
                    results = self.hands.process(rgb)
                except Exception as exc:
                    print("Virtual mouse: hand tracking failed:", exc)
                    results = None

                hand = self._checked_hand(results)

                # Only a real, confirmed hand gets its skeleton drawn,
                # so the feed shows exactly what the mouse responds to.
                if hand is not None:

                    self.mp_drawing.draw_landmarks(
                        frame,
                        hand,
                        self.mp_hands.HAND_CONNECTIONS
                    )

            with self._result_lock:

                self._result = (frame, hand, stamp)

                notify = not self._pending
                self._pending = True

            if notify:
                self.ready.emit()


# ==============================================================
# SCREEN MAP
#
# A miniature of the screen showing the cursor and the two scroll
# zones. The active zone fills up while the 1 second hold counts down.
# ==============================================================

class ScreenMap(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.cursor = None          # (fx, fy) in 0..1, or None
        self.zone = None            # "up", "down" or None
        self.progress = 0.0         # 0..1 dwell progress
        self.scrolling = False

        self.colors = {}

        self.setMinimumHeight(120)
        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred
        )

    def sizeHint(self):

        return QSize(260, 150)

    def set_colors(self, c):

        self.colors = c
        self.update()

    def set_state(self, cursor, zone, progress, scrolling):

        state = (cursor, zone, round(progress, 2), scrolling)

        if state == (
            self.cursor, self.zone, round(self.progress, 2), self.scrolling
        ):
            return

        self.cursor = cursor
        self.zone = zone
        self.progress = progress
        self.scrolling = scrolling

        self.update()

    def paintEvent(self, event):

        c = self.colors

        if not c:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Keep the screen's aspect ratio inside the widget.
        aspect = 16 / 9

        try:
            w, h = pyautogui.size()
            aspect = w / float(h)
        except Exception:
            pass

        avail_w = self.width() - 2
        avail_h = self.height() - 2

        width = min(avail_w, avail_h * aspect)
        height = width / aspect

        screen = QRectF(
            (self.width() - width) / 2,
            (self.height() - height) / 2,
            width,
            height
        )

        # Screen outline
        painter.setPen(QPen(QColor(c["border"]), 1.5))
        painter.setBrush(QColor(c["bg"]))
        painter.drawRoundedRect(screen, 6, 6)

        # Scroll zones
        zone_w = screen.width() * (ZONE_X[1] - ZONE_X[0])
        zone_h = screen.height() * ZONE_TOP
        zone_x = screen.left() + screen.width() * ZONE_X[0]

        zones = {
            "up": QRectF(zone_x, screen.top() + 3, zone_w, zone_h - 3),
            "down": QRectF(
                zone_x,
                screen.top() + screen.height() * ZONE_BOTTOM,
                zone_w,
                zone_h - 3
            ),
        }

        primary = QColor(c["primary"])

        for key, rect in zones.items():

            painter.setPen(QPen(QColor(c["border"]), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, 4, 4)

            if key == self.zone and self.progress > 0:

                fill = QRectF(rect)
                fill.setWidth(rect.width() * min(1.0, self.progress))

                tint = QColor(primary)
                tint.setAlpha(230 if self.scrolling else 120)

                painter.setPen(Qt.NoPen)
                painter.setBrush(tint)
                painter.drawRoundedRect(fill, 4, 4)

            painter.setPen(QColor(c["text_secondary"]))

            label = "Scroll up" if key == "up" else "Scroll down"

            if key == self.zone and self.scrolling:
                label = "Scrolling up" if key == "up" else "Scrolling down"
                painter.setPen(QColor(c["primary_text"]))

            font = painter.font()
            font.setPointSizeF(8)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignCenter, label)

        # Cursor
        if self.cursor is not None:

            fx, fy = self.cursor

            point = QPointF(
                screen.left() + fx * screen.width(),
                screen.top() + fy * screen.height()
            )

            painter.setPen(QPen(QColor(c["card"]), 2))
            painter.setBrush(primary)
            painter.drawEllipse(point, 5, 5)

        painter.end()


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

            # A little stricter than before: a weak guess is not acted
            # on. Tracking confidence decides when a tracked "hand" is
            # dropped and searched for again, so it is the higher one:
            # a false lock does not linger. (Detection above about 0.6
            # starts missing real hands, e.g. a thumbs-up.) More
            # checks: HAND CHECKS.
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                model_complexity=0,
                min_detection_confidence=0.6,
                min_tracking_confidence=0.7,
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

        # Adaptive cursor smoothing: steady when the hand is still,
        # responsive when it moves (see OneEuroFilter).
        self.filter_x = OneEuroFilter(min_cutoff=0.8, beta=0.015)
        self.filter_y = OneEuroFilter(min_cutoff=0.8, beta=0.015)

        self.last_gesture = "None"

        # Fist -> left click, Pinch -> right click. Each clicks ONCE per
        # gesture; the hand must open again before the next click.
        self.left_trigger = EdgeTrigger()
        self.right_trigger = EdgeTrigger()

        # Recent cursor positions (time, x, y). Closing the hand shifts the
        # knuckles, which drags the cursor off the target just before the
        # gesture is recognised, so clicks go to where the cursor was
        # a moment BEFORE the hand started closing.
        self._cursor_history = deque(maxlen=60)

        # Frames left to show the click flash on the camera feed.
        self._click_flash = 0
        self._click_text = ""

        # Scroll zone dwell state
        self._dwell_zone = None
        self._dwell_start = 0.0
        self._last_scroll = 0.0

        # ======================================================
        # FPS
        # ======================================================

        self.frame_count = 0
        self._frame_times = deque(maxlen=30)

        # ======================================================
        # CAMERA WORKER (background capture + hand detection)
        # ======================================================

        self.worker = None

        # ======================================================
        # BUILD UI
        # ======================================================

        self._theme_name = None
        self._status_state = "off"

        self.build_ui()

        from widgets import page_background

        page_background.clear_layers(self)

        self.apply_theme()

    # ==========================================================
    # UI
    # ==========================================================

    def build_ui(self):

        self.setObjectName("vmPage")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 24, 32, 24)
        main_layout.setSpacing(18)

        # --------------------------------------------------
        # HEADER: title on the left, tracking controls on the right
        # --------------------------------------------------

        header = QHBoxLayout()
        header.setSpacing(12)

        titles = QVBoxLayout()
        titles.setSpacing(2)

        title = QLabel("Virtual mouse")
        title.setObjectName("vmTitle")

        subtitle = QLabel(
            "Control the cursor with your hand in front of the camera."
        )
        subtitle.setObjectName("vmSubtitle")
        subtitle.setWordWrap(True)

        titles.addWidget(title)
        titles.addWidget(subtitle)

        header.addLayout(titles, 1)

        main_layout.addLayout(header)

        # --------------------------------------------------
        # BODY: camera | panel, resizable with a splitter
        # --------------------------------------------------

        self.splitter = GripSplitter(Qt.Horizontal, self)
        self.splitter.setObjectName("vmSplitter")
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(12)

        self.splitter.addWidget(self.build_camera_panel())
        self.splitter.addWidget(self.build_side_panel())

        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)

        main_layout.addWidget(self.splitter, 1)

        self.reset_splitter()

    def reset_splitter(self):
        """Give the camera about 70% of the space (horizontal) or 60%
        (stacked), whatever the current page size is."""

        horizontal = self.splitter.orientation() == Qt.Horizontal

        total = (
            self.splitter.width() if horizontal
            else self.splitter.height()
        )

        total = max(total, 600)

        share = 0.70 if horizontal else 0.60

        self.splitter.setSizes([
            int(total * share),
            int(total * (1 - share)),
        ])

    def build_camera_panel(self):

        frame = QFrame()
        frame.setObjectName("vmFeed")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(10)

        self.camera_label = QLabel()
        self.camera_label.setObjectName("vmCamera")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumSize(260, 195)

        # "Ignored" lets the label shrink below the pixmap size, so the
        # feed follows the splitter / window size in both directions.
        self.camera_label.setSizePolicy(
            QSizePolicy.Ignored,
            QSizePolicy.Ignored
        )

        self.camera_label.setText(
            "Camera is off.\nPress Start to begin tracking."
        )

        layout.addWidget(self.camera_label, 1)

        # Status strip under the feed
        status_row = QHBoxLayout()
        status_row.setSpacing(16)

        self.tracking_status = QLabel("Tracking off")
        self.tracking_status.setObjectName("vmStatus")

        self.gesture_action = QLabel("No hand detected")
        self.gesture_action.setObjectName("vmMeta")

        self.fps_label = QLabel("0 fps")
        self.fps_label.setObjectName("vmMeta")

        status_row.addWidget(self.tracking_status)
        status_row.addWidget(self.gesture_action)
        status_row.addStretch()
        status_row.addWidget(self.fps_label)

        layout.addLayout(status_row)

        return frame

    def build_side_panel(self):

        panel = QFrame()
        panel.setObjectName("vmPanel")
        panel.setMinimumWidth(300)

        outer = QVBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # --------------------------------------------------
        # Scrollable part: gestures and scroll zones
        # (scrolls only when the window is too short)
        # --------------------------------------------------

        content = QWidget()
        content.setObjectName("vmPanelContent")

        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 16, 18, 8)
        layout.setSpacing(6)

        # Gestures (the active one lights up live)
        layout.addWidget(self.make_section("Gestures"))

        self.guide_rows = {}

        for key, icon, name, action in GESTURE_GUIDE:

            row = self.make_guide_row(icon, name, action)

            self.guide_rows[key] = row

            layout.addWidget(row)

        layout.addSpacing(10)

        # Scroll zones
        layout.addWidget(self.make_section("Scroll zones"))

        hint = QLabel(
            "Hold the cursor still in a zone for 1 second to scroll. "
            "Move out of the zone to stop."
        )
        hint.setObjectName("vmHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.screen_map = ScreenMap()
        self.screen_map.setMinimumHeight(96)
        self.screen_map.setMaximumHeight(130)
        layout.addWidget(self.screen_map)

        layout.addStretch()

        scroll = QScrollArea()
        scroll.setObjectName("vmPanelScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(content)

        outer.addWidget(scroll, 1)

        # --------------------------------------------------
        # Pinned footer: sensitivity, then Start / Pause / Stop.
        # Always visible, whatever the window height.
        # --------------------------------------------------

        footer = QWidget()
        footer.setObjectName("vmPanelFooter")

        foot = QVBoxLayout(footer)
        foot.setContentsMargins(18, 12, 18, 16)
        foot.setSpacing(8)

        header = QHBoxLayout()

        header.addWidget(self.make_section("Cursor sensitivity"))
        header.addStretch()

        self.sensitivity_value = QLabel(f"{self.sensitivity}%")
        self.sensitivity_value.setObjectName("vmValue")
        header.addWidget(self.sensitivity_value)

        foot.addLayout(header)

        self.sensitivity_slider = QSlider(Qt.Horizontal)
        self.sensitivity_slider.setObjectName("vmSlider")
        self.sensitivity_slider.setMinimum(10)
        self.sensitivity_slider.setMaximum(100)
        self.sensitivity_slider.setValue(self.sensitivity)
        self.sensitivity_slider.valueChanged.connect(
            self.change_sensitivity
        )
        foot.addWidget(self.sensitivity_slider)

        foot.addSpacing(8)

        # Tracking controls
        foot.addLayout(self.build_buttons())

        outer.addWidget(footer, 0)

        return panel

    # ==========================================================
    # SMALL UI HELPERS
    # ==========================================================

    def make_section(self, text):

        label = QLabel(text)
        label.setObjectName("vmSection")

        return label

    def make_guide_row(self, icon, name, action):

        row = QFrame()
        row.setObjectName("vmGestureRow")
        row.setProperty("active", False)

        h = QHBoxLayout(row)
        h.setContentsMargins(10, 5, 10, 5)
        h.setSpacing(10)

        icon_label = QLabel(icon)
        icon_label.setObjectName("vmGestureIcon")
        icon_label.setFixedWidth(24)

        text = QVBoxLayout()
        text.setSpacing(0)

        name_label = QLabel(name)
        name_label.setObjectName("vmGestureName")

        action_label = QLabel(action)
        action_label.setObjectName("vmGestureAction")

        text.addWidget(name_label)
        text.addWidget(action_label)

        h.addWidget(icon_label)
        h.addLayout(text, 1)

        return row

    def build_buttons(self):

        layout = QHBoxLayout()
        layout.setSpacing(8)

        self.start_button = QPushButton("Start")
        self.pause_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")

        self.start_button.setObjectName("vmPrimary")
        self.pause_button.setObjectName("vmSecondary")
        self.stop_button.setObjectName("vmSecondary")

        for button in (
            self.start_button,
            self.pause_button,
            self.stop_button
        ):
            button.setFixedHeight(38)
            button.setMinimumWidth(64)
            button.setCursor(Qt.PointingHandCursor)
            button.setSizePolicy(
                QSizePolicy.Expanding,
                QSizePolicy.Fixed
            )

        # Start is the main action, so it gets the widest button.
        layout.addWidget(self.start_button, 2)
        layout.addWidget(self.pause_button, 1)
        layout.addWidget(self.stop_button, 1)

        self.start_button.clicked.connect(self.start_tracking)
        self.pause_button.clicked.connect(self.pause_tracking)
        self.stop_button.clicked.connect(self.stop_tracking)

        return layout

    # ==========================================================
    # BACKGROUND
    # ==========================================================

    def paintEvent(self, event):

        from widgets import page_background

        page_background.paint_page_background(self, self._page_colors)

    # ==========================================================
    # THEME
    #
    # Every colour on this page comes from the app theme through
    # ONE stylesheet, so switching light / dark repaints it all.
    # ==========================================================

    def apply_theme(self):

        from settings import theme as app_theme

        self._theme_name = app_theme.current_name()

        from widgets import page_background

        c = self._page_colors = page_colors()

        self.state_colors = STATE_COLORS.get(
            "Dark" if app_theme.is_dark() else "Light"
        )

        self.setStyleSheet(
            page_background.LAYER_RULE + f"""
            QWidget#vmPage {{
                background: transparent;
            }}

            QLabel {{
                background: transparent;
                color: {c['text']};
            }}

            QLabel#vmTitle {{
                font-size: 22px;
                font-weight: 700;
            }}

            QLabel#vmSubtitle {{
                font-size: 13px;
                color: {c['text_secondary']};
            }}

            QLabel#vmSection {{
                font-size: 14px;
                font-weight: 700;
            }}

            QLabel#vmHint {{
                font-size: 12px;
                color: {c['text_secondary']};
            }}

            QLabel#vmValue {{
                font-size: 13px;
                font-weight: 600;
            }}

            QFrame#vmFeed {{
                background: {c['card']};
                border: 1px solid {c['border']};
                border-radius: 14px;
            }}

            QLabel#vmCamera {{
                background: {c['well']};
                border-radius: 10px;
                color: {c['text_secondary']};
                font-size: 14px;
            }}

            QLabel#vmMeta {{
                font-size: 12px;
                color: {c['text_secondary']};
            }}

            QLabel#vmStatus {{
                font-size: 12px;
                font-weight: 700;
                color: {c['text_secondary']};
            }}

            QScrollArea#vmPanelScroll,
            QWidget#vmPanelContent {{
                background: transparent;
                border: none;
            }}

            QWidget#vmPanelFooter {{
                background: transparent;
                border-top: 1px solid {c['border']};
            }}

            QScrollArea#vmPanelScroll QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 4px 2px 4px 0;
            }}

            QScrollArea#vmPanelScroll QScrollBar::handle:vertical {{
                background: {c['border']};
                border-radius: 3px;
                min-height: 30px;
            }}

            QScrollArea#vmPanelScroll QScrollBar::add-line:vertical,
            QScrollArea#vmPanelScroll QScrollBar::sub-line:vertical,
            QScrollArea#vmPanelScroll QScrollBar::add-page:vertical,
            QScrollArea#vmPanelScroll QScrollBar::sub-page:vertical {{
                background: transparent;
                height: 0;
            }}

            QFrame#vmPanel {{
                background: {c['card']};
                border: 1px solid {c['border']};
                border-radius: 14px;
            }}

            QFrame#vmGestureRow {{
                background: transparent;
                border: none;
                border-left: 3px solid transparent;
                border-radius: 6px;
            }}

            QFrame#vmGestureRow[active="true"] {{
                background: {c['button_hover']};
                border-left: 3px solid {c['primary']};
            }}

            QLabel#vmGestureIcon {{
                font-size: 16px;
                font-weight: 700;
                color: {c['primary']};
                qproperty-alignment: AlignCenter;
            }}

            QLabel#vmGestureName {{
                font-size: 13px;
                font-weight: 600;
            }}

            QLabel#vmGestureAction {{
                font-size: 12px;
                color: {c['text_secondary']};
            }}

            QPushButton#vmPrimary {{
                background: {c['primary']};
                color: {c['primary_text']};
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
                padding: 0 8px;
            }}

            QPushButton#vmPrimary:hover {{
                background: {c['sidebar_hover']};
                color: {c['sidebar_text']};
            }}

            QPushButton#vmSecondary {{
                background: {c['primary']};
                color: {c['primary_text']};
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
                padding: 0 6px;
            }}

            QPushButton#vmSecondary:hover {{
                background: {c['sidebar_hover']};
                color: {c['sidebar_text']};
            }}

            QPushButton#vmPrimary[active="true"],
            QPushButton#vmSecondary[active="true"] {{
                background: {BUTTON_ACTIVE['Dark' if app_theme.is_dark() else 'Light']};
                color: {'#1A1206' if app_theme.is_dark() else '#FFFFFF'};
            }}

            QPushButton:focus {{
                outline: none;
                border: 2px solid {c['accent'] if app_theme.is_dark() else c['sidebar_hover']};
            }}

            QSlider#vmSlider::groove:horizontal {{
                height: 5px;
                background: {c['border']};
                border-radius: 2px;
            }}

            QSlider#vmSlider::sub-page:horizontal {{
                background: {c['primary']};
                border-radius: 2px;
            }}

            QSlider#vmSlider::handle:horizontal {{
                width: 16px;
                height: 16px;
                margin: -6px 0;
                background: {c['card']};
                border: 2px solid {c['primary']};
                border-radius: 9px;
            }}

            QSplitter#vmSplitter::handle {{
                background: transparent;
            }}
            """
        )

        for i in range(1, self.splitter.count()):

            handle = self.splitter.handle(i)

            if isinstance(handle, GripHandle):

                handle.grip_color = QColor(c['border'])
                handle.hover_color = QColor(c['primary'])
                handle.update()

        if hasattr(self, "screen_map"):
            self.screen_map.set_colors(c)

        self.update()

        self.set_tracking_status(
            self.tracking_status.text(),
            self._status_state
        )

    def set_tracking_status(self, text, state="off"):
        """state is one of: off, live, paused, error."""

        self._status_state = state

        self.tracking_status.setText(text)

        color = getattr(self, "state_colors", {}).get(state)

        if color:

            self.tracking_status.setStyleSheet(
                f"QLabel#vmStatus {{ color: {color}; }}"
            )

        else:

            self.tracking_status.setStyleSheet("")

        # Highlight the button that matches the current state.
        active = {
            "live": "start_button",
            "paused": "pause_button",
            "off": "stop_button",
        }.get(state)

        for name in ("start_button", "pause_button", "stop_button"):
            button = getattr(self, name, None)

            if button is None:
                continue

            button.setProperty("active", name == active)
            button.style().unpolish(button)
            button.style().polish(button)

    def set_active_gesture(self, key):
        """Highlight the guide row for the gesture in use."""

        for row_key, row in self.guide_rows.items():

            active = row_key == key

            if row.property("active") == active:
                continue

            row.setProperty("active", active)
            row.style().unpolish(row)
            row.style().polish(row)

    # ==========================================================
    # RESPONSIVE LAYOUT
    # ==========================================================

    def resizeEvent(self, event):

        super().resizeEvent(event)

        # Stack the camera above the panel on narrow windows.
        orientation = (
            Qt.Vertical if self.width() < 900 else Qt.Horizontal
        )

        if self.splitter.orientation() != orientation:

            self.splitter.setOrientation(orientation)

            self.reset_splitter()

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
                "Camera not available",
                "error"
            )

            return False

        # ------------------------------------------------------
        # FIXED CAMERA RESOLUTION
        # ------------------------------------------------------

        # MJPG lets most USB webcams deliver full frame rate at this
        # resolution (raw YUY2 often drops to 15 fps or less).
        try:

            self.camera.set(
                cv2.CAP_PROP_FOURCC,
                cv2.VideoWriter_fourcc(*"MJPG")
            )

        except Exception:
            pass

        self.camera.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            self.camera_width
        )

        self.camera.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            self.camera_height
        )

        try:

            self.camera.set(
                cv2.CAP_PROP_FPS,
                30
            )

        except Exception:
            pass

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

    def start_tracking(self):

        if not self.open_camera():
            return

        self.camera_running = True
        self.camera_paused = False

        # The user explicitly wants tracking active.
        self.camera_was_running = True

        # Reset cursor smoothing so the cursor does not jump
        # from an old hand position when tracking starts.
        self.reset_cursor_filter()

        self.frame_count = 0
        self._frame_times.clear()

        self.set_tracking_status(
            "Tracking on",
            "live"
        )

        if self.worker is None:

            self.worker = CameraWorker(
                self.camera,
                self.hands,
                self.mp_hands,
                self.mp_drawing
            )

            self.worker.ready.connect(self.update_camera)

            self.worker.start()

        self.worker.paused = False

    def stop_worker(self):
        """Stop the background threads before the camera is released."""

        if self.worker is None:
            return

        try:
            self.worker.ready.disconnect(self.update_camera)
        except TypeError:
            pass

        self.worker.stop()
        self.worker = None

    def reset_cursor_filter(self):
        """Forget the old hand position so the cursor does not jump."""

        self.previous_x = None
        self.previous_y = None

        self.filter_x.reset()
        self.filter_y.reset()

    # ==========================================================
    # PAUSE
    # ==========================================================

    def pause_tracking(self):

        if not self.camera_running:
            return

        self.camera_paused = True

        if self.worker is not None:
            self.worker.paused = True

        self.reset_gesture_status()

        self.set_tracking_status(
            "Paused",
            "paused"
        )

    # ==========================================================
    # STOP
    # ==========================================================

    def stop_tracking(self):

        self.camera_running = False
        self.camera_paused = False

        # The user explicitly stopped tracking.
        self.camera_was_running = False

        self.stop_worker()

        if self.camera:

            self.camera.release()
            self.camera = None

        # Pages mirroring this camera must not keep a frozen frame.
        self.latest_frame = None
        self.latest_hand = None

        self.reset_cursor_filter()

        self.last_gesture = "None"

        self.set_tracking_status(
            "Tracking off"
        )

        self.fps_label.setText(
            "0 fps"
        )

        self.camera_label.clear()

        self.camera_label.setText(
            "Camera is off.\nPress Start to begin tracking."
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

        self.stop_worker()

        if self.camera:
            self.camera.release()
            self.camera = None

        self.latest_frame = None
        self.latest_hand = None

        self.camera_running = False
        self.camera_paused = False

        self.reset_cursor_filter()

        self.reset_gesture_status()

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

        # The theme may have been changed on the Settings page.
        from settings import theme as app_theme

        if app_theme.current_name() != self._theme_name:
            self.apply_theme()

        if self.camera_was_running and self.camera is None:
            self.start_tracking()

    # ==========================================================
    # UPDATE CAMERA
    # ==========================================================

    def update_camera(self):
        """Handle the newest frame from the camera worker."""

        if self.worker is None or self.camera_paused:
            return

        result = self.worker.take()

        if result is None:
            return

        # Mirrored, with landmarks already drawn by the worker.
        frame, hand, stamp = result

        self._frame_stamp = stamp

        # ------------------------------------------------------
        # GESTURES
        # ------------------------------------------------------

        gesture = "None"

        # If MediaPipe is unavailable, just show raw camera feed.
        if self.hands is not None:

            if hand is not None:

                self.latest_hand = hand

                gesture = self.detect_gesture(
                    hand
                )

                self.perform_gesture(
                    gesture,
                    hand
                )

            else:

                self.latest_hand = None

                # The filter must not blend an old hand position
                # into the first frame after the hand comes back.
                self.filter_x.reset()
                self.filter_y.reset()

                self.reset_gesture_status()

        # ------------------------------------------------------
        # FPS (measured over the last 30 frames)
        # ------------------------------------------------------

        self.frame_count += 1

        now = time.monotonic()
        self._frame_times.append(now)

        if len(self._frame_times) > 1 and self.frame_count % 10 == 0:

            span = self._frame_times[-1] - self._frame_times[0]

            if span > 0:

                fps = (len(self._frame_times) - 1) / span

                self.fps_label.setText(f"{fps:.0f} fps")

        # ------------------------------------------------------
        # CAMERA DISPLAY
        # ------------------------------------------------------

        # Share the latest frame (with landmarks drawn) so other pages such
        # as the Whiteboard preview can show it without opening the camera.
        # The page-only overlay is drawn after this copy.
        self.latest_frame = frame.copy()

        self.draw_gesture_overlay(
            frame,
            gesture
        )

        self.display_frame(
            frame
        )

    def draw_gesture_overlay(self, frame, gesture):
        """Show a click flash on the feed so clicks are easy to confirm."""

        if self._click_flash <= 0:
            return

        self._click_flash -= 1

        cv2.putText(
            frame,
            self._click_text,
            (14, 36),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (60, 200, 120),
            2,
            cv2.LINE_AA
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

    @staticmethod
    def _dist(a, b):

        return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5

    def detect_gesture(
        self,
        hand
    ):

        lm = hand.landmark
        HL = self.mp_hands.HandLandmark

        dist = self._dist

        wrist = lm[HL.WRIST]

        # Hand size (wrist -> middle knuckle) so every threshold works at
        # any distance from the camera.
        palm = dist(wrist, lm[HL.MIDDLE_FINGER_MCP]) or 1e-6

        thumb_tip = lm[HL.THUMB_TIP]
        index_tip = lm[HL.INDEX_FINGER_TIP]

        # --------------------------------------------------
        # 🤏 THUMB + INDEX TOUCHING  ->  RIGHT CLICK
        #
        # The index tip must still be away from the palm: in a fist
        # the thumb rests near the curled index, which is not a pinch.
        # Hysteresis: tips must be close to start, may part a little
        # before the pinch ends.
        # --------------------------------------------------

        pinch = dist(thumb_tip, index_tip) / palm

        pinch_threshold = 0.32 if self.last_gesture == "Pinch" else 0.22

        index_reaching = (
            dist(index_tip, wrist)
            > dist(lm[HL.INDEX_FINGER_PIP], wrist)
        )

        if pinch < pinch_threshold and index_reaching:
            return "Pinch"

        # --------------------------------------------------
        # ✊ CLOSED HAND (FIST)  ->  LEFT CLICK
        # --------------------------------------------------

        if self.is_fist(lm, HL, palm):
            return "Fist"

        # --------------------------------------------------
        # 🖐️ OPEN PALM  ->  MOVE CURSOR (+ scroll zones)
        # --------------------------------------------------

        fingers = (
            (HL.INDEX_FINGER_TIP, HL.INDEX_FINGER_PIP),
            (HL.MIDDLE_FINGER_TIP, HL.MIDDLE_FINGER_PIP),
            (HL.RING_FINGER_TIP, HL.RING_FINGER_PIP),
            (HL.PINKY_TIP, HL.PINKY_PIP),
        )

        if all(lm[tip].y < lm[pip].y for tip, pip in fingers):
            return "Open Palm"

        return "None"

    def is_fist(self, lm, HL, palm):
        """Return True when all four fingers are curled into the palm.

        A finger counts as folded when its tip is below its middle
        knuckle (PIP), closer to the wrist than that knuckle, or close
        to the palm. This works whatever the hand's rotation.
        """

        dist = self._dist

        wrist = lm[HL.WRIST]

        fingers = (
            (HL.INDEX_FINGER_TIP, HL.INDEX_FINGER_PIP),
            (HL.MIDDLE_FINGER_TIP, HL.MIDDLE_FINGER_PIP),
            (HL.RING_FINGER_TIP, HL.RING_FINGER_PIP),
            (HL.PINKY_TIP, HL.PINKY_PIP),
        )

        for tip_id, pip_id in fingers:

            tip = lm[tip_id]
            pip = lm[pip_id]

            tip_wrist = dist(tip, wrist)

            curled = tip_wrist < dist(pip, wrist)
            below = tip.y > pip.y
            near_palm = tip_wrist < 1.3 * palm

            if not (curled or below or near_palm):
                return False

        return True

    # ==========================================================
    # PERFORM GESTURE
    # ==========================================================

    def perform_gesture(
        self,
        gesture,
        hand
    ):

        fire_left = self.left_trigger.update(gesture == "Fist")
        fire_right = self.right_trigger.update(gesture == "Pinch")

        # Scroll zones only count while the open palm steers the cursor.
        # A single undetected frame ("None") does not reset the hold.
        if gesture not in ("Open Palm", "None"):
            self.reset_dwell()

        self.last_gesture = gesture

        if gesture == "None":
            return

        # --------------------------------------------------
        # 🖐️ OPEN PALM -> move cursor, scroll in the zones
        # --------------------------------------------------

        if gesture == "Open Palm":

            self.move_cursor(hand)

            if not self.update_scroll_zone():
                self.set_active_gesture("move")
                self.set_action("Moving the cursor")

        # --------------------------------------------------
        # ✊ FIST -> left click (once per fist)
        # --------------------------------------------------

        elif gesture == "Fist":

            if fire_left:
                self.click("left")

            self.set_active_gesture("left")
            self.set_action("Left click")

        # --------------------------------------------------
        # 🤏 PINCH -> right click (once per pinch)
        # --------------------------------------------------

        elif gesture == "Pinch":

            if fire_right:
                self.click("right")

            self.set_active_gesture("right")
            self.set_action("Right click")

    def click(self, button):
        """Click where the cursor was just before the hand changed shape."""

        target = None
        cutoff = time.monotonic() - 0.3

        for t, x, y in reversed(self._cursor_history):

            if t <= cutoff:

                target = (x, y)
                break

        try:

            if target is not None:

                native_click(target[0], target[1], button)

                self.previous_x, self.previous_y = target

                # Continue smoothing from the click point, not from
                # where the closing hand had dragged the cursor.
                self.filter_x.x, self.filter_y.x = map(float, target)

            else:

                native_click(button=button)

        except Exception as exc:

            print(f"Virtual mouse: {button} click failed:", exc)

        self._click_text = (
            "Left click" if button == "left" else "Right click"
        )
        self._click_flash = 10

    # ==========================================================
    # ACTION LABEL
    # ==========================================================

    def set_action(self, text):

        if hasattr(self, "gesture_action"):

            self.gesture_action.setText(text)

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

        # Filter on the camera frame's capture time, so detection
        # speed does not change how smooth the cursor feels.
        t = getattr(self, "_frame_stamp", None) or time.monotonic()

        smooth_x = self.filter_x(float(target_x), t)
        smooth_y = self.filter_y(float(target_y), t)

        smooth_x = max(
            0,
            min(self.screen_width - 1, int(smooth_x))
        )

        smooth_y = max(
            0,
            min(self.screen_height - 1, int(smooth_y))
        )

        if (smooth_x, smooth_y) != (self.previous_x, self.previous_y):
            self.move_to(smooth_x, smooth_y)

        self.previous_x = smooth_x
        self.previous_y = smooth_y

    def move_to(self, x, y):

        self._cursor_history.append(
            (time.monotonic(), int(x), int(y))
        )

        try:

            native_move(x, y)

        except Exception:

            # Never let a cursor-move error crash frame handling.
            pass

    # ==========================================================
    # SCROLL ZONES
    #
    # Hold the cursor in the upper-middle of the screen for 1 second
    # to scroll up, or the lower-middle to scroll down. Scrolling
    # continues until the cursor leaves the zone.
    # ==========================================================

    def scroll_zone_at(self, x, y):

        fx = x / float(self.screen_width)
        fy = y / float(self.screen_height)

        if not (ZONE_X[0] <= fx <= ZONE_X[1]):
            return None

        if fy <= ZONE_TOP:
            return "up"

        if fy >= ZONE_BOTTOM:
            return "down"

        return None

    def update_scroll_zone(self):
        """Advance the dwell timer. Returns True while in a zone."""

        if self.previous_x is None:
            return False

        x, y = self.previous_x, self.previous_y

        zone = self.scroll_zone_at(x, y)

        now = time.monotonic()

        if zone != self._dwell_zone:

            self._dwell_zone = zone
            self._dwell_start = now
            self._last_scroll = 0.0

        cursor = (
            x / float(self.screen_width),
            y / float(self.screen_height),
        )

        if zone is None:

            self.screen_map.set_state(cursor, None, 0.0, False)

            return False

        elapsed = now - self._dwell_start

        progress = min(1.0, elapsed / SCROLL_DWELL_SECONDS)

        scrolling = elapsed >= SCROLL_DWELL_SECONDS

        if scrolling and now - self._last_scroll >= SCROLL_REPEAT_SECONDS:

            try:

                native_scroll(1 if zone == "up" else -1)

            except Exception as exc:

                print("Virtual mouse: scroll failed:", exc)

            self._last_scroll = now

        key = "scroll_up" if zone == "up" else "scroll_down"

        self.set_active_gesture(key)

        if scrolling:

            self.set_action(
                "Scrolling up" if zone == "up" else "Scrolling down"
            )

        else:

            remaining = SCROLL_DWELL_SECONDS - elapsed

            self.set_action(
                f"Hold to scroll {zone}: {remaining:.1f} s left"
            )

        self.screen_map.set_state(cursor, zone, progress, scrolling)

        return True

    def reset_dwell(self):

        self._dwell_zone = None
        self._dwell_start = 0.0
        self._last_scroll = 0.0

        if hasattr(self, "screen_map"):

            cursor = None

            if self.previous_x is not None:

                cursor = (
                    self.previous_x / float(self.screen_width),
                    self.previous_y / float(self.screen_height),
                )

            self.screen_map.set_state(cursor, None, 0.0, False)

    # ==========================================================
    # RESET
    # ==========================================================

    def reset_gesture_status(self):

        self.reset_dwell()

        # Losing the hand counts as "gesture released" so the next fist
        # or pinch clicks again.
        for _ in range(self.left_trigger.release):
            self.left_trigger.update(False)
            self.right_trigger.update(False)

        self.last_gesture = "None"

        if hasattr(self, "guide_rows"):
            self.set_active_gesture(None)

        self.set_action("No hand detected")

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
        # The feed fills the label while keeping its aspect ratio.
        # ------------------------------------------------------

        target = self.camera_label.contentsRect().size()

        if target.width() < 40 or target.height() < 40:

            target = QSize(480, 360)

        pixmap = pixmap.scaled(
            target,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
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

        if index is None or index == self.camera_index:
            return

        was_running = self.camera_running

        # Tracking may be paused because another page borrowed the
        # webcam; keep that intent so it resumes on the new camera.
        should_resume = self.camera_was_running

        self.stop_tracking()

        self.camera_index = index

        if was_running:

            self.start_tracking()

        else:

            self.camera_was_running = should_resume

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

        self.stop_worker()

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
