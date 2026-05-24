from blimputils import Accelerometer, Gyroscope, Magnetometer
import time
import math

# Initialize sensors
acc = Accelerometer()
gyro = Gyroscope()
mag = Magnetometer()

def compute_yaw_pitch_roll(ax, ay, az, mx, my, mz):
    # Normalize accelerometer
    norm_acc = math.sqrt(ax*ax + ay*ay + az*az)
    ax /= norm_acc
    ay /= norm_acc
    az /= norm_acc

    # Pitch and roll from accelerometer
    pitch = math.asin(-ax)
    roll = math.atan2(ay, az)

    # Tilt-compensated magnetometer
    mx2 = mx * math.cos(pitch) + mz * math.sin(pitch)
    my2 = mx * math.sin(roll) * math.sin(pitch) + my * math.cos(roll) - mz * math.sin(roll) * math.cos(pitch)

    yaw = math.atan2(-my2, mx2)

    # Convert to degrees
    return (
        math.degrees(yaw),
        math.degrees(pitch),
        math.degrees(roll)
    )

print("Debug IMU Reader Running...\nMove the blimp to see live values.\nCTRL+C to exit.\n")

while True:
    # Read sensors
    ax, ay, az = acc.get_xyz()
    gx, gy, gz = gyro.get_xyz()
    mx, my, mz = mag.get_mag()

    # Compute YPR
    yaw, pitch, roll = compute_yaw_pitch_roll(ax, ay, az, mx, my, mz)

    # Print clean debug output
    print(f"ACC:  X={ax:6.2f}  Y={ay:6.2f}  Z={az:6.2f}")
    print(f"GYR:  X={gx:6.2f}  Y={gy:6.2f}  Z={gz:6.2f}")
    print(f"MAG:  X={mx:6.2f}  Y={my:6.2f}  Z={mz:6.2f}")
    print(f"YPR:  Yaw={yaw:7.2f}°  Pitch={pitch:7.2f}°  Roll={roll:7.2f}°")
    print("-" * 50)

    time.sleep(0.1)
