"""
File: ui/ui_manager.py
Defines the UIManager class, which encapsulates the Tkinter GUI,
updates sensor readings, volume, connection status, and logs.
"""

import time
import tkinter as tk

class UIManager:
    """
    Manages the Tkinter user interface.
    """
    def __init__(self, root: tk.Tk):
        self.root = root
        self.last_log_time = 0
        self.LOG_INTERVAL = 2.0
        self.last_volume_disabled_logged = False
        self.setup_gui()

    def setup_gui(self):
        self.root.title("BLE Gyro Volume Controller")
        # Connection status frame with icon and label
        self.conn_frame = tk.Frame(self.root)
        self.conn_frame.pack(pady=5)
        self.conn_status_icon = tk.Label(self.conn_frame, text="❌", font=("Arial", 16))
        self.conn_status_icon.pack(side=tk.LEFT, padx=5)
        self.conn_status_label = tk.Label(self.conn_frame, text="BLE: Not connected", font=("Arial", 12))
        self.conn_status_label.pack(side=tk.LEFT)
        # Volume display label
        self.volume_label = tk.Label(self.root, text="Windows Volume: 0%", font=("Arial", 16))
        self.volume_label.pack(pady=5)
        # Sensor values display: Roll, Pitch, Yaw
        self.sensor_frame = tk.Frame(self.root)
        self.sensor_frame.pack(pady=5)
        self.roll_label = tk.Label(self.sensor_frame, text="Roll: 0.00", font=("Arial", 14))
        self.roll_label.grid(row=0, column=0, padx=5)
        self.pitch_label = tk.Label(self.sensor_frame, text="Pitch: 0.00", font=("Arial", 14))
        self.pitch_label.grid(row=0, column=1, padx=5)
        self.yaw_label = tk.Label(self.sensor_frame, text="Yaw: 0.00", font=("Arial", 14))
        self.yaw_label.grid(row=0, column=2, padx=5)
        # Log text area for events
        self.log_text = tk.Text(self.root, height=8, width=60)
        self.log_text.pack(pady=5)
        self.log_text.insert(tk.END, "Logs:\n")

    def update_connection_status(self, address: str, connected: bool = True):
        if connected:
            self.root.after(0, lambda: self.conn_status_label.config(text=f"BLE: Connected to {address}"))
            self.root.after(0, lambda: self.conn_status_icon.config(text="✅"))
        else:
            self.root.after(0, lambda: self.conn_status_label.config(text="BLE: Not connected"))
            self.root.after(0, lambda: self.conn_status_icon.config(text="❌"))

    def update_volume_label(self, vol: float):
        vol_percent = int(vol * 100)
        self.root.after(0, lambda: self.volume_label.config(text=f"Windows Volume: {vol_percent}%"))

    def update_sensor_labels(self, roll: float, pitch: float, yaw: float):
        self.root.after(0, lambda: self.roll_label.config(text=f"Roll: {roll:.2f}"))
        self.root.after(0, lambda: self.pitch_label.config(text=f"Pitch: {pitch:.2f}"))
        self.root.after(0, lambda: self.yaw_label.config(text=f"Yaw: {yaw:.2f}"))

    def log_message(self, message: str):
        self.root.after(0, lambda: (self.log_text.insert(tk.END, f"{message}\n"), self.log_text.see(tk.END)))

    def throttled_log(self, message: str):
        current_time = time.time()
        if current_time - self.last_log_time >= self.LOG_INTERVAL:
            self.log_message(message)
            self.last_log_time = current_time
