from blimputils import Magnetometer
import time

mag = Magnetometer()

print("Rotate the board 90° RIGHT each time. Ctrl+C to stop.\n")

while True:
    mx, my, mz = mag.get_xyz()
    print(f"MX={mx:7.2f}  MY={my:7.2f}  MZ={mz:7.2f}")
    time.sleep(0.5)
