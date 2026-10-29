# core/gesture_detector.py

from collections import deque
from typing import Optional


class SwipeDetector:
    """Spots a quick sideways swipe of the whole open hand.

    Call track(hand, now) on every camera frame (hand may be None). It
    follows the centre of the knuckles while the hand is open (at least
    three fingers stretched) and returns "Swipe Right" or "Swipe Left"
    once per swipe. Positions are in the mirrored camera image, so
    right is the user's right.

    A swipe has to be:
      * long: about one palm length across the image (so it adapts to
        how far the hand is from the camera), within WINDOW seconds;
      * straight: mostly sideways, not up/down;
      * steady: nearly all of the movement in one direction, so a
        shaky or wandering hand never counts.

    The knuckles are tracked rather than a fingertip: they stay in the
    picture and keep their shape even when the fingertips are blurred
    or cut off, and when the wrist is out of frame.

    With confirm_delay > 0 a swipe only fires after that long without
    the hand turning back, so a wave (back and forth) is not taken for
    a swipe. The recent path is kept in `trail` for drawing.
    """

    # Travel needed, in palm lengths, clamped to a fraction of the
    # image width.
    SWIPE_PALMS = 1.0
    MIN_DISTANCE = 0.10
    MAX_DISTANCE = 0.22

    # The travel has to happen within this many seconds.
    WINDOW = 0.45

    # Sideways travel must be this many times the up/down travel.
    STRAIGHTNESS = 1.8

    # Share of the sideways movement that must go the swipe's way.
    STEADINESS = 0.8

    # A gap without an open hand longer than this starts a new swipe
    # (shorter gaps are blurred frames mid-swipe).
    GAP = 0.25

    # After a swipe, ignore all movement for COOLDOWN, and a swipe the
    # other way for OPPOSITE_COOLDOWN (the hand coming back).
    COOLDOWN = 0.5
    OPPOSITE_COOLDOWN = 1.0

    # Turning back this far (image width) before confirm_delay ends
    # means it was a wave, not a swipe.
    REVERSE = 0.06

    # How long the trail behind the hand lasts.
    TRAIL_SECONDS = 0.6

    # A finger is stretched when its tip reaches this many times as far
    # from the wrist as its middle joint. Looser than GestureDetector:
    # a moving hand blurs.
    STRETCHED = 1.1

    def __init__(self):
        self._samples = deque()
        self._quiet_until = 0.0
        self._blocked = None          # (direction, until)
        self._pending = None          # [direction, fire_at, extreme_x]
        self._last_seen = 0.0
        self.confirm_delay = 0.0
        self.trail = deque()          # (time, x, y)
        self.last_swipe = None        # (direction, time)

    def reset(self):
        self._samples.clear()
        self._pending = None

    @classmethod
    def hand_open(cls, lm):
        """At least three of the four fingers straight out (any direction)."""

        def reach(i):
            return ((lm[i].x - lm[0].x) ** 2 + (lm[i].y - lm[0].y) ** 2) ** 0.5

        stretched = sum(
            reach(tip) > reach(pip) * cls.STRETCHED
            for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18))
        )

        return stretched >= 3

    @staticmethod
    def palm_centre(lm):
        """Centre of the four knuckles."""

        knuckles = (5, 9, 13, 17)
        x = sum(lm[i].x for i in knuckles) / 4
        y = sum(lm[i].y for i in knuckles) / 4

        return x, y

    def track(self, hand, now):
        """Follow the open `hand` (or None); returns a swipe or None."""

        self._trim_trail(now)

        if hand is None or not self.hand_open(hand.landmark):
            # A swipe waiting to be confirmed fires once the hand has
            # gone: it did not turn back.
            if self._pending and now >= self._pending[1]:
                return self._fire(self._pending[0], now)

            # Drop the swipe only after a real gap, not one bad frame.
            if now - self._last_seen > self.GAP:
                self._samples.clear()
            return None

        lm = hand.landmark

        if now - self._last_seen > self.GAP:
            self._samples.clear()
            self.trail.clear()

        self._last_seen = now

        x, y = self.palm_centre(lm)
        palm = ((lm[9].x - lm[0].x) ** 2 + (lm[9].y - lm[0].y) ** 2) ** 0.5

        return self.update(x, y, now, palm)

    def update(self, x, y, now, palm=None):

        self.trail.append((now, x, y))

        if self._pending:
            return self._confirm(x, now)

        if now < self._quiet_until:
            self._samples.clear()
            return None

        samples = self._samples
        samples.append((now, x, y))

        while samples and now - samples[0][0] > self.WINDOW:
            samples.popleft()

        if len(samples) < 3:
            return None

        # Compare with the furthest-back sample in the window.
        _t0, x0, y0 = samples[0]
        dx = x - x0
        dy = y - y0

        need = self.MIN_DISTANCE
        if palm:
            need = min(self.MAX_DISTANCE, max(self.MIN_DISTANCE, palm * self.SWIPE_PALMS))

        if abs(dx) < need or abs(dx) < abs(dy) * self.STRAIGHTNESS:
            return None

        # Steady: almost every step went the swipe's way.
        sign = 1 if dx > 0 else -1
        points = list(samples)
        forward = total = 0.0

        for (_ta, xa, _ya), (_tb, xb, _yb) in zip(points, points[1:]):
            step = (xb - xa) * sign
            total += abs(step)
            if step > 0:
                forward += step

        if total and forward / total < self.STEADINESS:
            return None

        direction = "Swipe Right" if dx > 0 else "Swipe Left"

        samples.clear()

        # The hand coming back after a swipe the other way.
        if self._blocked and self._blocked[0] != direction and now < self._blocked[1]:
            return None

        if self.confirm_delay > 0:
            self._pending = [direction, now + self.confirm_delay, x]
            return None

        return self._fire(direction, now)

    def _confirm(self, x, now):

        direction, fire_at, extreme = self._pending
        sign = 1 if direction == "Swipe Right" else -1

        if (x - extreme) * sign > 0:
            self._pending[2] = x
        elif (extreme - x) * sign >= self.REVERSE:
            # Turned back: a wave, not a swipe.
            self._pending = None
            self._samples.clear()
            return None

        if now >= fire_at:
            return self._fire(direction, now)

        return None

    def _fire(self, direction, now):

        self._pending = None
        self._samples.clear()
        self._quiet_until = now + self.COOLDOWN
        self._blocked = (direction, now + self.OPPOSITE_COOLDOWN)
        self.last_swipe = (direction, now)

        return direction

    def _trim_trail(self, now):

        while self.trail and now - self.trail[0][0] > self.TRAIL_SECONDS:
            self.trail.popleft()


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
        👉 Swipe open hand right -> Next Slide (see SwipeDetector)
        👈 Swipe open hand left  -> Previous Slide
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
    THUMB_OUT = 0.5
    THUMB_TILT = 0.25

    # Thumbs up / down: no finger may reach this far (see STRETCHED),
    # and the thumb tip must be this far (palm lengths) above / below
    # every finger point.
    CLEARLY_STRETCHED = 1.35
    THUMB_BEYOND = 0.1

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

    def _thumb_direction(self, lm, palm):
        """"Thumbs Up", "Thumbs Down" or None.

        The thumb must be straight, stick out from the fist, point
        mostly up or down, and its tip must be the highest (thumbs up)
        or lowest (thumbs down) point of the hand. That last check is
        what tells it from a hand with fingers pointing the same way,
        so the fingers only have to be not clearly stretched.
        """

        # Straight thumb: base -> tip about as long as its two bones.
        bones = self._dist(lm, 2, 3) + self._dist(lm, 3, 4)
        if self._dist(lm, 2, 4) < bones * 0.8:
            return None

        # Sticking out, not tucked against the fingers.
        if self._dist(lm, 4, 5) < palm * self.THUMB_OUT:
            return None

        thumb_dx = lm[4].x - lm[2].x
        thumb_dy = lm[4].y - lm[2].y      # image y grows downwards

        if abs(thumb_dy) < abs(thumb_dx) * 0.7 or abs(thumb_dy) < palm * self.THUMB_TILT:
            return None

        # No finger clearly straight (straight is ~1.4-1.6).
        for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18)):
            if self._dist(lm, 0, tip) > self._dist(lm, 0, pip) * self.CLEARLY_STRETCHED:
                return None

        # The thumb tip is beyond every finger point by a margin.
        margin = palm * self.THUMB_BEYOND
        fingers = range(5, 21)

        if thumb_dy < 0 and all(lm[4].y < lm[i].y - margin for i in fingers):
            return "Thumbs Up"

        if thumb_dy > 0 and all(lm[4].y > lm[i].y + margin for i in fingers):
            return "Thumbs Down"

        return None

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

        index_middle = self._dist(lm, 8, 12) / palm

        # ------------------------------------------------------
        # 👍 THUMBS UP / 👎 THUMBS DOWN
        # Checked first, with their own looser test for the folded
        # fingers: an upside-down fist (thumbs down) is foreshortened
        # and a loosely curled finger can read as "stretched".
        # ------------------------------------------------------
        thumb = self._thumb_direction(lm, palm)

        if thumb is not None:
            self.last_gesture = thumb
            return thumb

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
        # ✊ FIST (thumbs up / down were checked above)
        # ------------------------------------------------------
        elif (
            not index_up
            and not middle_up
            and not ring_up
            and not pinky_up
        ):
            gesture = "Fist"

        else:
            gesture = "None"

        self.last_gesture = gesture
        return gesture
