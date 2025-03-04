"""
Libs needed: bleak, pycaw, comtypes, keyboard
This application uses a BLE peripheral (e.g. an Android app) that sends gyroscope data
to adjust the Windows system volume and trigger media play/pause commands.

P.S: This is the initial monolith app, it works standalone without the need of other packages.
"""


import asyncio
import threading
import tkinter as tk
import time
from bleak import BleakScanner, BleakClient
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from ctypes import POINTER, cast
import keyboard  # May require admin privileges
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# BLE service and characteristic UUIDs
SERVICE_UUID = "0000a000-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "0000a001-0000-1000-8000-00805f9b34fb"

# Global variables for gesture and volume control
previous_yaw = None
previous_pitch = None
last_pitch_time = 0
last_gesture_time = 0
yaw_threshold = 0.3         # Threshold for detecting play/pause gesture based on yaw change
gesture_cooldown = 1.0      # Cooldown (seconds) between gesture triggers

# Pitch range used for mapping (if needed)
min_pitch = -1.0
max_pitch = 1.0

def map_pitch_to_volume(pitch: float) -> float:
    """
    Map a pitch value from [min_pitch, max_pitch] to a volume scalar in [0.0, 1.0].
    """
    pitch = max(min_pitch, min(max_pitch, pitch))
    return (pitch - min_pitch) / (max_pitch - min_pitch)

# --- Setup for Windows Volume Control (using pycaw) ---
devices_audio = AudioUtilities.GetSpeakers()
interface = devices_audio.Activate(IAudioEndpointVolume._iid_, 3, None)  # CLSCTX_ALL = 3
volume_control = cast(interface, POINTER(IAudioEndpointVolume))

# --- Tkinter GUI Setup ---
root = tk.Tk()
root.title("BLE Gyro Volume Controller")

# Connection status frame with icon and label
conn_frame = tk.Frame(root)
conn_frame.pack(pady=5)
conn_status_icon = tk.Label(conn_frame, text="❌", font=("Arial", 16))  # Red cross: not connected
conn_status_icon.pack(side=tk.LEFT, padx=5)
conn_status_label = tk.Label(conn_frame, text="BLE: Not connected", font=("Arial", 12))
conn_status_label.pack(side=tk.LEFT)

# Volume display label
volume_label = tk.Label(root, text="Windows Volume: 0%", font=("Arial", 16))
volume_label.pack(pady=5)

# Sensor values display: Roll, Pitch, and Yaw
sensor_frame = tk.Frame(root)
sensor_frame.pack(pady=5)
roll_label = tk.Label(sensor_frame, text="Roll: 0.00", font=("Arial", 14))
roll_label.grid(row=0, column=0, padx=5)
pitch_label = tk.Label(sensor_frame, text="Pitch: 0.00", font=("Arial", 14))
pitch_label.grid(row=0, column=1, padx=5)
yaw_label = tk.Label(sensor_frame, text="Yaw: 0.00", font=("Arial", 14))
yaw_label.grid(row=0, column=2, padx=5)

# Log text area for connection and gesture events
log_text = tk.Text(root, height=8, width=60)
log_text.pack(pady=5)
log_text.insert(tk.END, "Logs:\n")

def log_message(message: str):
    """Append a message to the log area."""
    log_text.insert(tk.END, f"{message}\n")
    log_text.see(tk.END)

# Throttled logging: restrict log frequency to avoid flooding
LOG_INTERVAL = 2.0  # seconds
last_log_time = 0
last_volume_disabled_logged = False  # Flag to log "volume control disabled" only once per period

def throttled_log(message: str):
    """Log a message only if a set time interval has passed."""
    global last_log_time
    current_time = time.time()
    if current_time - last_log_time >= LOG_INTERVAL:
        log_message(message)
        last_log_time = current_time

def update_volume_label(vol: float):
    """Update the volume display label."""
    vol_percent = int(vol * 100)
    volume_label.config(text=f"Windows Volume: {vol_percent}%")

def update_sensor_labels(roll: float, pitch: float, yaw: float):
    """Update the sensor labels for roll, pitch, and yaw."""
    roll_label.config(text=f"Roll: {roll:.2f}")
    pitch_label.config(text=f"Pitch: {pitch:.2f}")
    yaw_label.config(text=f"Yaw: {yaw:.2f}")

