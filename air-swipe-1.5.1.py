import cv2
import mediapipe as mp
from pynput import keyboard
import time
import math

try:
    import pygetwindow as gw
    import pyautogui
except ImportError:
    print("Errores en las librerias")
    gw = None
    pyautogui = None


#### inicia las manos de mediapipe ####

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    min_detection_confidence = 0.5,
    min_tracking_confidence = 0.5,
    max_num_hands = 2
)

mp_draw = mp.solutions.drawing_utils

keyboard_controller = keyboard.Controller()

#### variables de sensibilidad ####

SWIPE_THRESHOLD = 70
PINCH_THRESHOLD = 30
GESTURE_COOLDOWN = 1.0
MOVEMENT_IDLE_THRESHOLD = 15

swipe_start_x = 0
swipe_start_y = 0
current_finger_x = 0
current_finger_y = 0
gesture_detected = False
last_gesture_time = time.time()

is_pinching = False
window_grab_offset_x = 0
window_grab_offset_y = 0
grabbed_window = None
last_pinch_pos_x = 0
last_pinch_pos_y = 0


#### control de la camara ####

current_camera_index = 0
CAMERA_TOGGLE_KEY = 'c'

cap = None

def open_camera(index):

    new_cap = cv2.VideoCapture(index)
    if not new_cap.isOpened():
        print(f"error abriendo la camara")
        return None
    new_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    new_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    print(f"camara abierta")
    return new_cap

## abre la primera camara ##

cap = open_camera(current_camera_index)

while cap is None:
    current_camera_index += 1
    if current_camera_index > 10:
        print(f"no se encontraron camaras disponibles")
        exit()
    cap = open_camera(current_camera_index)

print(f"todo funciona correctamente, presiona q para salir y c para cambiar de camara")

def press_and_release(keys):
    for key in keys:
        keyboard_controller.press(key)
    for key in reversed(keys):
        keyboard_controller.release(key)
    return True

def get_activated_window():
    if gw:
        try:
            return gw.getActiveWindow()
        except gw.PyGetWindowException:
            return None
    return None

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        print("error en la camara, reintentando")
        cap.release()

        current_camera_index += 1
        
        cap = open_camera(current_camera_index)

        if cap is None:
            print(f"Error leyendo la camara")
            break
        continue

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)
    image_display = frame.copy()

    gesture_text = "ESPERANDO..."
    camera_info_text = f"Cam: {current_camera_index}"

    current_time = time.time()

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(image_display, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]

            h, w, c = image_display.shape

            current_finger_x, current_finger_y = int(index_finger_tip.x * w), int(index_finger_tip.y * h)
            thumb_x, thumb_y = int(thumb_tip.x * w), int(thumb_tip.y * h)

            cv2.circle(image_display, (current_finger_x, current_finger_y), 8, (0, 255, 0), cv2.FILLED)
            cv2.circle(image_display, (thumb_x, thumb_y), 8, (255, 0, 0), cv2.FILLED)

            distance = math.hypot(current_finger_x - thumb_x, current_finger_y - thumb_y)

            ## deteccion de la pinza ##

            if distance < PINCH_THRESHOLD:
                if not is_pinching:
                    is_pinching = True
                    gesture_text = "pinch detected"
                    print("pinch detected")

                    if gw:
                        activate_window = get_activated_window()
                        if activate_window:
                            grabbed_window = activate_window
                            window_grab_offset_x = current_finger_x - grabbed_window.left
                            window_grab_offset_y = current_finger_y - grabbed_window.top
                            last_pinch_pos_x, last_pinch_pos_y = current_finger_x, current_finger_y

                            print(f"window {grabbed_window.title} grabbed")
                        else:
                            print(f"no se pudo obtener la ventana")
                            grabbed_window = None
                    
                if is_pinching and grabbed_window:
                    gesture_text = "moving window"

                    dx_pinch = current_finger_x - last_pinch_pos_x
                    dy_pinch = current_finger_y - last_pinch_pos_y

                    if abs(dx_pinch) > MOVEMENT_IDLE_THRESHOLD or abs(dy_pinch) > MOVEMENT_IDLE_THRESHOLD:
                        new_window_x = current_finger_x - window_grab_offset_x
                        new_window_y = current_finger_y - window_grab_offset_y

                        try:
                            grabbed_window.moveTo(new_window_x, new_window_y)
                        except gw.PyGetWindowException as e:
                            print(f"error in wondow {e}")
                            grabbed_window = None
                        except Exception as e:
                            print(f"unexpected error")
                            grabbed_window = None

            else:
                if is_pinching:
                    is_pinching = False
                    grabbed_window = None
                    print("pinch released")

                elif not gesture_detected and (current_time - last_gesture_time) > GESTURE_COOLDOWN:
                    if swipe_start_x == 0 and swipe_start_y == 0:
                        swipe_start_x, swipe_start_y = current_finger_x, current_finger_y

                    dx = current_finger_x - swipe_start_x
                    dy = current_finger_y - swipe_start_y

                    if abs(dx) > SWIPE_THRESHOLD or abs(dy) > SWIPE_THRESHOLD:
                        gesture_detected = True
                        last_gesture_time = current_time

                        executed = False
                        if abs(dx) > abs(dy):
                            if dx > SWIPE_THRESHOLD:
                                gesture_text = "swiped right"
                                executed = press_and_release([keyboard.Key.alt, keyboard.Key.tab])
                                if executed: print(f"alt + tab")
                            elif dx < SWIPE_THRESHOLD:
                                gesture_text = "swiped left"
                                executed = press_and_release([keyboard.Key.alt, keyboard.Key.tab])
                                if executed: print(f"alt + tab")
                        
                        else:
                            if dy > SWIPE_THRESHOLD:
                                gesture_text = "swiped down"
                                executed = press_and_release([keyboard.Key.cmd, keyboard.Key.down])
                                if executed: print(f"win + down")
                            elif dy < SWIPE_THRESHOLD:
                                gesture_text = "swiped up"
                                executed = press_and_release([keyboard.Key.cmd, keyboard.Key.up])
                                if executed: print(f"win + up")

                        if executed:
                            print(f"gesture {gesture_text} executed")
                        else:
                            print(f"error running command")

                elif gesture_detected and (current_time - last_gesture_time) > GESTURE_COOLDOWN:
                    gesture_detected = False
                    swipe_start_x = 0
                    swipe_start_y = 0

    else:
        gesture_detected = False
        swipe_start_x = 0
        swipe_start_y = 0
        is_pinching = False
        grabbed_window = None

#    cv2.putText(image_display, gesture_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
#    cv2.putText(image_display, camera_info_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2, cv2.LINE_AA)
    cv2.imshow('air-swipe', image_display)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord(CAMERA_TOGGLE_KEY):
        print(f"cambiando camara")
        if cap:
            cap.release()
        
        current_camera_index = (current_camera_index + 1) % 5

        new_cap = None
        attempts = 0
        max_attempts = 5

        while new_cap is None and attempts < max_attempts:
            new_cap = open_camera(current_camera_index)
            if new_cap is None:
                current_camera_index = (current_camera_index + 1) % 5
            attempts += 1

        if new_cap is None:
            print(f"couldn't find working cameras")
            break
        else:
            cap = new_cap
            gesture_detected = None
            swipe_start_x = 0
            swipe_start_y = 0
            is_pinching = False
            grabbed_window = None

if cap:
    cap.release()
cv2.destroyAllWindows()
hands.close()





