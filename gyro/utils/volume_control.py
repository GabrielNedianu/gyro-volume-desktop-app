"""
File: utils/volume_control.py
Provides utility functions and globals for volume control.
Sets up the Windows Volume Control using pycaw and defines a mapping function.
"""

from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from ctypes import POINTER, cast

min_pitch = -1.0
max_pitch = 1.0

def map_pitch_to_volume(pitch: float) -> float:
    """
    Map a pitch value from [min_pitch, max_pitch] to a volume scalar in [0.0, 1.0].
    """
    pitch = max(min_pitch, min(max_pitch, pitch))
    return (pitch - min_pitch) / (max_pitch - min_pitch)

# Setup for Windows Volume Control (using pycaw)
devices_audio = AudioUtilities.GetSpeakers()
interface = devices_audio.Activate(IAudioEndpointVolume._iid_, 3, None)  # CLSCTX_ALL = 3
volume_control = cast(interface, POINTER(IAudioEndpointVolume))
