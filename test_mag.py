from blimputils import Magnetometer
import time

mag = Magnetometer()

print("Rotate the board slowly in a full circle...\n")

while True:
    mx, my, mz = mag.get_xyz()
    print(f"MX={mx:8.2f}  MY={my:8.2f}  MZ={mz:8.2f}")
    time.sleep(0.2)
