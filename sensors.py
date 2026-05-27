# sensors.py
# Corrected for upside‑down PCB (chip facing down)

import math
from blimputils import Accelerometer, Gyroscope, Magnetometer

accel = Accelerometer()
gyro  = Gyroscope()
mag   = Magnetometer()

ACC_SCALE = 4.0

def init_sensors():
    try: accel.init()
    except: pass
    try: gyro.init()
    except: pass
    try: mag.init()
    except: pass

def compute_yaw_pitch_roll(ax, ay, az, mx, my, mz):
    # Normalize accelerometer
    norm = math.sqrt(ax*ax + ay*ay + az*az)
    ax /= norm
    ay /= norm
    az /= norm

    # Pitch and roll
    pitch = math.asin(-ax)
    roll  = math.atan2(ay, az)

    # Tilt‑compensated magnetometer
    mx2 = mx * math.cos(pitch) + mz * math.sin(pitch)
    my2 = mx * math.sin(roll) * math.sin(pitch) + my * math.cos(roll) - mz * math.sin(roll) * math.cos(pitch)

    yaw = math.atan2(-my2, mx2)

    return (
        math.degrees(yaw),
        math.degrees(pitch),
        math.degrees(roll)
    )

def read_orientation():
    # Raw sensor reads
    ax, ay, az = accel.get_xyz()
    mx, my, mz = mag.get_xyz()

    # Scale accel
    ax *= ACC_SCALE
    ay *= ACC_SCALE
    az *= ACC_SCALE

    # BOARD IS UPSIDE‑DOWN (chip facing down)
    ax = -ax
    ay = -ay
    az = -az   # <-- this was missing before

    # Magnetometer also flips X/Y when upside‑down
    mx = -mx
    my = -my
    # mz stays the same

    # Compute yaw/pitch/roll
    yaw, pitch, roll = compute_yaw_pitch_roll(ax, ay, az, mx, my, mz)

    # Fix yaw range to 0–360
    if yaw < 0:
        yaw += 360.0

    # Fix roll for upside‑down board
    roll = roll + 180.0
    if roll > 180.0:
        roll -= 360.0

    return yaw, pitch, roll
