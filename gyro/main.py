"""
File: monolith.py
Entry point for the BLE Gyro Volume Controller application.
"""

import threading
import tkinter as tk
import asyncio
from ui.ui_manager import UIManager
from ble.ble_client import BLEClient

def start_ble_loop(ui_manager):
    asyncio.run(BLEClient(ui_manager).run())

def main():
    root = tk.Tk()
    ui_manager = UIManager(root)
    ble_thread = threading.Thread(target=lambda: start_ble_loop(ui_manager), daemon=True)
    ble_thread.start()
    root.mainloop()

if __name__ == "__main__":
    main()
