#!/usr/bin/env python3
import curses
import time
from dataclasses import dataclass
from typing import Iterable

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
# Drive Base (Left/Right pairs)
# -----------------------------

class DriveBase:
    def __init__(self, left: Iterable[MotorPins], right: Iterable[MotorPins]):
        self.left = [Motor(p) for p in left]
        self.right = [Motor(p) for p in right]

    def drive(self, left_speed: float, right_speed: float):
        for m in self.left:
            m.set_speed(left_speed)
        for m in self.right:
            m.set_speed(right_speed)

    def stop(self):
        self.drive(0, 0)

    def close(self):
        self.stop()
        for m in self.left + self.right:
            m.close()


# -----------------------------
# Your actual PCB motor mapping
# -----------------------------
# Motor layout:
#   Left side:  Motor 1, Motor 2
#   Right side: Motor 3, Motor 4

LEFT_MOTORS = [
    MotorPins(21, 13),  # Motor 1
    MotorPins(20, 6),   # Motor 2
]

RIGHT_MOTORS = [
    MotorPins(16, 5),   # Motor 3
    MotorPins(19, 26),  # Motor 4
]

# -----------------------------
# Teleop Commands
# -----------------------------

COMMANDS = {
    "w": (1.0, 1.0),     # forward
    "s": (-1.0, -1.0),   # backward
    "a": (-0.6, 0.6),    # turn left
    "d": (0.6, -0.6),    # turn right
    " ": (0.0, 0.0),     # stop
}


# -----------------------------
# Teleop Loop
# -----------------------------

def run(stdscr):
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    drive = DriveBase(LEFT_MOTORS, RIGHT_MOTORS)

    stdscr.nodelay(True)
    curses.curs_set(0)
    stdscr.addstr(0, 0, "W/A/S/D to drive, SPACE to stop, Q to quit")
    stdscr.refresh()

    current_left = 0.0
    current_right = 0.0

    try:
        while True:
            key = stdscr.getch()

            if key != -1:
                if key in (ord("q"), ord("Q")):
                    break

                if 0 <= key < 256:
                    ch = chr(key).lower()

                    if ch in COMMANDS:
                        current_left, current_right = COMMANDS[ch]
                        drive.drive(current_left, current_right)
                        stdscr.addstr(2, 0, f"Command: {ch}   ")
                        stdscr.refresh()

            # No timeout — motors keep last command
            time.sleep(0.01)

    finally:
        drive.close()
        GPIO.cleanup()


if __name__ == "__main__":
    curses.wrapper(run)
