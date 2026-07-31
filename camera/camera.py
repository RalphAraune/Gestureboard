import cv2

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Camera is not open")
    exit()

cv2.namedWindow("Live Video")

while True:
    ret, frame = cap.read()

    if not ret:
        print("Can't receive frame")
        break

    frame = cv2.flip(frame, 1)

    cv2.imshow("Live Video", frame)

    # Press Q to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    # Close if the user clicks the X button
    if cv2.getWindowProperty("Live Video", cv2.WND_PROP_VISIBLE) < 1:
        break

cap.release()
cv2.destroyAllWindows()