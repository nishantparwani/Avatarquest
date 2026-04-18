# arduino_bridge.py
import serial
import time

PORT = "COM3"
BAUD = 9600

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)

print("[OK] Connected")

last_state = "CLEAR"

def get_state():
    global last_state

    line = ser.readline().decode(errors="ignore").strip()

    if not line:
        return last_state

    if not line.startswith("PROX:"):
        return last_state

    value = int(line.split(":")[1])

    if value >= 4:
        last_state = "JUMP"
    elif value >= 2:
        last_state = "LEFT"
    else:
        last_state = "RIGHT"

    return last_state