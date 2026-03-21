"""
============================================================
IoT Lab 2 - Raspberry Pi Bluetooth Server
============================================================
Run on the Raspberry Pi.
Uses the same PiCar-X API as Lab 1 code.

Usage:
    1. Pair PC with Pi via Bluetooth
    2. Run: python3 pi_bluetooth_server.py
    3. Then run pc_bluetooth_client.py on PC
============================================================
"""

import socket
import threading
import time
import json

from picarx import Picarx

# ---- Initialize PiCar-X ----
px = Picarx()

# ---- Settings (same defaults as your Lab 1) ----
MOVE_SPEED = 5
TURN_ANGLE = 30
RFCOMM_CHANNEL = 1

# ---- Car State ----
car_state = {
    "speed": 0,
    "direction": "stopped",
    "distance_traveled": 0.0,
    "steering_angle": 0,
    "obstacle_dist": 999.0,
}

state_lock = threading.Lock()
last_move_time = None
running = True


# ============================================================
# Sensor Functions (from your Lab 1 code)
# ============================================================

def get_front_dist():
    """Ultrasonic distance with 3-sample averaging (your Lab 1 method)."""
    vals = []
    for _ in range(3):
        d = px.ultrasonic.read()
        if d > 0:
            vals.append(d)
        time.sleep(0.05)
    return round(sum(vals) / len(vals), 1) if vals else 999.0


def get_cpu_temperature():
    """Read Pi CPU temperature from sysfs."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = float(f.read().strip()) / 1000.0
        return round(temp, 1)
    except Exception:
        return 0.0


def get_battery_voltage():
    """Read battery voltage via robot_hat ADC."""
    try:
        from robot_hat import ADC
        adc = ADC("A4")
        raw = adc.read()
        voltage = raw * 3.3 / 4095 * 3
        return round(voltage, 2)
    except Exception:
        return 7.4


def get_battery_percentage(voltage):
    """2S LiPo: 6.0V=0%, 8.4V=100%."""
    if voltage <= 6.0:
        return 0
    elif voltage >= 8.4:
        return 100
    return int((voltage - 6.0) / 2.4 * 100)


# ============================================================
# Movement Commands (matching your Lab 1 API usage)
# ============================================================

def execute_command(command):
    """Execute movement command on PiCar-X."""
    global last_move_time
    command = command.strip().lower()
    print(f"[CMD] {command}")

    with state_lock:
        if command == "forward":
            px.set_dir_servo_angle(0)
            px.forward(MOVE_SPEED)
            car_state["direction"] = "forward"
            car_state["speed"] = MOVE_SPEED
            car_state["steering_angle"] = 0
            last_move_time = time.time()

        elif command == "backward":
            px.set_dir_servo_angle(0)
            px.backward(MOVE_SPEED)
            car_state["direction"] = "backward"
            car_state["speed"] = MOVE_SPEED
            car_state["steering_angle"] = 0
            last_move_time = time.time()

        elif command == "left":
            px.set_dir_servo_angle(-TURN_ANGLE)
            px.forward(MOVE_SPEED)
            car_state["direction"] = "left"
            car_state["speed"] = MOVE_SPEED
            car_state["steering_angle"] = -TURN_ANGLE
            last_move_time = time.time()

        elif command == "right":
            px.set_dir_servo_angle(TURN_ANGLE)
            px.forward(MOVE_SPEED)
            car_state["direction"] = "right"
            car_state["speed"] = MOVE_SPEED
            car_state["steering_angle"] = TURN_ANGLE
            last_move_time = time.time()

        elif command == "stop":
            px.stop()
            px.set_dir_servo_angle(0)
            car_state["direction"] = "stopped"
            car_state["speed"] = 0
            car_state["steering_angle"] = 0
            last_move_time = None


# ============================================================
# Background Threads
# ============================================================

def distance_tracker():
    """Accumulate distance traveled."""
    while running:
        with state_lock:
            if last_move_time and car_state["speed"] > 0:
                car_state["distance_traveled"] += car_state["speed"] * 0.1
                car_state["distance_traveled"] = round(
                    car_state["distance_traveled"], 1
                )
        time.sleep(0.1)


def sensor_updater():
    """Periodically read ultrasonic sensor."""
    while running:
        dist = get_front_dist()
        with state_lock:
            car_state["obstacle_dist"] = dist
        time.sleep(0.3)


# ============================================================
# Status JSON
# ============================================================

def build_status_json():
    """Build JSON with all car status data."""
    voltage = get_battery_voltage()
    with state_lock:
        status = {
            "cpu_temp": get_cpu_temperature(),
            "battery_voltage": voltage,
            "battery_percent": get_battery_percentage(voltage),
            "speed": car_state["speed"],
            "direction": car_state["direction"],
            "distance_traveled": car_state["distance_traveled"],
            "steering_angle": car_state["steering_angle"],
            "obstacle_dist": car_state["obstacle_dist"],
            "timestamp": time.strftime("%H:%M:%S"),
        }
    return json.dumps(status)


# ============================================================
# Bluetooth Client Handler
# ============================================================

def handle_client(client_sock, client_info):
    print(f"[CONN] Connected: {client_info}")
    try:
        while True:
            data = client_sock.recv(1024)
            if not data:
                break
            message = data.decode("utf-8").strip()
            if message == "GET_STATUS":
                response = build_status_json()
            else:
                execute_command(message)
                response = build_status_json()
            client_sock.send(response.encode("utf-8"))
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        client_sock.close()
        execute_command("stop")
        print(f"[DISC] Disconnected: {client_info}")


# ============================================================
# Main
# ============================================================

def main():
    global running

    threading.Thread(target=distance_tracker, daemon=True).start()
    threading.Thread(target=sensor_updater, daemon=True).start()

    server_sock = socket.socket(
        socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM
    )
    server_sock.bind(("", RFCOMM_CHANNEL))
    server_sock.listen(1)

    print("=" * 50)
    print("  IoT Lab 2 - Pi Bluetooth Server")
    print(f"  Speed={MOVE_SPEED}, Angle={TURN_ANGLE}")
    print("  Waiting for Bluetooth connection...")
    print("=" * 50)

    try:
        while True:
            client_sock, client_info = server_sock.accept()
            threading.Thread(
                target=handle_client,
                args=(client_sock, client_info),
                daemon=True,
            ).start()
    except KeyboardInterrupt:
        print("\n[EXIT] Shutting down...")
    finally:
        running = False
        px.stop()
        px.set_dir_servo_angle(0)
        server_sock.close()


if __name__ == "__main__":
    main()
