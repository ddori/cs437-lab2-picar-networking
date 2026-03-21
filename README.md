# IoT Lab 2 - PiCar-X Networking (Bluetooth + WiFi)
CS 437 Internet of Things @ UIUC

## Project Structure

```
cs437-lab2-picar-networking/
├── bluetooth/                     ← Bluetooth (bonus 5 pts)
│   ├── pi_bluetooth_server.py     ← Run on Raspberry Pi
│   └── pc_bluetooth_client.py     ← Run on PC (Tkinter GUI)
├── wifi_server/                   ← WiFi server (main)
│   └── wifi_server.py             ← Run on Raspberry Pi
├── electron_app/                  ← Electron frontend (main)
│   ├── package.json
│   ├── main.js
│   ├── preload.js
│   ├── index.html
│   └── index.js
└── README.md
```

## PiCar-X Integration

Both Pi server scripts use the same PiCar-X API from Lab 1:

- `from picarx import Picarx` / `px = Picarx()`
- `px.forward(speed)` / `px.backward(speed)` / `px.stop()`
- `px.set_dir_servo_angle(angle)` (-30 to +30)
- `px.ultrasonic.read()` (3-sample average with zero filtering)
- Default speed: 5, turn angle: 30 (same as Lab 1)

## Data Transmitted (8 fields, exceeds the minimum 3 requirement)

### Pi to PC (Status)

| Field              | Description                                      |
|--------------------|--------------------------------------------------|
| cpu_temp           | CPU temperature (C)                              |
| battery_percent    | Battery level (%)                                |
| battery_voltage    | Battery voltage (V)                              |
| speed              | Current motor speed                              |
| direction          | Movement direction (forward/backward/left/right/stopped) |
| steering_angle     | Steering servo angle (deg)                       |
| distance_traveled  | Accumulated travel distance (cm)                 |
| obstacle_dist      | Ultrasonic obstacle distance (cm)                |

### PC to Pi (Commands)

| Command     | Action           |
|-------------|------------------|
| forward     | Drive forward    |
| backward    | Drive backward   |
| left        | Turn left        |
| right       | Turn right       |
| stop        | Stop all motors  |
| GET_STATUS  | Request status   |

---

## How to Run

### Bluetooth (Bonus)

**Pi setup (one time):**
```bash
# Edit bluez.service (see lab document for details)
sudo nano /etc/systemd/system/dbus-org.bluez.service
# Add -C to the end of the ExecStart line
# Add line: ExecStartPost=/usr/bin/sdptool add SP
sudo systemctl daemon-reload
sudo systemctl restart bluetooth.service
```

**On Raspberry Pi:**
```bash
python3 pi_bluetooth_server.py
```

**On PC:**
1. Open `pc_bluetooth_client.py` and set `SERVER_MAC` to your Pi's Bluetooth MAC address
   (Find it on Pi: `bluetoothctl show`)
2. Run:
```bash
python3 pc_bluetooth_client.py
```

### WiFi + Electron (Main)

**On Raspberry Pi:**
```bash
python3 wifi_server.py
# Note the IP address printed on startup
```

**On PC:**
```bash
cd electron_app
npm install     # first time only
npm start
```
Enter the Pi's IP address in the app, click Connect, then control the car using buttons or keyboard.

---

## Keyboard Shortcuts (both Bluetooth and Electron)

| Key         | Action    |
|-------------|-----------|
| Up / W      | Forward   |
| Down / S    | Backward  |
| Left / A    | Turn left |
| Right / D   | Turn right|
| Space / Q   | Stop      |
