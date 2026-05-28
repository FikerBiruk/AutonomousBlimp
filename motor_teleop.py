#!/usr/bin/env python3
import sys
import termios
import tty
import time
import RPi.GPIO as GPIO
from dataclasses import dataclass

PWM_FREQUENCY = 1000

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

# Motor mapping
MOTOR_PINS = [
    MotorPins(21, 13),  # Motor 1 (front-left)
    MotorPins(20, 6),   # Motor 2 (vertical-left)
    MotorPins(16, 5),   # Motor 3 (vertical-right)
    MotorPins(19, 26),  # Motor 4 (front-right)
]

def getch():
    """Non-blocking single keypress reader."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch

def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    motors = [Motor(p) for p in MOTOR_PINS]

    print("\nKeyboard Teleop Active")
    print("Controls:")
    print("  W = forward")
    print("  S = backward")
    print("  A = turn left")
    print("  D = turn right")
    print("  E = up")
    print("  Q = down")
    print("  X = stop all")
    print("  Z = quit\n")

    forward_speed = 0.6
    turn_speed = 0.6
    vertical_speed = 0.6

    try:
        while True:
            key = getch()

            if key == "w":
                motors[0].set_speed(forward_speed)
                motors[3].set_speed(forward_speed)

            elif key == "s":
                motors[0].set_speed(-forward_speed)
                motors[3].set_speed(-forward_speed)

            elif key == "a":
                motors[0].set_speed(-turn_speed)
                motors[3].set_speed(turn_speed)

            elif key == "d":
                motors[0].set_speed(turn_speed)
                motors[3].set_speed(-turn_speed)

            elif key == "e":
                motors[1].set_speed(vertical_speed)
                motors[2].set_speed(vertical_speed)

            elif key == "q":
                motors[1].set_speed(-vertical_speed)
                motors[2].set_speed(-vertical_speed)

            elif key == "x":
                for m in motors:
                    m.stop()

            elif key == "z":
                break

    finally:
        for m in motors:
            m.stop()
        GPIO.cleanup()
        print("\nTeleop ended. Motors stopped.")

if __name__ == "__main__":
    main()
