# sensors.py
# Thin wrapper around your blimp-utils drivers
# Assumes blimputils provides Accelerometer, Gyroscope, Magnetometer classes
# I2C bus 1, BMI270 @ 0x68, BMM350 @ 0x14

import math
import time
from blimputils import Accelerometer, Gyroscope, Magnetometer

# Create sensor objects using addresses you provided
I2C_BUS = 1
BMI_ADDR = 0x68
BMM_ADDR = 0x14

# Instantiate drivers. Drivers are expected to handle their own init.
accel = Accelerometer(bus=I2C_BUS, addr=BMI_ADDR)
gyro  = Gyroscope(bus=I2C_BUS, addr=BMI_ADDR)
mag   = Magnetometer(bus=I2C_BUS, addr=BMM_ADDR)

# Complementary filter state
_last_time = None
_yaw = 0.0
_pitch = 0.0
_roll = 0.0

def init_sensors():
    # If your drivers need explicit init calls, call them here
    try:
        accel.init()
    except Exception:
        pass
    try:
        gyro.init()
    except Exception:
        pass
    try:
        mag.init()
    except Exception:
        pass

def _accel_to_pitch_roll(ax, ay, az):
    # Orientation mapping you gave:
    # +Y = forward/back, +X = left/right, +Z = up/down
    # Using standard formulas adapted to axis mapping
    # pitch: rotation around X axis (nose up/down)
    # roll: rotation around Y axis (tilt left/right)
    # Note signs chosen to produce intuitive positive angles
    pitch = math.degrees(math.atan2(-ay, math.sqrt(ax*ax + az*az)))
    roll  = math.degrees(math.atan2(ax, az))
    return pitch, roll

def _tilt_compensated_yaw(mx, my, mz, pitch_deg, roll_deg):
    # Convert degrees to radians
    pitch = math.radians(pitch_deg)
    roll = math.radians(roll_deg)

    # Tilt compensation formulas
    Xh = mx * math.cos(pitch) + mz * math.sin(pitch)
    Yh = mx * math.sin(roll) * math.sin(pitch) + my * math.cos(roll) - mz * math.sin(roll) * math.cos(pitch)

    yaw = math.degrees(math.atan2(Yh, Xh))
    # Normalize to [-180,180]
    if yaw > 180:
        yaw -= 360
    if yaw < -180:
        yaw += 360
    return yaw

def read_imu():
    # Returns accel (ax,ay,az), gyro (gx,gy,gz) in sensor units as provided by drivers
    ax, ay, az = accel.get_xyz()
    gx, gy, gz = gyro.get_xyz()
    return (ax, ay, az), (gx, gy, gz)

def read_mag():
    mx, my, mz = mag.get_xyz()
    return mx, my, mz

def read_orientation():
    # Returns (yaw_deg, pitch_deg, roll_deg) using complementary filter
    global _last_time, _yaw, _pitch, _roll

    now = time.monotonic()
    if _last_time is None:
        dt = 0.02
    else:
        dt = now - _last_time
    _last_time = now

    (ax, ay, az), (gx, gy, gz) = read_imu()
    mx, my, mz = read_mag()

    # Gyro rates assumed in deg/s from driver. If drivers return rad/s, convert accordingly
    # Integrate gyro for short-term orientation
    # Use accel for long-term pitch/roll, mag for yaw with tilt compensation

    # Compute accel-based pitch/roll
    accel_pitch, accel_roll = _accel_to_pitch_roll(ax, ay, az)

    # Integrate gyro rates
    # gyro axes mapping must match orientation mapping. Here we assume:
    # gx = rotation rate around X (left/right axis) -> affects pitch
    # gy = rotation rate around Y (forward/back axis) -> affects roll
    # gz = rotation rate around Z (up/down axis) -> affects yaw
    # If your driver returns different ordering, swap accordingly
    _pitch += gx * dt
    _roll  += gy * dt
    _yaw   += gz * dt

    # Complementary filter for pitch/roll
    alpha = 0.98
    _pitch = alpha * _pitch + (1 - alpha) * accel_pitch
    _roll  = alpha * _roll  + (1 - alpha) * accel_roll

    # Tilt-compensated yaw from magnetometer
    mag_yaw = _tilt_compensated_yaw(mx, my, mz, _pitch, _roll)

    # Fuse gyro yaw integration with mag yaw using complementary filter
    # Handle wrap-around when computing error
    def angle_diff(a, b):
        d = a - b
        while d > 180:
            d -= 360
        while d < -180:
            d += 360
        return d

    yaw_error = angle_diff(mag_yaw, _yaw)
    # small gain to nudge integrated yaw toward mag yaw
    yaw_correction_gain = 0.02
    _yaw += yaw_correction_gain * yaw_error

    # Normalize _yaw to [-180,180]
    if _yaw > 180:
        _yaw -= 360
    if _yaw < -180:
        _yaw += 360

    return _yaw, _pitch, _roll
