# sensors.py — FINAL AXIS-SOLVED VERSION

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
    norm = math.sqrt(ax*ax + ay*ay + az*az)
    ax /= norm
    ay /= norm
    az /= norm

    pitch = math.asin(-ax)
    roll  = math.atan2(ay, az)

    mx2 = mx * math.cos(pitch) + mz * math.sin(pitch)
    my2 = (
            mx * math.sin(roll) * math.sin(pitch)
            + my * math.cos(roll)
            - mz * math.sin(roll) * math.cos(pitch)
    )

    yaw = math.atan2(-my2, mx2)

    return (
        math.degrees(yaw),
        math.degrees(pitch),
        math.degrees(roll)
    )

def read_orientation():
    ax, ay, az = accel.get_xyz()
    mx_raw, my_raw, mz_raw = mag.get_xyz()

    ax *= ACC_SCALE
    ay *= ACC_SCALE
    az *= ACC_SCALE

    # Board upside-down
    ax = -ax
    ay = -ay
    az = -az

    # FINAL SOLVED MAGNETOMETER MAPPING
    mx = -my_raw
    my =  mx_raw
    mz = -mz_raw

    yaw, pitch, roll = compute_yaw_pitch_roll(ax, ay, az, mx, my, mz)

    if yaw < 0:
        yaw += 360.0

    roll = roll + 180.0
    if roll > 180.0:
        roll -= 360.0

    return yaw, pitch, roll
