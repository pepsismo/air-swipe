import cv2
import mediapipe as mp
import pyautogui
import time

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

# Open webcam
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

print("Webcam opened successfully. Move your INDEX FINGER to control. Press 'q' to quit.")

# Variables for tracking index finger tip
prev_index_tip_x = 0
prev_index_tip_y = 0
tracking_initialized = False # To ensure we have a starting point

# Gesture parameters
gesture_threshold = 40  # Pixels for a "swipe" with the finger
last_gesture_time = time.time()
gesture_cooldown = 1.0  # Seconds to prevent rapid re-triggering of gestures

# Drawing options (optional: make index finger tip stand out)
draw_circle_radius = 15
draw_circle_color = (0, 255, 255) # Yellow
draw_circle_thickness = cv2.FILLED

# For FPS calculation
pTime = 0

while True:
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1) # Mirror effect
    h, w, c = frame.shape # Get frame dimensions

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # Draw all hand landmarks (optional, can be removed if you only want the finger tip)
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # Get the coordinates of the Index Finger Tip (landmark #8)
            # MediaPipe's landmark list: https://google.github.io/mediapipe/solutions/hands.html
            index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            current_index_tip_x = int(index_finger_tip.x * w)
            current_index_tip_y = int(index_finger_tip.y * h)

            # Draw a circle on the index finger tip to highlight it
            cv2.circle(frame, (current_index_tip_x, current_index_tip_y),
                       draw_circle_radius, draw_circle_color, draw_circle_thickness)

            # Initialize tracking on the first detection
            if not tracking_initialized:
                prev_index_tip_x = current_index_tip_x
                prev_index_tip_y = current_index_tip_y
                tracking_initialized = True
                last_gesture_time = time.time() # Reset cooldown on first detection
                continue # Skip gesture detection for the very first frame

            # --- Gesture Detection Logic ---
            if time.time() - last_gesture_time > gesture_cooldown:
                # Calculate movement differentials
                dx = current_index_tip_x - prev_index_tip_x
                dy = current_index_tip_y - prev_index_tip_y

                # Check for horizontal swipe (Alt+Tab)
                if abs(dx) > gesture_threshold and abs(dy) < gesture_threshold / 2: # Prioritize dominant horizontal movement
                    if dx > 0:
                        print("Index Finger Swipe Right - Alt+Tab")
                        pyautogui.hotkey('alt', 'tab')
                        last_gesture_time = time.time()
                    else:
                        print("Index Finger Swipe Left - Alt+Tab")
                        pyautogui.hotkey('alt', 'tab')
                        last_gesture_time = time.time()
                
                # Check for vertical swipe (Show Desktop)
                elif abs(dy) > gesture_threshold * 1.5 and abs(dx) < gesture_threshold / 2: # Larger threshold for vertical, dominant vertical
                    if dy < 0: # Moving up means smaller Y coordinate
                        print("Index Finger Swipe Up - Show Desktop")
                        pyautogui.hotkey('win', 'd')
                        last_gesture_time = time.time()
                    # You could add a 'Swipe Down' for another action if needed
                    # elif dy > 0:
                    #     print("Index Finger Swipe Down")
                    #     pyautogui.hotkey('win', 'r')
                    #     last_gesture_time = time.time()

            # Update previous position for the next frame
            prev_index_tip_x = current_index_tip_x
            prev_index_tip_y = current_index_tip_y
            
    # Calculate and display FPS (optional)
    cTime = time.time()
    fps = 1 / (cTime - pTime)
    pTime = cTime
    cv2.putText(frame, f'FPS: {int(fps)}', (10, 30), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)

    cv2.imshow('Index Finger Gesture Control', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()