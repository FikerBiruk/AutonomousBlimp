import math
from blimputils import Magnetometer

mag = Magnetometer()

def norm(a):
    return a + 360 if a < 0 else a

while True:
    mx, my, mz = mag.get_xyz()

    y1 = norm(math.degrees(math.atan2(my, mx)))
    y2 = norm(math.degrees(math.atan2(mx, my)))
    y3 = norm(math.degrees(math.atan2(-my, mx)))
    y4 = norm(math.degrees(math.atan2(mx, -my)))

    print(f"y1=atan2(my, mx):     {y1:7.2f}")
    print(f"y2=atan2(mx, my):     {y2:7.2f}")
    print(f"y3=atan2(-my, mx):    {y3:7.2f}")
    print(f"y4=atan2(mx, -my):    {y4:7.2f}")
    print()
