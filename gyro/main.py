"""
File: monolith.py
Entry point for the BLE Gyro Volume Controller application.
"""

import threading
import tkinter as tk
import asyncio
from ui.ui_manager import UIManager
from ble.ble_client import BLEClient

# Global variable for the BLE thread.
ble_thread = None

def start_ble_loop(ui_manager):
    asyncio.run(BLEClient(ui_manager).run())

def refresh_ble(ui_manager):
    """
    Refresh the BLE process by starting a new BLEClient instance.
    """
    ui_manager.log_message("Refreshing BLE process...")
    global ble_thread
    ble_thread = threading.Thread(target=lambda: start_ble_loop(ui_manager), daemon=True)
    ble_thread.start()

def main():
    root = tk.Tk()
    ui_manager = UIManager(root)
    ui_manager.set_refresh_callback(lambda: refresh_ble(ui_manager))

    global ble_thread
    ble_thread = threading.Thread(target=lambda: start_ble_loop(ui_manager), daemon=True)
    ble_thread.start()
    root.mainloop()

if __name__ == "__main__":
    main()
