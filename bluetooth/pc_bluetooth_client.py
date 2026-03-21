"""
============================================================
IoT Lab 2 - PC Bluetooth Client (Tkinter UI)
============================================================
Run on your PC (Windows/Linux, NOT in VM).
- Connects to Pi via Bluetooth RFCOMM
- GUI with directional buttons + keyboard control
- Displays car status: CPU temp, battery, speed,
  direction, steering, distance, obstacle dist

Prerequisites:
    - Python 3.9+ on Windows (for AF_BLUETOOTH)
    - Pi paired with PC
    - pi_bluetooth_server.py running on Pi

Usage:
    1. Change SERVER_MAC to your Pi's Bluetooth MAC
    2. Run: python3 pc_bluetooth_client.py
============================================================
"""

import socket
import threading
import json
import time
import tkinter as tk
from tkinter import messagebox

# ============================================================
# CHANGE THIS to your Pi's Bluetooth MAC address!
# Find it: on Pi run "bluetoothctl show" or "hciconfig"
# ============================================================
SERVER_MAC = "XX:XX:XX:XX:XX:XX"
RFCOMM_CHANNEL = 1


class CarControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("IoT Lab 2 - PiCar-X Bluetooth Controller")
        self.root.geometry("680x700")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        self.sock = None
        self.connected = False
        self.polling = False

        self.setup_ui()
        self.bind_keys()

    def setup_ui(self):
        # Title
        tk.Label(
            self.root, text="PiCar-X Bluetooth Remote",
            font=("Helvetica", 20, "bold"),
            fg="#cdd6f4", bg="#1e1e2e",
        ).pack(pady=(15, 5))

        # Connection
        conn_frame = tk.Frame(self.root, bg="#1e1e2e")
        conn_frame.pack(pady=5)

        self.conn_label = tk.Label(
            conn_frame, text="● Disconnected",
            font=("Helvetica", 12), fg="#f38ba8", bg="#1e1e2e",
        )
        self.conn_label.pack(side=tk.LEFT, padx=10)

        self.conn_btn = tk.Button(
            conn_frame, text="Connect", font=("Helvetica", 11, "bold"),
            bg="#a6e3a1", fg="#1e1e2e", width=12,
            command=self.toggle_connection,
        )
        self.conn_btn.pack(side=tk.LEFT, padx=10)

        # ---- Control Buttons ----
        ctrl_frame = tk.LabelFrame(
            self.root, text=" Controls ",
            font=("Helvetica", 13, "bold"),
            fg="#cdd6f4", bg="#1e1e2e", labelanchor="n",
        )
        ctrl_frame.pack(pady=15, padx=20)

        btn_cfg = dict(
            font=("Helvetica", 18, "bold"), width=5, height=2,
            bg="#89b4fa", fg="#1e1e2e", activebackground="#74c7ec",
            relief="raised", bd=3,
        )

        inner = tk.Frame(ctrl_frame, bg="#1e1e2e")
        inner.pack(pady=15, padx=30)

        tk.Button(inner, text="▲\nFwd",
                  command=lambda: self.send("forward"), **btn_cfg
                  ).grid(row=0, column=1, padx=5, pady=5)

        tk.Button(inner, text="◀\nLeft",
                  command=lambda: self.send("left"), **btn_cfg
                  ).grid(row=1, column=0, padx=5, pady=5)

        tk.Button(inner, text="■\nStop",
                  command=lambda: self.send("stop"),
                  font=("Helvetica", 18, "bold"), width=5, height=2,
                  bg="#f38ba8", fg="#1e1e2e", activebackground="#eba0ac",
                  relief="raised", bd=3,
                  ).grid(row=1, column=1, padx=5, pady=5)

        tk.Button(inner, text="▶\nRight",
                  command=lambda: self.send("right"), **btn_cfg
                  ).grid(row=1, column=2, padx=5, pady=5)

        tk.Button(inner, text="▼\nBwd",
                  command=lambda: self.send("backward"), **btn_cfg
                  ).grid(row=2, column=1, padx=5, pady=5)

        tk.Label(inner, text="Keyboard: Arrow keys / WASD, Space=Stop",
                 font=("Consolas", 10), fg="#6c7086", bg="#1e1e2e",
                 ).grid(row=3, column=0, columnspan=3, pady=(10, 0))

        # ---- Status Display ----
        stat_frame = tk.LabelFrame(
            self.root, text=" Car Status ",
            font=("Helvetica", 13, "bold"),
            fg="#cdd6f4", bg="#1e1e2e", labelanchor="n",
        )
        stat_frame.pack(pady=10, padx=20, fill=tk.X)

        stat_inner = tk.Frame(stat_frame, bg="#1e1e2e")
        stat_inner.pack(pady=10, padx=15, fill=tk.X)

        lbl_cfg = dict(font=("Consolas", 12), fg="#a6adc8", bg="#1e1e2e", anchor="w")
        val_cfg = dict(font=("Consolas", 13, "bold"), fg="#f9e2af", bg="#1e1e2e", anchor="w")

        items = [
            ("CPU Temperature:", "cpu_temp", "-- °C"),
            ("Battery:", "battery", "--%  (--V)"),
            ("Speed:", "speed", "--"),
            ("Direction:", "direction", "--"),
            ("Steering Angle:", "steering", "-- °"),
            ("Distance Traveled:", "distance", "-- cm"),
            ("Obstacle Distance:", "obstacle", "-- cm"),
            ("Last Update:", "timestamp", "--:--:--"),
        ]

        self.vals = {}
        for i, (label, key, default) in enumerate(items):
            tk.Label(stat_inner, text=label, **lbl_cfg).grid(
                row=i, column=0, sticky="w", padx=(10, 5), pady=2
            )
            v = tk.Label(stat_inner, text=default, **val_cfg)
            v.grid(row=i, column=1, sticky="w", padx=(5, 10), pady=2)
            self.vals[key] = v

        # Log
        self.log_label = tk.Label(
            self.root, text="Ready. Press Connect.",
            font=("Consolas", 10), fg="#6c7086", bg="#1e1e2e",
        )
        self.log_label.pack(pady=5)

    def bind_keys(self):
        self.root.bind("<Up>", lambda e: self.send("forward"))
        self.root.bind("<Down>", lambda e: self.send("backward"))
        self.root.bind("<Left>", lambda e: self.send("left"))
        self.root.bind("<Right>", lambda e: self.send("right"))
        self.root.bind("<space>", lambda e: self.send("stop"))
        self.root.bind("w", lambda e: self.send("forward"))
        self.root.bind("s", lambda e: self.send("backward"))
        self.root.bind("a", lambda e: self.send("left"))
        self.root.bind("d", lambda e: self.send("right"))
        self.root.bind("q", lambda e: self.send("stop"))

    # ---- Connection ----
    def toggle_connection(self):
        if self.connected:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        if SERVER_MAC == "XX:XX:XX:XX:XX:XX":
            messagebox.showerror(
                "Setup Required",
                "Edit pc_bluetooth_client.py and set\n"
                "SERVER_MAC to your Pi's Bluetooth MAC address!\n\n"
                "Find it on Pi: bluetoothctl show",
            )
            return

        self.log("Connecting...")
        self.conn_btn.config(state=tk.DISABLED)

        def do_connect():
            try:
                self.sock = socket.socket(
                    socket.AF_BLUETOOTH, socket.SOCK_STREAM,
                    socket.BTPROTO_RFCOMM,
                )
                self.sock.connect((SERVER_MAC, RFCOMM_CHANNEL))
                self.connected = True

                self.root.after(0, lambda: self.conn_label.config(
                    text="● Connected", fg="#a6e3a1"))
                self.root.after(0, lambda: self.conn_btn.config(
                    text="Disconnect", bg="#f38ba8", state=tk.NORMAL))
                self.root.after(0, lambda: self.log("Connected!"))

                self.polling = True
                threading.Thread(target=self.poll_status, daemon=True).start()

            except Exception as e:
                self.root.after(0, lambda: self.log(f"Failed: {e}"))
                self.root.after(0, lambda: self.conn_btn.config(state=tk.NORMAL))

        threading.Thread(target=do_connect, daemon=True).start()

    def disconnect(self):
        self.polling = False
        self.connected = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        self.conn_label.config(text="● Disconnected", fg="#f38ba8")
        self.conn_btn.config(text="Connect", bg="#a6e3a1")
        self.log("Disconnected.")

    # ---- Communication ----
    def send(self, command):
        if not self.connected:
            self.log("Not connected!")
            return

        def do_send():
            try:
                self.sock.send(command.encode("utf-8"))
                data = self.sock.recv(4096)
                if data:
                    status = json.loads(data.decode("utf-8"))
                    self.root.after(0, lambda: self.update_status(status))
                    self.root.after(0, lambda: self.log(f"Sent: {command}"))
            except Exception as e:
                self.root.after(0, lambda: self.log(f"Error: {e}"))
                self.root.after(0, self.disconnect)

        threading.Thread(target=do_send, daemon=True).start()

    def poll_status(self):
        while self.polling and self.connected:
            try:
                self.sock.send("GET_STATUS".encode("utf-8"))
                data = self.sock.recv(4096)
                if data:
                    status = json.loads(data.decode("utf-8"))
                    self.root.after(0, lambda s=status: self.update_status(s))
            except Exception:
                break
            time.sleep(2)

    def update_status(self, s):
        try:
            self.vals["cpu_temp"].config(text=f"{s.get('cpu_temp', 0)} °C")
            bp = s.get("battery_percent", 0)
            bv = s.get("battery_voltage", 0)
            self.vals["battery"].config(text=f"{bp}%  ({bv}V)")
            self.vals["speed"].config(text=f"{s.get('speed', 0)}")
            self.vals["direction"].config(text=f"{s.get('direction', '--')}")
            self.vals["steering"].config(text=f"{s.get('steering_angle', 0)} °")
            self.vals["distance"].config(text=f"{s.get('distance_traveled', 0)} cm")
            self.vals["obstacle"].config(text=f"{s.get('obstacle_dist', 999)} cm")
            self.vals["timestamp"].config(text=f"{s.get('timestamp', '--')}")
        except Exception:
            pass

    def log(self, msg):
        self.log_label.config(text=msg)

    def on_close(self):
        self.polling = False
        if self.connected:
            try:
                self.sock.send("stop".encode("utf-8"))
            except Exception:
                pass
            self.disconnect()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = CarControlApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
