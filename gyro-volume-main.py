import asyncio
import threading
import tkinter as tk
import time
from bleak import BleakClient, BleakScanner
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from ctypes import POINTER, cast
import keyboard  # May require admin privileges

# Define your custom BLE UUIDs
SERVICE_UUID = "0000a000-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "0000a001-0000-1000-8000-00805f9b34fb"

# Gesture detection variables
previous_yaw = None
last_gesture_time = 0
yaw_threshold = 1.0  # Radian threshold for play/pause gesture
gesture_cooldown = 1.0  # Minimum seconds between gestures

# Pitch mapping range (adjust as needed)
min_pitch = -1.0
max_pitch = 1.0


def map_pitch_to_volume(pitch: float) -> float:
    """Map pitch (from min_pitch to max_pitch) to a volume scalar between 0.0 and 1.0."""
    pitch = max(min_pitch, min(max_pitch, pitch))
    return (pitch - min_pitch) / (max_pitch - min_pitch)


# --- Initialize pycaw for Windows volume control ---
devices_audio = AudioUtilities.GetSpeakers()
interface = devices_audio.Activate(IAudioEndpointVolume._iid_, 3, None)  # CLSCTX_ALL is 3
volume_control = cast(interface, POINTER(IAudioEndpointVolume))

# --- Tkinter GUI Setup ---
root = tk.Tk()
root.title("BLE Gyro Volume Controller")

conn_status_label = tk.Label(root, text="BLE: Not connected", font=("Arial", 12))
conn_status_label.pack(pady=5)

volume_label = tk.Label(root, text="Windows Volume: 0%", font=("Arial", 16))
volume_label.pack(pady=5)

log_text = tk.Text(root, height=10, width=60)
log_text.pack(pady=5)
log_text.insert(tk.END, "Logs:\n")


def log_message(msg: str):
    log_text.insert(tk.END, msg + "\n")
    log_text.see(tk.END)


def update_volume_label(vol: float):
    volume_label.config(text=f"Windows Volume: {int(vol * 100)}%")


# --- BLE Client using Bleak ---
async def ble_client_task():
    global previous_yaw, last_gesture_time
    log_message("Scanning for BLE devices...")
    devices = await BleakScanner.discover()
    target = None
    for d in devices:
        # Check if the device advertises our service UUID
        if SERVICE_UUID.lower() in [s.lower() for s in d.metadata.get("uuids", [])]:
            target = d
            break
    if target is None:
        log_message("No device with the target service found.")
        return
    log_message(f"Found target device: {target.name} ({target.address})")

    # Update connection status on the Tkinter UI (in the monolith thread)
    root.after(0, lambda: conn_status_label.config(text=f"BLE: Connected to {target.address}"))

    async with BleakClient(target.address) as client:
        if not client.is_connected:
            log_message("Failed to connect.")
            return
        log_message("Connected to BLE device.")

        # # Define the notification callback
        # def notification_handler(sender, data):
        #     global previous_yaw, last_gesture_time
        #     try:
        #         decoded = data.decode("utf-8").strip()
        #         values = decoded.split(",")
        #         if len(values) >= 3:
        #             roll, pitch, yaw = map(float, values[:3])
        #             vol_scalar = map_pitch_to_volume(pitch)
        #             # Update Windows volume using pycaw
        #             volume_control.SetMasterVolumeLevelScalar(vol_scalar, None)
        #             current_vol = volume_control.GetMasterVolumeLevelScalar()
        #             # Update the Tkinter label in the monolith thread
        #             root.after(0, lambda: update_volume_label(current_vol))
        #             log_message(
        #                 f"Data: roll={roll:.2f}, pitch={pitch:.2f}, yaw={yaw:.2f} -> Volume: {int(current_vol * 100)}%"
        #             )
        #
        #             # Gesture detection: if rapid yaw change, trigger play/pause
        #             current_time = time.time()
        #             if previous_yaw is not None and (current_time - last_gesture_time) > gesture_cooldown:
        #                 if abs(yaw - previous_yaw) > yaw_threshold:
        #                     keyboard.send("play/pause media")
        #                     last_gesture_time = current_time
        #                     log_message("Gesture detected: Toggling Play/Pause")
        #             previous_yaw = yaw
        #     except Exception as e:
        #         log_message(f"Notification error: {e}")

        def notification_handler(sender, data):
            global previous_yaw, last_gesture_time
            try:
                decoded = data.decode("utf-8").strip()
                values = decoded.split(",")
                if len(values) >= 3:
                    roll, pitch, yaw = map(float, values[:3])

                    # --- Volume Adjustment Based on Roll ---
                    # Read the current volume (0.0 - 1.0)
                    current_vol = volume_control.GetMasterVolumeLevelScalar()
                    tilt_threshold = 0.25  # No change for small tilts
                    rate_factor = 0.02  # Determines how much volume changes per notification

                    new_vol = current_vol
                    if roll < -tilt_threshold:
                        # Tilt to left decreases volume
                        new_vol = current_vol - rate_factor * (abs(roll) - tilt_threshold)
                    elif roll > tilt_threshold:
                        # Tilt to right increases volume
                        new_vol = current_vol + rate_factor * (roll - tilt_threshold)

                    # Clamp new volume between 0.0 and 1.0
                    new_vol = max(0.0, min(1.0, new_vol))

                    # Update volume via pycaw
                    volume_control.SetMasterVolumeLevelScalar(new_vol, None)
                    # Update the Tkinter label (run in UI thread)
                    root.after(0, lambda: update_volume_label(new_vol))
                    log_message(f"Volume adjusted: roll={roll:.2f} -> Volume: {int(new_vol * 100)}%")

                    # --- Play/Pause Gesture Based on Yaw ---
                    current_time = time.time()
                    if previous_yaw is not None and (current_time - last_gesture_time) > gesture_cooldown:
                        if abs(yaw - previous_yaw) > yaw_threshold:
                            keyboard.send("play/pause media")
                            last_gesture_time = current_time
                            log_message("Gesture detected: Toggling Play/Pause")
                    previous_yaw = yaw

            except Exception as e:
                log_message(f"Notification error: {e}")

        # Retry loop for starting notifications
        while True:
            try:
                await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
                log_message("Subscribed to notifications. Waiting for data...")
                break  # Break out of loop on success
            except Exception as e:
                log_message(f"Failed to start notify: {e}. Retrying in 5 seconds...")
                await asyncio.sleep(5)

        # Keep the connection open indefinitely (or until the device disconnects)
        while client.is_connected:
            await asyncio.sleep(1)

        await client.stop_notify(CHARACTERISTIC_UUID)


def start_ble_loop():
    asyncio.run(ble_client_task())


# Run the BLE client in a separate daemon thread
ble_thread = threading.Thread(target=start_ble_loop, daemon=True)
ble_thread.start()

# Start the Tkinter monolith loop
root.mainloop()
