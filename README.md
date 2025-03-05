# BLE Gyro Volume Controller

BLE Gyro Volume Controller is a multi-platform project that lets you control your Windows system volume and trigger media playback commands using gyroscope data from an Android device. The Android app acts as a BLE peripheral that continuously sends sensor data (roll, pitch, yaw) over Bluetooth Low Energy (BLE). A Python desktop application acts as a BLE central, processing that data to adjust volume and control media commands—all while providing a modern, material-inspired UI.

## Overview

### How It Works

1. **Android BLE Peripheral:**
   - The Android app gathers gyroscope sensor data (roll, pitch, yaw) from the device.
   - It advertises a custom BLE service with a unique UUID and sends sensor data as notifications.
   - The Android app uses Jetpack Compose and MVVM architecture for a clean, modern UI.

2. **Python BLE Central:**
   - The Python app uses Bleak to scan for and connect to the Android BLE peripheral.
   - Sensor data received via notifications is processed to:
     - **Adjust Volume:** When the device is held level, its roll value controls the Windows volume (tilt left decreases, tilt right increases).
     - **Toggle Media Playback:** A forward tilt gesture (with a significant pitch change) triggers play/pause commands.
   - The app uses Tkinter for the UI and follows a modular MVVM-like architecture for maintainability.

### Architecture

The project is organized into several modules:

- **Android App (Java/Kotlin):**
  - **BLE Peripheral Service & Sensor Manager:** Advertises the BLE service and sends sensor data.
  - **UI (Jetpack Compose):** Displays sensor readings, connection status, and theme settings.

- **Python App:**
  - **main.py:** Application entry point; initializes UI and starts the BLE client.
  - **ble/ble_client.py:** Contains the `BLEClient` class to handle BLE scanning, connection, and notification subscription.
  - (Future-Implementation) **gesture/gesture_manager.py:** Will provide a framework to detect more complex gestures.
  - **ui/ui_manager.py:** Manages the Tkinter UI (connection status, sensor display, logging, refresh button, and settings).
  - **utils/volume_control.py:** Sets up Windows volume control via pycaw and provides helper functions.

## Features

- **Real-time Sensor Data:** The Android device sends continuous gyroscope data via BLE.
- **Volume Control:** Adjusts Windows volume based on the device’s roll when held level.
- **Media Control:** A forward tilt gesture triggers play/pause commands.
- **Modern UI:** The Python UI uses Tkinter with material-inspired components (app bar, bottom bar with a blinking BLE status dot, sensor data table with icons, and a refresh button).
- **Extensible Architecture:** The project is modularized, making it easy to add advanced gesture detection, theme customization, or additional sensors.

## Prerequisites

### Android App

- Android Studio 4.2+  
- An Android device (or emulator with BLE support)  
- Minimum SDK: 24  
- Dependencies: Jetpack Compose, Material Components  

### Python App

- Python 3.8+  
- Windows OS with BLE support  
- Required Python libraries:
  - [bleak](https://pypi.org/project/bleak/)
  - [pycaw](https://pypi.org/project/pycaw/)
  - [comtypes](https://pypi.org/project/comtypes/)
  - [keyboard](https://pypi.org/project/keyboard/)
  - Tkinter (bundled with Python)

## Setup and Usage

### Android App

1. Clone the repository and open the Android project in Android Studio.
2. Build and run the app on your Android device. Ensure Bluetooth is enabled.
3. The app will start advertising the BLE service and transmitting sensor data.

### Python App

1. **Clone the repository:**

   ```bash
   git clone https://github.com/GabrielNedianu/ble-gyro-volume-controller-python.git
   cd ble-gyro-volume-controller-python
   ```

2. **Create and activate a virtual environment:**

   On Windows:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Python application:**

   ```bash
   python main.py
   ```
The UI will display sensor readings, BLE connection status, and logs. Use the refresh button to restart the BLE process if needed.
