# core/gesture_detector.py

from collections import deque
from typing import Optional


class SwipeDetector:
    """Spots a quick sideways swipe of the index fingertip.

    Call track(hand, now) on every camera frame that has a hand. It
    follows the fingertip while the index finger is stretched out and
    returns "Swipe Right" or "Swipe Left" once per swipe: the tip has
    to travel SWIPE_DISTANCE across the image within WINDOW seconds,
    mostly sideways, so slowly moving the pointer or holding the finger
    still never counts. Positions are in the mirrored camera image, so
    right is the user's right.

    The pose check is separate from GestureDetector on purpose: during
    a swipe the finger points sideways, which GestureDetector does not
    count as "up", and a frame or two of a blurred hand must not end
    the swipe.
    """

    # Fraction of the image width the tip must travel.
    SWIPE_DISTANCE = 0.12

    # The travel has to happen within this many seconds.
    WINDOW = 0.5

    # Sideways travel must be this many times the up/down travel.
    STRAIGHTNESS = 1.5

    # A gap without a stretched index finger longer than this starts
    # a new swipe (shorter gaps are blurred frames mid-swipe).
    GAP = 0.25

    # After a swipe, ignore movement for this long (the hand coming
    # back must not count as a swipe the other way).
    COOLDOWN = 0.8

    def __init__(self):
        self._samples = deque()
        self._quiet_until = 0.0

    def reset(self):
        self._samples.clear()

    @staticmethod
    def index_stretched(lm):
        """Index finger straight out (any direction), middle finger folded.

        Measured from the wrist, so it works with the finger pointing up
        or sideways: a straight finger's tip is well beyond its middle
        joint, a folded one's is not.
        """

        def reach(i):
            return ((lm[i].x - lm[0].x) ** 2 + (lm[i].y - lm[0].y) ** 2) ** 0.5

        # A straight finger reaches ~1.4-1.6x as far as its middle joint,
        # a curled one about 1x or less.
        index_out = reach(8) > reach(6) * 1.2
        middle_out = reach(12) > reach(10) * 1.2

        return index_out and not middle_out

    def track(self, hand, now):
        """Follow the fingertip of `hand`; returns a swipe or None."""

        if hand is None:
            return None

        lm = hand.landmark

        if not self.index_stretched(lm):
            # Drop the swipe only after a real gap, not one bad frame.
            if self._samples and now - self._samples[-1][0] > self.GAP:
                self._samples.clear()
            return None

        if self._samples and now - self._samples[-1][0] > self.GAP:
            self._samples.clear()

        return self.update(lm[8].x, lm[8].y, now)

    def update(self, x, y, now):

        if now < self._quiet_until:
            self._samples.clear()
            return None

        samples = self._samples
        samples.append((now, x, y))

        while samples and now - samples[0][0] > self.WINDOW:
            samples.popleft()

        # Compare with the furthest-back sample in the window.
        _t0, x0, y0 = samples[0]
        dx = x - x0
        dy = y - y0

        if abs(dx) < self.SWIPE_DISTANCE or abs(dx) < abs(dy) * self.STRAIGHTNESS:
            return None

        samples.clear()
        self._quiet_until = now + self.COOLDOWN

        return "Swipe Right" if dx > 0 else "Swipe Left"


class WaveDetector:
    """Spots an open hand waved side to side, like wiping a board.

    Call track(x, now) with the palm's x position on every frame the
    hand is open, and idle(now) on other frames. A wave is STROKES
    sideways strokes (each at least AMPLITUDE of the image width,
    alternating direction) within WINDOW seconds, so simply moving the
    open hand across the screen to reach something never counts.
    """

    AMPLITUDE = 0.06
    STROKES = 3
    WINDOW = 1.6

    # Open hand missing longer than this starts over.
    GAP = 0.3

    def __init__(self):
        self.reset()

    def reset(self):
        self._direction = 0
        self._extreme = None
        self._strokes = 0
        self._first = 0.0
        self._last = 0.0

    def progress(self):
        """0..1: how far through a wave the hand is (0 for one stroke,
        which is just moving the hand)."""
        if self._strokes <= 1:
            return 0.0
        return min(1.0, (self._strokes - 1) / (self.STROKES - 1))

    def idle(self, now):
        if self._extreme is not None and now - self._last > self.GAP:
            self.reset()

    def track(self, x, now):
        """Returns True once, when the wave is complete."""

        if self._extreme is not None and now - self._last > self.GAP:
            self.reset()

        self._last = now

        if self._extreme is None:
            self._extreme = x
            return False

        if self._strokes and now - self._first > self.WINDOW:
            self.reset()
            self._extreme = x
            self._last = now
            return False

        if self._direction == 0:
            if abs(x - self._extreme) >= self.AMPLITUDE:
                self._direction = 1 if x > self._extreme else -1
                self._strokes = 1
                self._first = now
                self._extreme = x
            return False

        if (x - self._extreme) * self._direction > 0:
            # Still moving the same way: follow the furthest point.
            self._extreme = x
        elif (self._extreme - x) * self._direction >= self.AMPLITUDE:
            # Turned back far enough: a new stroke.
            self._direction = -self._direction
            self._strokes += 1
            self._extreme = x

        if self._strokes >= self.STROKES:
            self.reset()
            return True

        return False


