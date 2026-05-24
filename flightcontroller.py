#!/usr/bin/env python3
# flight_controller.py
# Real sensor reads via blimputils, PID loops, mixer, and curses teleop
# Prints motor outputs instead of driving motors

import curses
import time
from pid import PID
import sensors

# PID controllers for yaw, pitch, roll
yaw_pid   = PID(kp=0.02, ki=0.0, kd=0.002, setpoint=0.0, output_limits=(-1.0, 1.0))
pitch_pid = PID(kp=0.03, ki=0.0, kd=0.004, setpoint=0.0, output_limits=(-1.0, 1.0))
roll_pid  = PID(kp=0.03, ki=0.0, kd=0.004, setpoint=0.0, output_limits=(-1.0, 1.0))

# Teleop state
forward_cmd = 0.0
vertical_cmd = 0.0
yaw_setpoint_step = 5.0  # degrees per keypress
throttle_ramp = 0.02     # how fast W/S/Q/E change thrust

def mix(forward_cmd, vertical_cmd, yaw_cmd, pitch_cmd, roll_cmd):
    # Motor mapping:
    # M1: horizontal left
    # M2: vertical left
    # M3: vertical right
    # M4: horizontal right

    # Horizontal motors: forward + yaw
    m1 = forward_cmd - yaw_cmd
    m4 = forward_cmd + yaw_cmd

    # Vertical motors: vertical throttle + pitch/roll stabilization
    m2 = vertical_cmd + pitch_cmd + roll_cmd
    m3 = vertical_cmd + pitch_cmd - roll_cmd

    # Clamp to [-1,1]
    def clamp(v):
        return max(-1.0, min(1.0, v))

    return clamp(m1), clamp(m2), clamp(m3), clamp(m4)

def run(stdscr):
    global forward_cmd, vertical_cmd
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(50)

    sensors.init_sensors()

    stdscr.addstr(0, 0,
                  "Flight controller running.\n"
                  "W/S = forward/back (hold)\n"
                  "Q/E = up/down (hold)\n"
                  "A/D = yaw left/right\n"
                  "SPACE = zero thrust\n"
                  "X = reset PIDs\n"
                  "ESC = quit"
                  )
    stdscr.refresh()

    try:
        while True:
            key = stdscr.getch()

            # -------------------------
            # Continuous throttle control
            # -------------------------
            if key != -1:
                if key in (27,):  # ESC
                    break

                # Forward/backward thrust
                if key in (ord('w'), ord('W')):
                    forward_cmd += throttle_ramp
                elif key in (ord('s'), ord('S')):
                    forward_cmd -= throttle_ramp

                # Vertical thrust (UP/DOWN)
                elif key in (ord('q'), ord('Q')):
                    vertical_cmd += throttle_ramp
                elif key in (ord('e'), ord('E')):
                    vertical_cmd -= throttle_ramp

                # Zero thrust
                elif key == ord(' '):
                    forward_cmd = 0.0
                    vertical_cmd = 0.0

                # Reset PIDs
                elif key in (ord('x'), ord('X')):
                    yaw_pid.reset()
                    pitch_pid.reset()
                    roll_pid.reset()

                # Yaw setpoint adjust
                elif key == ord('a'):
                    yaw_pid.setpoint -= yaw_setpoint_step
                elif key == ord('d'):
                    yaw_pid.setpoint += yaw_setpoint_step

            # Clamp thrusts
            forward_cmd = max(-1.0, min(1.0, forward_cmd))
            vertical_cmd = max(-1.0, min(1.0, vertical_cmd))

            # -------------------------
            # Read orientation from sensors
            # -------------------------
            yaw, pitch, roll = sensors.read_orientation()

            # These angles are already corrected by your IMU transform:
            #   roll ≈ 0° when level
            #   pitch ≈ 0° when level
            #   yaw = correct heading
            # No more transforms needed.

            # -------------------------
            # Compute PID outputs
            # -------------------------
            yaw_out = yaw_pid.update(yaw)
            pitch_out = pitch_pid.update(pitch)
            roll_out = roll_pid.update(roll)

            # -------------------------
            # Mixer -> motor commands
            # -------------------------
            m1, m2, m3, m4 = mix(forward_cmd, vertical_cmd, yaw_out, pitch_out, roll_out)

            # -------------------------
            # Print status
            # -------------------------
            stdscr.addstr(10, 0, f"Setpoints: Yaw={yaw_pid.setpoint:6.1f}°")
            stdscr.addstr(11, 0, f"Sensors:   Yaw={yaw:6.1f}°  Pitch={pitch:6.1f}°  Roll={roll:6.1f}°")
            stdscr.addstr(12, 0, f"PIDs:      Yaw={yaw_out:5.2f}  Pitch={pitch_out:5.2f}  Roll={roll_out:5.2f}")
            stdscr.addstr(14, 0, f"Motors (sim): M1={m1:5.2f}  M2={m2:5.2f}  M3={m3:5.2f}  M4={m4:5.2f}")
            stdscr.addstr(16, 0, f"Forward cmd:  {forward_cmd:4.2f}")
            stdscr.addstr(17, 0, f"Vertical cmd: {vertical_cmd:4.2f}")
            stdscr.refresh()

            time.sleep(0.02)

    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    curses.wrapper(run)
