import cv2
import mediapipe as mp
from pynput import keyboard
import time
import math

try:
    import pygetwindow as gw
    import pyautogui
except ImportError:
    print("Las bibliotecas 'pygetwindow' o 'pyautogui' no están instaladas.")
    print("Por favor, instala: pip install pygetwindow pyautogui")
    gw = None
    pyautogui = None

# Inicializar MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
    max_num_hands=1
)
mp_draw = mp.solutions.drawing_utils

keyboard_controller = keyboard.Controller()

# --- Variables de control de sensibilidad y estado ---
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

# --- Control de Cámara ---
current_camera_index = 0  # Empezar con la cámara predeterminada (0)
CAMERA_TOGGLE_KEY = 'c'   # Tecla para cambiar de cámara

cap = None # Inicializamos cap como None

def open_camera(index):
    """Intenta abrir una cámara por su índice."""
    new_cap = cv2.VideoCapture(index)
    if not new_cap.isOpened():
        print(f"Advertencia: No se pudo abrir la cámara con índice {index}. Intentando la siguiente...")
        return None
    
    new_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    new_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    print(f"Cámara {index} abierta.")
    return new_cap

# Intentar abrir la primera cámara al inicio
cap = open_camera(current_camera_index)
while cap is None:
    current_camera_index += 1
    if current_camera_index > 10: # Límite para evitar bucles infinitos si no hay cámaras
        print("Error: No se encontró ninguna cámara disponible.")
        exit()
    cap = open_camera(current_camera_index)


print(f"Cámara {current_camera_index} activa. Presiona '{CAMERA_TOGGLE_KEY}' para cambiar de cámara. Presiona 'q' para salir.")

def press_and_release(keys):
    for key in keys:
        keyboard_controller.press(key)
    for key in reversed(keys):
        keyboard_controller.release(key)
    return True

def get_active_window():
    if gw:
        try:
            return gw.getActiveWindow()
        except gw.PyGetWindowException:
            return None
    return None

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        # Si la cámara se desconecta o hay un error, intentamos reabrirla
        print(f"Error al leer de la cámara {current_camera_index}. Intentando reabrir o cambiar...")
        cap.release()
        current_camera_index += 1
        cap = open_camera(current_camera_index)
        if cap is None: # Si la siguiente cámara tampoco funciona
            print("No hay más cámaras disponibles o todas fallaron.")
            break # Salir del bucle principal
        continue # Continuar al siguiente fotograma con la nueva cámara

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)
    image_display = frame.copy()

    gesture_text = "Esperando gesto..."
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

            # --- Detección de Pinza ---
            if distance < PINCH_THRESHOLD:
                if not is_pinching:
                    is_pinching = True
                    gesture_text = "Pinza Activa!"
                    print("Pinza detectada!")

                    if gw:
                        active_window = get_active_window()
                        if active_window:
                            grabbed_window = active_window
                            window_grab_offset_x = current_finger_x - grabbed_window.left
                            window_grab_offset_y = current_finger_y - grabbed_window.top
                            last_pinch_pos_x, last_pinch_pos_y = current_finger_x, current_finger_y
                            print(f"Ventana '{grabbed_window.title}' agarrada.")
                        else:
                            print("No se pudo obtener la ventana activa.")
                            grabbed_window = None
                
                if is_pinching and grabbed_window:
                    gesture_text = "Moviendo ventana..."
                    
                    dx_pinch = current_finger_x - last_pinch_pos_x
                    dy_pinch = current_finger_y - last_pinch_pos_y

                    if abs(dx_pinch) > MOVEMENT_IDLE_THRESHOLD or abs(dy_pinch) > MOVEMENT_IDLE_THRESHOLD:
                        new_window_x = current_finger_x - window_grab_offset_x
                        new_window_y = current_finger_y - window_grab_offset_y
                        
                        try:
                            grabbed_window.moveTo(new_window_x, new_window_y)
                        except gw.PyGetWindowException as e:
                            print(f"Error al mover la ventana: {e}")
                            grabbed_window = None
                        except Exception as e:
                            print(f"Error inesperado al mover la ventana: {e}")
                            grabbed_window = None

            else: # Pinza no activa
                if is_pinching:
                    is_pinching = False
                    grabbed_window = None
                    print("Pinza liberada.")
                
                # --- Detección de Swipes ---
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
                                gesture_text = "Swipe a la Derecha!"
                                executed = press_and_release([keyboard.Key.alt, keyboard.Key.tab])
                                if executed: print("Activado: Alt + Tab")
                            elif dx < -SWIPE_THRESHOLD:
                                gesture_text = "Swipe a la Izquierda!"
                                executed = press_and_release([keyboard.Key.alt, keyboard.Key.tab])
                                if executed: print("Activado: Alt + Tab")
                        else:
                            if dy > SWIPE_THRESHOLD:
                                gesture_text = "Swipe Abajo!"
                                executed = press_and_release([keyboard.Key.cmd, keyboard.Key.down])
                                if executed: print("Activado: Win + Abajo")
                            elif dy < -SWIPE_THRESHOLD:
                                gesture_text = "Swipe Arriba!"
                                executed = press_and_release([keyboard.Key.cmd, keyboard.Key.up])
                                if executed: print("Activado: Win + Arriba")
                        
                        if executed:
                            print(f"Gesto '{gesture_text}' ejecutado.")
                        else:
                             print(f"Gesto '{gesture_text}' detectado (no se pudo ejecutar el comando).")

                elif gesture_detected and (current_time - last_gesture_time) > GESTURE_COOLDOWN:
                    gesture_detected = False
                    swipe_start_x = 0
                    swipe_start_y = 0
    else: # No hay manos detectadas
        gesture_detected = False
        swipe_start_x = 0
        swipe_start_y = 0
        is_pinching = False
        grabbed_window = None

    cv2.putText(image_display, gesture_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
    cv2.putText(image_display, camera_info_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2, cv2.LINE_AA) # Información de la cámara
    cv2.imshow('Hand Gesture Control', image_display)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord(CAMERA_TOGGLE_KEY):
        print("Cambiando de cámara...")
        if cap:
            cap.release() # Liberar la cámara actual
        
        # Intentar la siguiente cámara
        current_camera_index = (current_camera_index + 1) % 5 # Probar hasta 5 cámaras (0 a 4)
                                                              # Ajusta este '5' si tienes más o menos cámaras
        new_cap = None
        attempts = 0
        max_attempts = 5 # Intentar un número limitado de veces para encontrar una cámara válida
        
        while new_cap is None and attempts < max_attempts:
            new_cap = open_camera(current_camera_index)
            if new_cap is None:
                current_camera_index = (current_camera_index + 1) % 5
            attempts += 1

        if new_cap is None:
            print("No se pudieron encontrar más cámaras disponibles.")
            break # Si no hay más cámaras, salir
        else:
            cap = new_cap
            # Resetear variables de gestos al cambiar de cámara para evitar activaciones fantasma
            gesture_detected = False
            swipe_start_x = 0
            swipe_start_y = 0
            is_pinching = False
            grabbed_window = None

# Liberar los recursos
if cap: # Asegurarse de que cap no sea None antes de liberar
    cap.release()
cv2.destroyAllWindows()
hands.close()