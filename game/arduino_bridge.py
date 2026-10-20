# arduino_bridge.py
# Reads the proximity sensor over serial ("PROX:<value>" lines) and turns it into a move.
# No Arduino plugged in (or pyserial missing)? The game still runs on the keyboard alone.
import time

PORT = "COM3"
BAUD = 9600

ser = None
try:
    import serial
    ser = serial.Serial(PORT, BAUD, timeout=0.01)
    time.sleep(2)
    print(f"[OK] Arduino connected on {PORT}")
except Exception as e:  # no board, wrong port, or pyserial not installed
    print(f"[INFO] No Arduino on {PORT} ({e.__class__.__name__}); keyboard only.")

last_state = "CLEAR"


def get_state():
    global last_state
    if ser is None:
        return "CLEAR"

    line = ser.readline().decode(errors="ignore").strip()

    if not line:
        return last_state

    if not line.startswith("PROX:"):
        return last_state

    try:
        value = int(line.split(":")[1])
    except ValueError:  # half a line arrived; keep the last move
        return last_state

    if value >= 4:
        last_state = "JUMP"
    elif value >= 2:
        last_state = "LEFT"
    else:
        last_state = "RIGHT"

    return last_state
