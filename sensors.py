# sensors.py — SIMPLE BLIMP VERSION (yaw only)

import math
from blimputils import Magnetometer

mag = Magnetometer()

def init_sensors():
    try: mag.init()
    except: pass

def read_yaw():
    mx_raw, my_raw, mz_raw = mag.get_xyz()

    # Correct axis mapping (derived from your raw data)
    mx = -my_raw
    my =  mx_raw

    # Compute yaw
    yaw = math.degrees(math.atan2(my, mx))

    # Normalize to 0–360
    if yaw < 0:
        yaw += 360

    return yaw