class GestureDetector:
    """
    Hand-gesture recognition for GestureBoard Presentation Control.

    Presentation gestures:
        🤘 Rock & Roll   -> Start Presentation
        👉 Swipe index finger right -> Next Slide (see SwipeDetector)
        👈 Swipe index finger left  -> Previous Slide
        👍 Thumbs Up     -> Full Screen
        👎 Thumbs Down   -> Exit Full Screen
        ☝️ Index Finger  -> Cursor / Pointer

    Annotation gestures:
        🖖 Three Fingers            -> Turn Annotation On
        👋 Open Hand waved          -> Clear the slide (see WaveDetector)
        ☝️ + 🖕 Index + Middle together -> Draw
        ✌️ Peace Sign (apart)        -> Stop Drawing
        ✋ Open Hand                 -> Move Cursor / Select Tool
        ✊ Fist                      -> Click
    """

    # Index and middle tips closer than this (in palm lengths) are
    # "together" (draw); further apart is the peace sign (stop).
    TOGETHER_PALMS = 0.32

    # A finger is stretched when its tip reaches this many times as far
    # from the wrist as its middle joint (straight ~1.4-1.6, curled ~1).
    STRETCHED = 1.15

    # Thumb tip at least this far (palm lengths) from the index knuckle
    # counts as sticking out, and this far above / below the thumb's
    # base joint as pointing up / down.
    THUMB_OUT = 0.6
    THUMB_TILT = 0.3

    def __init__(self):
        self.last_gesture = "None"

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _dist(landmarks, a, b):
        return (
            (landmarks[a].x - landmarks[b].x) ** 2
            + (landmarks[a].y - landmarks[b].y) ** 2
        ) ** 0.5

    def _stretched(self, lm, tip, pip):
        """Finger straight out, in any direction.

        Measured from the wrist rather than "tip above joint", so a
        sideways hand (thumbs up, a fist turned to the camera) reads
        the same as an upright one.
        """
        return self._dist(lm, 0, tip) > self._dist(lm, 0, pip) * self.STRETCHED

    # ============================================================
    # DETECT
    # ============================================================

    def detect(self, hand_landmarks) -> str:

        if hand_landmarks is None:
            self.last_gesture = "None"
            return "None"

        lm = hand_landmarks.landmark

        # Every length is compared with the palm (wrist -> middle
        # knuckle), so it works at any distance from the camera.
        palm = max(self._dist(lm, 0, 9), 1e-6)

        index_up = self._stretched(lm, 8, 6)
        middle_up = self._stretched(lm, 12, 10)
        ring_up = self._stretched(lm, 16, 14)
        pinky_up = self._stretched(lm, 20, 18)

        # Thumb: sticking out from the fist, then which way it points.
        thumb_out = self._dist(lm, 4, 5) > palm * self.THUMB_OUT
        thumb_dx = lm[4].x - lm[2].x
        thumb_dy = lm[4].y - lm[2].y      # image y grows downwards
        thumb_vertical = abs(thumb_dy) > abs(thumb_dx) * 0.8

        index_middle = self._dist(lm, 8, 12) / palm

        # ------------------------------------------------------
        # 🤘 ROCK & ROLL  (index + pinky up)  ->  START
        # ------------------------------------------------------
        if index_up and pinky_up and not middle_up and not ring_up:
            gesture = "Rock & Roll"

        # ------------------------------------------------------
        # 🖖 THREE FINGERS (index + middle + ring)  ->  ANNOTATION
        # ------------------------------------------------------
        elif index_up and middle_up and ring_up and not pinky_up:
            gesture = "Three Fingers"

        # ------------------------------------------------------
        # ✋ OPEN HAND (all four)  ->  MOVE CURSOR
        # ------------------------------------------------------
        elif index_up and middle_up and ring_up and pinky_up:
            gesture = "Open Hand"

        # ------------------------------------------------------
        # ☝️/✌️  INDEX + MIDDLE
        #   together -> DRAW, separated -> PEACE (stop drawing)
        # ------------------------------------------------------
        elif index_up and middle_up and not ring_up and not pinky_up:

            if index_middle < self.TOGETHER_PALMS:
                gesture = "Index + Middle"
            else:
                gesture = "Peace Sign"

        # ------------------------------------------------------
        # ☝️ INDEX ONLY  ->  POINT RIGHT / LEFT / UP
        # ------------------------------------------------------
        elif index_up and not middle_up and not ring_up and not pinky_up:

            # Use the index direction from the wrist to the tip (more stable
            # than tip-vs-knuckle) to decide left / right / up.
            index_dx = lm[8].x - lm[0].x

            if index_dx > 0.10:
                gesture = "Point Right"
            elif index_dx < -0.10:
                gesture = "Point Left"
            else:
                gesture = "Index Finger"

        # ------------------------------------------------------
        # 👍 THUMBS UP / 👎 THUMBS DOWN / ✊ FIST
        # ------------------------------------------------------
        elif (
            not index_up
            and not middle_up
            and not ring_up
            and not pinky_up
        ):

            tilt = palm * self.THUMB_TILT

            if thumb_out and thumb_vertical and thumb_dy < -tilt:
                gesture = "Thumbs Up"
            elif thumb_out and thumb_vertical and thumb_dy > tilt:
                gesture = "Thumbs Down"
            else:
                gesture = "Fist"

        else:
            gesture = "None"

        self.last_gesture = gesture
        return gesture
