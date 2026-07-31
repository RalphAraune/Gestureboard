import cv2
import mediapipe as mp
import time

# ------------------------
# MediaPipe Setup
# ------------------------
mp_hands = mp.solutions.hands

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)

# ------------------------
# Variables
# ------------------------
command = "Waiting..."
cooldown = 0.8      # 800 ms debounce
last_command_time = 0

# ------------------------
# Finger Detection
# ------------------------
def fingers_up(hand_landmarks, hand_label):

    fingers = []

    # Thumb
    if hand_label == "Right":
        fingers.append(
            1 if hand_landmarks.landmark[4].x <
                 hand_landmarks.landmark[3].x else 0
        )
    else:
        fingers.append(
            1 if hand_landmarks.landmark[4].x >
                 hand_landmarks.landmark[3].x else 0
        )

    # Index
    fingers.append(
        1 if hand_landmarks.landmark[8].y <
             hand_landmarks.landmark[6].y else 0
    )

    # Middle
    fingers.append(
        1 if hand_landmarks.landmark[12].y <
             hand_landmarks.landmark[10].y else 0
    )

    # Ring
    fingers.append(
        1 if hand_landmarks.landmark[16].y <
             hand_landmarks.landmark[14].y else 0
    )

    # Pinky
    fingers.append(
        1 if hand_landmarks.landmark[20].y <
             hand_landmarks.landmark[18].y else 0
    )

    return fingers


# ------------------------
# Main Loop
# ------------------------
while True:

    success, frame = cap.read()

    if not success:
        break

    frame = cv2.flip(frame, 1)

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    results = hands.process(rgb)

    current_time = time.time()

    if results.multi_hand_landmarks:

        hand = results.multi_hand_landmarks[0]
        handedness = results.multi_handedness[0]

        hand_label = handedness.classification[0].label

        mp_draw.draw_landmarks(
            frame,
            hand,
            mp_hands.HAND_CONNECTIONS
        )

        fingers = fingers_up(hand, hand_label)

        # ------------------------
        # Gesture Recognition
        # ------------------------

        if current_time - last_command_time > cooldown:

            # 👍 START
            if fingers == [1,0,0,0,0]:
                command = "START PRESENTATION"
                last_command_time = current_time

            # 🤘 STOP
            elif fingers == [1,1,0,0,1]:
                command = "STOP PRESENTATION"
                last_command_time = current_time

            # ✌ NEXT
            elif fingers == [0,1,1,0,0]:
                command = "NEXT SLIDE"
                last_command_time = current_time

            # 🖖 PREVIOUS
            elif fingers == [0,1,1,1,0]:
                command = "PREVIOUS SLIDE"
                last_command_time = current_time

        # ------------------------
        # Debug Information
        # ------------------------

        cv2.putText(
            frame,
            f"Hand : {hand_label}",
            (20,90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255,255,0),
            2
        )

        cv2.putText(
            frame,
            f"Fingers : {fingers}",
            (20,130),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0,255,255),
            2
        )

    # ------------------------
    # Display Command
    # ------------------------

    cv2.putText(
        frame,
        command,
        (20,50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0,255,0),
        3
    )

    cv2.imshow("Gesture Presentation Test", frame)

    key = cv2.waitKey(1)

    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()