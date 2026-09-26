# core/gesture_detector.py

from typing import Optional


class GestureDetector:
    """
    Hand-gesture recognition for GestureBoard Presentation Control.

    Presentation gestures:
        🤘 Rock & Roll   -> Start Presentation
        👉 Point Right   -> Next Slide
        👈 Point Left    -> Previous Slide
        👍 Thumbs Up     -> Full Screen
        👎 Thumbs Down   -> Exit Full Screen
        ☝️ Index Finger  -> Cursor / Pointer

    Annotation gestures:
        🖖 Three Fingers            -> Toggle Annotation Mode
        ☝️ + 🖕 Index + Middle together -> Draw
        ✌️ Peace Sign (apart)        -> Stop Drawing
        ✋ Open Hand                 -> Move Cursor / Select Tool
        ✊ Fist                      -> Click
    """

    # Distance (normalised) below which the index and middle tips are
    # considered "together" (draw) vs "separated" (peace sign).
    TOGETHER_DISTANCE = 0.045

    def __init__(self):
        self.last_gesture = "None"

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _finger_up(landmarks, tip, pip):
        return landmarks[tip].y < landmarks[pip].y

    @staticmethod
    def _dist(landmarks, a, b):
        return (
            (landmarks[a].x - landmarks[b].x) ** 2
            + (landmarks[a].y - landmarks[b].y) ** 2
        ) ** 0.5

    # ============================================================
    # DETECT
    # ============================================================

    def detect(self, hand_landmarks) -> str:

        if hand_landmarks is None:
            self.last_gesture = "None"
            return "None"

        lm = hand_landmarks.landmark

        index_up = self._finger_up(lm, 8, 6)
        middle_up = self._finger_up(lm, 12, 10)
        ring_up = self._finger_up(lm, 16, 14)
        pinky_up = self._finger_up(lm, 20, 18)

        # Thumb: extended and pointing up (tip above the MCP).
        thumb_tip_up = lm[4].y < lm[2].y
        thumb_extended = self._dist(lm, 4, 5) > 0.08

        index_middle = self._dist(lm, 8, 12)

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

            if index_middle < self.TOGETHER_DISTANCE:
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

            if thumb_extended and thumb_tip_up:
                gesture = "Thumbs Up"
            elif thumb_extended and not thumb_tip_up:
                gesture = "Thumbs Down"
            else:
                gesture = "Fist"

        else:
            gesture = "None"

        self.last_gesture = gesture
        return gesture
