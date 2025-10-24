import cv2
import mediapipe as mp
import time

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
# hands = mp_hands.Hands() # Default parameters
# You can customize detection and tracking confidence for better performance in different lighting/distances
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils # Utility for drawing landmarks

# Open webcam
# 0 usually refers to the default webcam. If you have multiple, you might try 1, 2, etc.
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

print("Webcam opened successfully. Press 'q' to quit.")

# Variables for FPS calculation (optional)
pTime = 0 # Previous time
cTime = 0 # Current time

while True:
    # Read a frame from the webcam
    success, frame = cap.read()
    if not success:
        print("Error: Could not read frame from webcam.")
        break

    # Flip the frame horizontally for a mirror effect (optional, often preferred for webcam)
    frame = cv2.flip(frame, 1)

    # Convert the BGR image (OpenCV default) to RGB (MediaPipe requires RGB)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Process the frame and find hands
    # 'results' contains the detected hand landmarks and handedness (left/right)
    results = hands.process(rgb_frame)

    # Check if any hands were detected
    if results.multi_hand_landmarks:
        # Iterate through each hand detected
        for hand_landmarks in results.multi_hand_landmarks:
            # Draw landmarks on the original BGR frame
            # The mp_draw.draw_landmarks function draws dots (landmarks) and connections between them
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # Optionally, you can also get coordinates of specific landmarks
            # For example, to print the tip of the index finger:
            # For a more detailed breakdown of landmarks, refer to MediaPipe documentation
            # Index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            # h, w, c = frame.shape # Get frame dimensions
            # cx, cy = int(Index_finger_tip.x * w), int(Index_finger_tip.y * h)
            # cv2.circle(frame, (cx, cy), 10, (255, 0, 0), cv2.FILLED) # Draw a blue circle on the tip


    # Calculate and display FPS (optional)
    cTime = time.time()
    fps = 1 / (cTime - pTime)
    pTime = cTime
    cv2.putText(frame, f'FPS: {int(fps)}', (10, 30), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)

    # Display the frame
    cv2.imshow('PEP', frame)

    # Wait for 1ms and check if 'q' key is pressed to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the webcam and destroy all OpenCV windows
cap.release()
cv2.destroyAllWindows()