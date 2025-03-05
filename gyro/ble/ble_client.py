"""
File: ble/ble_client.py
Contains the BLEClient class that handles BLE scanning, connection,
and notification subscription via Bleak. It processes incoming gyroscope data
to adjust system volume and trigger media control gestures.
"""

import asyncio
import time
import keyboard  # May require admin privileges
from bleak import BleakScanner, BleakClient
from utils.volume_control import volume_control, map_pitch_to_volume
from ui.ui_manager import UIManager  # For type hints (optional)

# BLE service and characteristic UUIDs
SERVICE_UUID = "0000a000-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "0000a001-0000-1000-8000-00805f9b34fb"

# Gesture parameters
yaw_threshold = 0.3         # Threshold for detecting play/pause gesture (yaw)
gesture_cooldown = 1.0      # Cooldown in seconds between gesture triggers

class BLEClient:
    """
    BLEClient handles scanning for the target BLE peripheral, connecting to it,
    and subscribing to notifications. It uses sensor data to update volume and
    trigger media controls.
    """
    def __init__(self, ui_manager: UIManager):
        self.ui = ui_manager
        self.previous_yaw = None
        self.previous_pitch = None
        self.last_pitch_time = 0
        self.last_gesture_time = 0

    async def run(self):
        self.ui.log_message("Scanning for BLE devices...")
        devices = await BleakScanner.discover()
        target = None
        for d in devices:
            if SERVICE_UUID.lower() in [s.lower() for s in d.metadata.get("uuids", [])]:
                target = d
                break
        if target is None:
            self.ui.log_message("No device with the target service found.")
            return
        self.ui.log_message(f"Found target device: {target.name} ({target.address})")
        self.ui.update_connection_status(target.address, connected=True)

        async with BleakClient(target.address) as client:
            if not client.is_connected:
                self.ui.log_message("Failed to connect.")
                return
            self.ui.log_message("Connected to BLE device.")

            def notification_handler(sender, data):
                """
                Process incoming notifications:
                - Update sensor labels.
                - When phone is held level (pitch between -1.5 and -0.5), adjust volume based on roll.
                - When phone is tilted forward (pitch > -0.7) with significant pitch change, trigger play/pause.
                """
                try:
                    decoded = data.decode("utf-8").strip()
                    values = decoded.split(",")
                    if len(values) >= 3:
                        roll, pitch, yaw = map(float, values[:3])
                        self.ui.update_sensor_labels(roll, pitch, yaw)

                        # Volume Adjustment: when phone is held level (pitch between -1.5 and -0.5)
                        if -1.5 <= pitch <= -0.5:
                            self.ui.last_volume_disabled_logged = False  # Reset flag when level
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
                            self.ui.update_volume_label(new_vol)
                            self.ui.throttled_log(f"Volume adjusted: roll={roll:.2f} -> Volume: {int(new_vol * 100)}%")
                        else:
                            if not self.ui.last_volume_disabled_logged:
                                self.ui.log_message("Volume control disabled (phone not held level)")
                                self.ui.last_volume_disabled_logged = True

                        # Play/Pause Gesture: when phone is tilted forward (pitch > -0.7)
                        # Trigger only if pitch changes by more than 0.1 and cooldown has passed.
                        pitch_delta_threshold = 0.1
                        if pitch > -0.7:
                            current_time = time.time()
                            if ((self.previous_pitch is None or abs(pitch - self.previous_pitch) > pitch_delta_threshold) and
                                (current_time - self.last_pitch_time > gesture_cooldown)):
                                keyboard.send("play/pause media")
                                self.last_pitch_time = current_time
                                self.ui.log_message("Gesture detected: Toggling Play/Pause")
                        self.previous_pitch = pitch
                        self.previous_yaw = yaw
                except Exception as e:
                    self.ui.log_message(f"Notification error: {e}")

            # Retry loop for starting notifications.
            while True:
                try:
                    await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
                    self.ui.log_message("Subscribed to notifications. Waiting for data...")
                    break
                except Exception as e:
                    self.ui.log_message(f"Failed to start notify: {e}. Retrying in 5 seconds...")
                    asyncio.sleep(5)

            # Keep the connection alive
            while client.is_connected:
                await asyncio.sleep(1)
            try:
                await client.stop_notify(CHARACTERISTIC_UUID)
            except Exception as e:
                self.ui.log_message(f"Error stopping notifications: {e}")
