# sensors.py
# FINAL CLEAN VERSION — EXACT MATCH TO debug IMU ORIENTATION

import math
from blimputils import Accelerometer, Gyroscope, Magnetometer

# Instantiate drivers EXACTLY like debugsensors.py
accel = Accelerometer()
gyro  = Gyroscope()
mag   = Magnetometer()

ACC_SCALE = 4.0   # same as debugsensors.py

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

    # Tilt-compensated magnetometer
    mx2 = mx * math.cos(pitch) + mz * math.sin(pitch)
    my2 = mx * math.sin(roll) * math.sin(pitch) + my * math.cos(roll) - mz * math.sin(roll) * math.cos(pitch)

    yaw = math.atan2(-my2, mx2)

    return (
        math.degrees(yaw),
        math.degrees(pitch),
        math.degrees(roll)
    )

def read_orientation():
    # Read raw sensors
    ax, ay, az = accel.get_xyz()
    mx, my, mz = mag.get_xyz()

    # Scale accel
    ax *= ACC_SCALE
    ay *= ACC_SCALE
    az *= ACC_SCALE

    # Board is upside-down AND rotated 180° around Z
    ax = -ax
    ay = -ay
    # DO NOT flip Z — Z is correct

    # Compute yaw/pitch/roll
    yaw, pitch, roll = compute_yaw_pitch_roll(ax, ay, az, mx, my, mz)

    # Fix yaw (board rotated 180° around Z)
    yaw += 180.0
    if yaw > 180.0:
        yaw -= 360.0

    # Fix roll (board inverted)
    roll -= 180.0
    if roll < -180.0:
        roll += 360.0

    return yaw, pitch, roll
