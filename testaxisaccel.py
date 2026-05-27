from blimputils import Accelerometer
import time

accel = Accelerometer()
accel.init()

print("Hold the board flat, upside down. Rotate 90° RIGHT each time.\n")

while True:
    ax, ay, az = accel.get_xyz()
    print(f"AX={ax:7.2f}  AY={ay:7.2f}  AZ={az:7.2f}")
    time.sleep(0.5)
