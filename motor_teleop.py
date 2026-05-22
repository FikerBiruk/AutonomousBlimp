#!/usr/bin/env python3
"""Keyboard teleop for four DC motors over SSH.

Controls:
- w: forward
- s: reverse
- a: turn left
- d: turn right
- space: stop
- q: quit

This script assumes two motors on the left side and two motors on the right
side. Edit the pin numbers below to match your motor driver wiring.

Run it from an SSH session on the Pi:
    sudo python3 motor_teleop.py
"""

from __future__ import annotations

import curses
import time
from dataclasses import dataclass
from typing import Iterable

import RPi.GPIO as GPIO


PWM_FREQUENCY = 1000
HOLD_TIMEOUT_SECONDS = 0.20


@dataclass(frozen=True)
class MotorPins:
    in1: int
    in2: int
    enable: int


class Motor:
    def __init__(self, pins: MotorPins) -> None:
        self._pins = pins
        GPIO.setup(self._pins.in1, GPIO.OUT)
        GPIO.setup(self._pins.in2, GPIO.OUT)
        GPIO.setup(self._pins.enable, GPIO.OUT)
        self._pwm = GPIO.PWM(self._pins.enable, PWM_FREQUENCY)
        self._pwm.start(0)
        self.stop()

    def set_speed(self, speed: float) -> None:
        speed = max(-1.0, min(1.0, speed))
        duty_cycle = abs(speed) * 100.0

        if speed > 0:
            GPIO.output(self._pins.in1, GPIO.HIGH)
            GPIO.output(self._pins.in2, GPIO.LOW)
            self._pwm.ChangeDutyCycle(duty_cycle)
        elif speed < 0:
            GPIO.output(self._pins.in1, GPIO.LOW)
            GPIO.output(self._pins.in2, GPIO.HIGH)
            self._pwm.ChangeDutyCycle(duty_cycle)
        else:
            self.stop()

    def stop(self) -> None:
        GPIO.output(self._pins.in1, GPIO.LOW)
        GPIO.output(self._pins.in2, GPIO.LOW)
        self._pwm.ChangeDutyCycle(0)

    def close(self) -> None:
        self.stop()
        self._pwm.stop()


class DriveBase:
    def __init__(self, left_motors: Iterable[MotorPins], right_motors: Iterable[MotorPins]) -> None:
        self._left = [Motor(pins) for pins in left_motors]
        self._right = [Motor(pins) for pins in right_motors]

    def drive(self, left_speed: float, right_speed: float) -> None:
        for motor in self._left:
            motor.set_speed(left_speed)
        for motor in self._right:
            motor.set_speed(right_speed)

    def stop(self) -> None:
        self.drive(0.0, 0.0)

    def close(self) -> None:
        self.stop()
        for motor in self._left + self._right:
            motor.close()


# Replace these with your actual GPIO pins.
LEFT_MOTORS = [
    MotorPins(in1=5, in2=6, enable=13),
    MotorPins(in1=16, in2=20, enable=21),
]
RIGHT_MOTORS = [
    MotorPins(in1=17, in2=27, enable=22),
    MotorPins(in1=23, in2=24, enable=25),
]


COMMANDS = {
    "w": (1.0, 1.0),
    "s": (-1.0, -1.0),
    "a": (-1.0, 1.0),
    "d": (1.0, -1.0),
    " ": (0.0, 0.0),
}


def run(stdscr: curses.window) -> None:
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    drive_base = DriveBase(LEFT_MOTORS, RIGHT_MOTORS)

    stdscr.nodelay(True)
    stdscr.keypad(True)
    curses.curs_set(0)
    stdscr.clear()
    stdscr.addstr(0, 0, "W/A/S/D to drive, space to stop, q to quit")
    stdscr.addstr(1, 0, "Hold keys down. Motors stop shortly after key repeat ends.")
    stdscr.refresh()

    last_command_time = 0.0
    active = False

    try:
        while True:
            key_code = stdscr.getch()
            if key_code != -1:
                if key_code in (ord("q"), ord("Q")):
                    break

                if 0 <= key_code < 256:
                    key = chr(key_code).lower()
                    if key in COMMANDS:
                        left_speed, right_speed = COMMANDS[key]
                        drive_base.drive(left_speed, right_speed)
                        active = (left_speed != 0.0) or (right_speed != 0.0)
                        last_command_time = time.monotonic()
                        stdscr.addstr(3, 0, f"Key: {key}   ")
                        stdscr.refresh()

            if active and (time.monotonic() - last_command_time) > HOLD_TIMEOUT_SECONDS:
                drive_base.stop()
                active = False
                stdscr.addstr(3, 0, "Key: stop   ")
                stdscr.refresh()

            time.sleep(0.01)
    finally:
        drive_base.close()
        GPIO.cleanup()


if __name__ == "__main__":
    curses.wrapper(run)
