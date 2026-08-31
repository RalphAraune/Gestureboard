"""Hand tracking using MediaPipe (optional - falls back gracefully if DLL fails)."""

import sys

# Try to import mediapipe, handle DLL load failure gracefully
try:
    import mediapipe as mp
    _mediapipe_available = True
except Exception:
    _mediapipe_available = False
    mp = None


class HandTracker:
    """Hand tracker using MediaPipe for gesture detection.
    
    Falls back gracefully if MediaPipe is not available or DLL fails to load.
    """

    def __init__(self, min_detection_confidence=0.5, min_tracking_confidence=0.5):
        self._mediapipe_available = _mediapipe_available
        self._running = False
        self._min_det = min_detection_confidence
        self._min_trk = min_tracking_confidence

        if self._mediapipe_available:
            try:
                self.mp_hands = mp.solutions.hands
                self.hands = self.mp_hands.Hands(
                    static_image_mode=False,
                    max_num_hands=1,
                    min_detection_confidence=min_detection_confidence,
                    min_tracking_confidence=min_tracking_confidence,
                )
                self.mp_draw = mp.solutions.drawing_utils
            except Exception:
                self._mediapipe_available = False
        else:
            self.hands = None
            self.mp_draw = None

    def start_tracking(self):
        """Start hand tracking (called when camera begins)."""
        self._running = True

    def stop_tracking(self):
        """Stop hand tracking."""
        self._running = False

    def hands_gesture(self, frame):
        """Detect hand landmarks and draw a dot-and-line skeleton on the frame.

        The frame is expected to already be mirrored and contiguous by the
        caller. Detection + drawing happen in-place. Returns a dict, or None.
        """
        if not self._mediapipe_available or not self._running:
            return None

        try:
            # Convert BGR image to RGB for MediaPipe
            import numpy as np
            rgb = cv2.cvtColor(np.ascontiguousarray(frame), cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb)

            if not results.multi_hand_landmarks:
                return None

            # Get the first hand
            hand_landmarks = results.multi_hand_landmarks[0]

            # Landmark positions in pixel coordinates
            h, w, _ = frame.shape
            landmarks = []
            for lm in hand_landmarks.landmark:
                landmarks.append((int(lm.x * w), int(lm.y * h)))

            # Draw with MediaPipe's proven renderer, then reinforce with
            # visible manual dots + lines so they always show up.
            try:
                self.mp_draw.draw_landmarks(
                    frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS
                )
            except Exception:
                pass

            # Extra high-contrast manual skeleton
            DOT_COLOR = (0, 0, 255)      # red dots
            LINE_COLOR = (70, 160, 255)  # bright orange lines (BGR)
            for a, b in self.mp_hands.HAND_CONNECTIONS:
                cv2.line(frame, landmarks[a], landmarks[b], LINE_COLOR, 2, cv2.LINE_AA)
            for pt in landmarks:
                cv2.circle(frame, pt, 5, DOT_COLOR, -1, cv2.LINE_AA)

            # Determine gesture
            gesture = self._determine_gesture(landmarks)

            handedness = None
            try:
                if results.multi_handedness:
                    handedness = results.multi_handedness[0].classification[0].label
            except Exception:
                handedness = None

            return {
                "gesture": gesture,
                "landmarks": landmarks,
                "handedness": handedness,
            }
        except Exception:
            return None

    def _determine_gesture(self, landmarks):
        """Determine the hand gesture from landmark positions.
        
        Returns:
            String describing the gesture
        """
        if len(landmarks) < 21:
            return "unknown"

        # Get key landmarks
        # Tip of index finger
        index_tip = landmarks[8]
        # Tip of thumb
        thumb_tip = landmarks[4]
        # Base of index finger
        index_base = landmarks[5]

        # Check if fingers are extended
        # Index finger extended: tip y is above mcp y
        index_extended = landmarks[8][1] < landmarks[6][1]
        # Thumb extended: tip x is to the side of IP
        thumb_extended = abs(landmarks[4][0] - landmarks[3][0]) > 20

        if index_extended and thumb_extended:
            return "pointing"
        elif not index_extended and not thumb_extended:
            return "fist"
        else:
            return "open"

    def release(self):
        """Release MediaPipe resources."""
        self._running = False
        if self.hands:
            try:
                self.hands.close()
            except Exception:
                pass