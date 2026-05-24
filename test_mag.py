from blimputils import Magnetometer
import time, math

mag = Magnetometer()

print("Move the board. Ctrl+C to stop.\n")

while True:
    mx, my, mz = mag.get_xyz()
    mag_norm = math.sqrt(mx*mx + my*my + mz*mz)
    print(f"MX={mx:7.2f}  MY={my:7.2f}  MZ={mz:7.2f}  |B|={mag_norm:7.2f}")
    time.sleep(0.2)