# --- BLE Client using Bleak ---
async def ble_client_task():
    """
    Discover the target BLE device, connect to it, and subscribe to notifications.
    Process the incoming gyroscope data to adjust volume and trigger media control gestures.
    """
    global previous_yaw, last_gesture_time, last_volume_disabled_logged
    log_message("Scanning for BLE devices...")
    devices = await BleakScanner.discover()
    target = None
    for d in devices:
        if SERVICE_UUID.lower() in [s.lower() for s in d.metadata.get("uuids", [])]:
            target = d
            break
    if target is None:
        log_message("No device with the target service found.")
        return
    log_message(f"Found target device: {target.name} ({target.address})")

    # Update connection status (icon and text)
    root.after(0, lambda: (conn_status_label.config(text=f"BLE: Connected to {target.address}"),
                           conn_status_icon.config(text="✅")))

    async with BleakClient(target.address) as client:
        if not client.is_connected:
            log_message("Failed to connect.")
            return
        log_message("Connected to BLE device.")

        def notification_handler(sender, data):
            """
            Process incoming notifications:
            - Update sensor value labels.
            - If the phone is held level (pitch between -1.5 and -0.5), adjust volume based on roll.
            - If the phone is tilted forward (pitch > -0.7) and the pitch changes significantly, trigger play/pause.
            """
            global previous_yaw, last_gesture_time, previous_pitch, last_pitch_time, last_volume_disabled_logged
            try:
                decoded = data.decode("utf-8").strip()
                values = decoded.split(",")
                if len(values) >= 3:
                    # Parse sensor values: roll, pitch, yaw
                    roll, pitch, yaw = map(float, values[:3])
                    root.after(0, lambda: update_sensor_labels(roll, pitch, yaw))

                    # Volume Adjustment: when phone is held level (pitch between -1.5 and -0.5)
                    if -1.5 <= pitch <= -0.5:
                        last_volume_disabled_logged = False  # Reset flag when phone is level
                        current_vol = volume_control.GetMasterVolumeLevelScalar()
                        tilt_threshold = 0.2  # Deadzone for roll
                        rate_factor = 0.02    # Sensitivity factor for volume change
                        new_vol = current_vol
                        if roll < -tilt_threshold:
                            new_vol = current_vol - rate_factor * (abs(roll) - tilt_threshold)
                        elif roll > tilt_threshold:
                            new_vol = current_vol + rate_factor * (roll - tilt_threshold)
                        new_vol = max(0.0, min(1.0, new_vol))
                        volume_control.SetMasterVolumeLevelScalar(new_vol, None)
                        root.after(0, lambda: update_volume_label(new_vol))
                        throttled_log(f"Volume adjusted: roll={roll:.2f} -> Volume: {int(new_vol * 100)}%")
                    else:
                        if not last_volume_disabled_logged:
                            throttled_log("Volume control disabled (phone not held level)")
                            last_volume_disabled_logged = True

                    # Play/Pause Gesture: Trigger when phone is tilted forward (pitch > -0.7)
                    # Trigger only if pitch changes by more than 0.1 from the previous reading
                    pitch_delta_threshold = 0.1
                    if pitch > -0.7:
                        current_time = time.time()
                        if (previous_pitch is None or abs(pitch - previous_pitch) > pitch_delta_threshold) and (current_time - last_pitch_time > gesture_cooldown):
                            keyboard.send("play/pause media")
                            last_pitch_time = current_time
                            throttled_log("Gesture detected: Toggling Play/Pause")
                    previous_pitch = pitch
                    previous_yaw = yaw
            except Exception as e:
                throttled_log(f"Notification error: {e}")

        # Retry loop: try to subscribe to notifications until successful.
        while True:
            try:
                await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
                log_message("Subscribed to notifications. Waiting for data...")
                break
            except Exception as e:
                log_message(f"Failed to start notify: {e}. Retrying in 5 seconds...")
                await asyncio.sleep(5)

        # Keep the connection alive while the client remains connected.
        while client.is_connected:
            await asyncio.sleep(1)
        try:
            await client.stop_notify(CHARACTERISTIC_UUID)
        except Exception as e:
            log_message(f"Error stopping notifications: {e}")

def start_ble_loop():
    """Start the BLE client task using asyncio."""
    asyncio.run(ble_client_task())

# Start the BLE client in a daemon thread.
ble_thread = threading.Thread(target=start_ble_loop, daemon=True)
ble_thread.start()

root.mainloop()
