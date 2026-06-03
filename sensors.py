import math
from blimputils import Magnetometer

mag = Magnetometer()

def init_sensors():
    pass  # no init() needed

def read_yaw():
    mx, my, mz = mag.get_xyz()

    # Correct axis mapping for your PCB orientation
    yaw = math.degrees(math.atan2(mx, -my))

    if yaw < 0:
        yaw += 360

    return yaw

