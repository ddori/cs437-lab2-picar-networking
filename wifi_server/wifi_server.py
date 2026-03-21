"""
============================================================
IoT Lab 2 - Raspberry Pi WiFi Server
============================================================
Run on the Raspberry Pi.
TCP socket server for Electron web app.
Same PiCar-X API as Lab 1 code.

Usage:
    1. Find Pi IP: ifconfig
    2. Run: python3 wifi_server.py
    3. Start Electron app on PC, enter Pi IP
============================================================
"""

import socket
import threading
import time
import json

from picarx import Picarx

# ---- Initialize PiCar-X ----
px = Picarx()

# ---- Settings ----
HOST = "0.0.0.0"
PORT = 65432
MOVE_SPEED = 5
TURN_ANGLE = 30

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
# Sensor Functions (from Lab 1)
# ============================================================

def get_front_dist():
    """Ultrasonic distance, 3-sample average."""
    vals = []
    for _ in range(3):
        d = px.ultrasonic.read()
        if d > 0:
            vals.append(d)
        time.sleep(0.05)
    return round(sum(vals) / len(vals), 1) if vals else 999.0


def get_cpu_temperature():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = float(f.read().strip()) / 1000.0
        return round(temp, 1)
    except Exception:
        return 0.0


def get_battery_voltage():
    try:
        from robot_hat import ADC
        adc = ADC("A4")
        raw = adc.read()
        voltage = raw * 3.3 / 4095 * 3
        return round(voltage, 2)
    except Exception:
        return 7.4


def get_battery_percentage(voltage):
    if voltage <= 6.0:
        return 0
    elif voltage >= 8.4:
        return 100
    return int((voltage - 6.0) / 2.4 * 100)


# ============================================================
# Movement Commands
# ============================================================

def execute_command(command):
    global last_move_time
    command = command.strip().lower()
    print(f"  [CMD] {command}")

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
    while running:
        with state_lock:
            if last_move_time and car_state["speed"] > 0:
                car_state["distance_traveled"] += car_state["speed"] * 0.1
                car_state["distance_traveled"] = round(
                    car_state["distance_traveled"], 1
                )
        time.sleep(0.1)


def sensor_updater():
    while running:
        dist = get_front_dist()
        with state_lock:
            car_state["obstacle_dist"] = dist
        time.sleep(0.3)


# ============================================================
# Status JSON
# ============================================================

def build_status_json():
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
# TCP Client Handler
# ============================================================

def handle_client(conn, addr):
    print(f"[CONN] Connected by {addr}")
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            # TCP can batch multiple messages, split by newline
            messages = data.decode("utf-8").strip().split("\n")
            for msg in messages:
                msg = msg.strip().replace("\r", "")
                if not msg:
                    continue
                if msg == "GET_STATUS":
                    response = build_status_json()
                else:
                    execute_command(msg)
                    response = build_status_json()
                conn.sendall((response + "\n").encode("utf-8"))
    except ConnectionResetError:
        print(f"[DISC] Client {addr} disconnected")
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        conn.close()
        execute_command("stop")
        print(f"[DISC] {addr} closed")


# ============================================================
# Main
# ============================================================

def main():
    global running

    threading.Thread(target=distance_tracker, daemon=True).start()
    threading.Thread(target=sensor_updater, daemon=True).start()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)

    # Show Pi's IP address
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "unknown"

    print("=" * 55)
    print("  IoT Lab 2 - Pi WiFi Server")
    print(f"  Listening on port {PORT}")
    print(f"  Pi IP address: {local_ip}")
    print(f"  -> Enter this IP in the Electron app")
    print(f"  Speed={MOVE_SPEED}, Angle={TURN_ANGLE}")
    print("=" * 55)

    try:
        while True:
            conn, addr = server.accept()
            threading.Thread(
                target=handle_client,
                args=(conn, addr),
                daemon=True,
            ).start()
    except KeyboardInterrupt:
        print("\n[EXIT] Shutting down...")
    finally:
        running = False
        px.stop()
        px.set_dir_servo_angle(0)
        server.close()


if __name__ == "__main__":
    main()
