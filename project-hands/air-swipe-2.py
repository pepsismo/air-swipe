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
SWIPE_THRESHOLD = 70  # Aumentado para menos sensibilidad
PINCH_THRESHOLD = 30  # Reducido para requerir dedos más juntos
GESTURE_COOLDOWN = 1.0 # Tiempo en segundos para evitar detecciones múltiples
MOVEMENT_IDLE_THRESHOLD = 15 # Cuánto debe moverse la mano antes de mover la ventana (píxeles)

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
last_pinch_pos_x = 0 # Para controlar el movimiento inicial de la pinza
last_pinch_pos_y = 0

# --- Modo de Operación ---
active_mode = False # False: Modo Vista (solo muestra), True: Modo Activo (ejecuta comandos)
MODE_TOGGLE_KEY = 'm' # Tecla para alternar entre modos

# Captura de video
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: No se pudo abrir la cámara.")
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print(f"Cámara abierta. Presiona '{MODE_TOGGLE_KEY}' para alternar entre Modo Activo/Vista. Presiona 'q' para salir.")

def press_and_release(keys):
    """Presiona y suelta un conjunto de teclas."""
    if active_mode: # Solo ejecuta si estamos en modo activo
        for key in keys:
            keyboard_controller.press(key)
        for key in reversed(keys):
            keyboard_controller.release(key)
        return True # Indica que el comando fue ejecutado
    return False # Indica que no se ejecutó porque no estaba en modo activo

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
        print("Error: No se pudo leer el frame de la cámara.")
        break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)
    image_display = frame.copy()

    gesture_text = "Esperando gesto..."
    mode_text = "MODO: VISTA (Press 'm' to activate)"
    if active_mode:
        mode_text = "MODO: ACTIVO (Press 'm' to view)"

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

                    if active_mode and gw:
                        active_window = get_active_window()
                        if active_window:
                            grabbed_window = active_window
                            window_grab_offset_x = current_finger_x - grabbed_window.left
                            window_grab_offset_y = current_finger_y - grabbed_window.top
                            last_pinch_pos_x, last_pinch_pos_y = current_finger_x, current_finger_y # Guardar posición inicial de la pinza
                            print(f"Ventana '{grabbed_window.title}' agarrada.")
                        else:
                            print("No se pudo obtener la ventana activa.")
                            grabbed_window = None
                
                # Si la pinza está activa, y estamos en modo activo y tenemos una ventana agarrada
                if is_pinching and active_mode and grabbed_window:
                    gesture_text = "Moviendo ventana..."
                    
                    # Calcular el desplazamiento desde la posición inicial de la pinza para el umbral
                    dx_pinch = current_finger_x - last_pinch_pos_x
                    dy_pinch = current_finger_y - last_pinch_pos_y

                    # Mover solo si la mano se ha movido lo suficiente
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
                
                # --- Detección de Swipes (solo si no hay pinza activa y en cooldown) ---
                elif not gesture_detected and (current_time - last_gesture_time) > GESTURE_COOLDOWN:
                    if swipe_start_x == 0 and swipe_start_y == 0:
                        swipe_start_x, swipe_start_y = current_finger_x, current_finger_y
                    
                    dx = current_finger_x - swipe_start_x
                    dy = current_finger_y - swipe_start_y

                    if abs(dx) > SWIPE_THRESHOLD or abs(dy) > SWIPE_THRESHOLD:
                        gesture_detected = True
                        last_gesture_time = current_time

                        # Solo ejecutar comando si press_and_release retorna True (modo activo)
                        executed = False
                        if abs(dx) > abs(dy):
                            if dx > SWIPE_THRESHOLD:
                                gesture_text = "Swipe a la Derecha!"
                                executed = press_and_release([keyboard.Key.alt, keyboard.Key.tab])
                                if executed: print("Activado: Alt + Tab")
                            elif dx < -SWIPE_THRESHOLD:
                                gesture_text = "Swipe a la Izquierda!"
                                executed = press_and_release([keyboard.Key.cmd, keyboard.KeyCode.from_char('d')])
                                if executed: print("Activado: Win + D")
                        else:
                            if dy > SWIPE_THRESHOLD:
                                gesture_text = "Swipe Abajo!"
                                executed = press_and_release([keyboard.Key.cmd, keyboard.Key.down])
                                if executed: print("Activado: Win + Abajo")
                            elif dy < -SWIPE_THRESHOLD:
                                gesture_text = "Swipe Arriba!"
                                executed = press_and_release([keyboard.Key.cmd, keyboard.Key.up])
                                if executed: print("Activado: Win + Arriba")
                        
                        if not executed and active_mode:
                            print(f"Gesto '{gesture_text}' no ejecutado (¿ya activo?).")
                        elif not executed and not active_mode:
                            print(f"Gesto '{gesture_text}' detectado (Modo Vista).")
                
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
    cv2.putText(image_display, mode_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2, cv2.LINE_AA) # Texto del modo
    cv2.imshow('Hand Gesture Control', image_display)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord(MODE_TOGGLE_KEY): # Alternar modo con la tecla 'm'
        active_mode = not active_mode
        print(f"Modo cambiado a: {'ACTIVO' if active_mode else 'VISTA'}")
        # Resetear estados al cambiar de modo para evitar activaciones inesperadas
        is_pinching = False
        grabbed_window = None
        gesture_detected = False
        swipe_start_x = 0
        swipe_start_y = 0

cap.release()
cv2.destroyAllWindows()
hands.close()