#!/usr/bin/env python3
import curses
import time
from dataclasses import dataclass

import RPi.GPIO as GPIO

PWM_FREQUENCY = 1000  # Hz

# -----------------------------
# Motor Driver (DRV8212P)
# -----------------------------

@dataclass(frozen=True)
class MotorPins:
    in1: int
    in2: int

class Motor:
    def __init__(self, pins: MotorPins):
        self.pins = pins

        GPIO.setup(pins.in1, GPIO.OUT)
        GPIO.setup(pins.in2, GPIO.OUT)

        self.pwm_in1 = GPIO.PWM(pins.in1, PWM_FREQUENCY)
        self.pwm_in2 = GPIO.PWM(pins.in2, PWM_FREQUENCY)

        self.pwm_in1.start(0)
        self.pwm_in2.start(0)

    def set_speed(self, speed: float):
        speed = max(-1.0, min(1.0, speed))
        duty = abs(speed) * 100

        if speed > 0:
            self.pwm_in1.ChangeDutyCycle(duty)
            self.pwm_in2.ChangeDutyCycle(0)
        elif speed < 0:
            self.pwm_in1.ChangeDutyCycle(0)
            self.pwm_in2.ChangeDutyCycle(duty)
        else:
            self.pwm_in1.ChangeDutyCycle(0)
            self.pwm_in2.ChangeDutyCycle(0)

    def stop(self):
        self.set_speed(0)

    def close(self):
        self.stop()
        self.pwm_in1.stop()
        self.pwm_in2.stop()


# -----------------------------
# Motor Mapping (your PCB)
# -----------------------------
# Motor 1 = horizontal left
# Motor 2 = vertical left
# Motor 3 = vertical right
# Motor 4 = horizontal right

MOTOR_PINS = [
    MotorPins(21, 13),  # Motor 1
    MotorPins(20, 6),   # Motor 2
    MotorPins(16, 5),   # Motor 3
    MotorPins(19, 26),  # Motor 4
]

# -----------------------------
# Teleop Commands
# -----------------------------
# Horizontal motors: 1 & 4
# Vertical motors:   2 & 3

def apply_drive(motors, forward, turn, vertical):
    """
    forward:  -1 to 1
    turn:     -1 to 1
    vertical: -1 to 1
    """

    # Horizontal motors
    left_h  = forward - turn
    right_h = forward + turn

    # Vertical motors (both push downwards)
    up_left  = vertical
    up_right = vertical

    # Motor order: 1,2,3,4
    speeds = [
        left_h,     # Motor 1
        up_left,    # Motor 2
        up_right,   # Motor 3
        right_h     # Motor 4
    ]

    for motor, speed in zip(motors, speeds):
        motor.set_speed(speed)


# -----------------------------
# Teleop Loop
# -----------------------------

def run(stdscr):
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    motors = [Motor(p) for p in MOTOR_PINS]

    # Use a short blocking timeout so we can treat lack of key within the
    # timeout as a key-release (i.e. user not actively holding the key).
    # This makes motors run only while a key is actively held.
    stdscr.timeout(50)  # milliseconds
    curses.curs_set(0)
    # Note: 'q' is rise, use 'z' to quit (avoid duplicate 'q')
    stdscr.addstr(0, 0, "WASD = move (hold), Q = rise (hold), E = fall (hold), SPACE = stop, X = hover, Z = quit")
    stdscr.refresh()

    forward = 0.0
    turn = 0.0
    vertical = 0.0
    # Timestamp of the last received key event. We keep motors active for a
    # short grace period after the last key to tolerate OS key-repeat delays.
    last_key_time = 0.0
    hold_timeout = 0.15  # seconds

    try:
        while True:
            # Read a key (blocks up to stdscr.timeout milliseconds)
            key = stdscr.getch()
            now = time.time()

            if key != -1:
                # Record the time we last saw a key so we can keep motors
                # running for a short grace period even if OS key repeats are
                # delayed.
                last_key_time = now

                # Quit (use 'z' to quit to avoid conflicting with 'q' for rise)
                if key in (ord("z"), ord("Z")):
                    break

                if key == ord("w"):
                    forward = 0.2
                elif key == ord("s"):
                    forward = -0.2
                elif key == ord("a"):
                    turn = -0.7
                elif key == ord("d"):
                    turn = 0.7
                elif key == ord(" "):
                    forward = turn = vertical = 0.0
                elif key == ord("x"):
                    vertical = 0.0
                elif key == ord("q") or key == ord("Q"):  # rise
                    vertical = 0.1
                elif key == ord("e") or key == ord("E"):  # fall
                    vertical = -0.1

                stdscr.addstr(2, 0, f"FWD={forward:.1f}  TURN={turn:.1f}  VERT={vertical:.1f}   ")
                stdscr.refresh()
            else:
                # No key event this iteration - if it's been longer than
                # hold_timeout since the last key event, consider keys
                # released and clear commands so motors stop.
                if now - last_key_time > hold_timeout:
                    forward = 0.0
                    turn = 0.0
                    vertical = 0.0

            # Apply motor speeds continuously
            apply_drive(motors, forward, turn, vertical)

            time.sleep(0.01)

    finally:
        for m in motors:
            m.close()
        GPIO.cleanup()


if __name__ == "__main__":
    curses.wrapper(run)
