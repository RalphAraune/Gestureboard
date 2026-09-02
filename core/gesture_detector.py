# core/gesture_detector.py

from typing import Optional


class GestureDetector:
    """
    Gesture recognition for GestureBoard Presentation Control.

    Supported gestures:
        ✊ Fist              -> Start Presentation
        ☝️ Index             -> Cursor / Pointer
        ✌️ Peace             -> Next Slide
        🖖 Three Fingers     -> Previous Slide
        🤟 Thumb + Pinky     -> Full Screen
        ✋ Open Hand         -> Exit Full Screen
    """

    def __init__(self):
        self.last_gesture = "None"

    @staticmethod
    def _finger_extended(landmarks, tip, pip):
        """
        Determines whether a finger is extended.

        MediaPipe landmark coordinates:
            x -> horizontal
            y -> vertical

        For index/middle/ring/pinky:
            fingertip above PIP = extended
        """
        return landmarks[tip].y < landmarks[pip].y

    @staticmethod
    def _thumb_extended(landmarks):
        """
        Detects whether the thumb is extended.

        This uses horizontal distance between thumb tip and thumb IP.
        """
        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]

        return abs(thumb_tip.x - thumb_ip.x) > 0.04

    def detect(self, hand_landmarks) -> str:
        """
        Detect gesture from MediaPipe hand landmarks.

        Returns a readable gesture name.
        """

        if hand_landmarks is None:
            self.last_gesture = "None"
            return "None"

        lm = hand_landmarks.landmark

        # MediaPipe finger landmarks
        INDEX_TIP = 8
        INDEX_PIP = 6

        MIDDLE_TIP = 12
        MIDDLE_PIP = 10

        RING_TIP = 16
        RING_PIP = 14

        PINKY_TIP = 20
        PINKY_PIP = 18

        index = self._finger_extended(lm, INDEX_TIP, INDEX_PIP)
        middle = self._finger_extended(lm, MIDDLE_TIP, MIDDLE_PIP)
        ring = self._finger_extended(lm, RING_TIP, RING_PIP)
        pinky = self._finger_extended(lm, PINKY_TIP, PINKY_PIP)
        thumb = self._thumb_extended(lm)

        # ---------------------------------------------------------
        # PEACE SIGN
        # Index + Middle extended
        # Ring + Pinky closed
        # ---------------------------------------------------------
        if index and middle and not ring and not pinky:
            gesture = "Peace Sign"

        # ---------------------------------------------------------
        # THREE FINGERS
        # Index + Middle + Ring extended
        # Pinky closed
        #
        # Thumb is ignored because the user's preferred gesture
        # is specifically index + middle + ring.
        # ---------------------------------------------------------
        elif index and middle and ring and not pinky:
            gesture = "Three Fingers"

        # ---------------------------------------------------------
        # THUMB + PINKY
        # Used for Full Screen
        # ---------------------------------------------------------
        elif thumb and pinky and not index and not middle and not ring:
            gesture = "Thumb + Pinky"

        # ---------------------------------------------------------
        # OPEN HAND
        # All four fingers extended
        # ---------------------------------------------------------
        elif index and middle and ring and pinky:
            gesture = "Open Hand"

        # ---------------------------------------------------------
        # INDEX ONLY
        # ---------------------------------------------------------
        elif index and not middle and not ring and not pinky:
            gesture = "Index Finger"

        # ---------------------------------------------------------
        # FIST
        # ---------------------------------------------------------
        elif not index and not middle and not ring and not pinky:
            gesture = "Fist"

        else:
            gesture = "Unknown"

        self.last_gesture = gesture
        return gesture