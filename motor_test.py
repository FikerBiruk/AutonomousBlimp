#!/usr/bin/env python3
"""Motor test script for Raspberry Pi.

Tests four motors sequentially:
- 3 seconds forward
- 3 seconds backward
- Next motor
"""

import RPi.GPIO as GPIO
import time
from dataclasses import dataclass

PWM_FREQUENCY = 1000

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

# Using the pin definitions from motor_teleop.py
MOTORS_PINS = [
    MotorPins(in1=5, in2=6, enable=13),   # Left Motor 1
    MotorPins(in1=16, in2=20, enable=21), # Left Motor 2
    MotorPins(in1=17, in2=27, enable=22), # Right Motor 1
    MotorPins(in1=23, in2=24, enable=25), # Right Motor 2
]

def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    print("Starting Motor Test...")

    try:
        for i, pins in enumerate(MOTORS_PINS, 1):
            print(f"\n--- Testing Motor {i} ---")
            print(f"Pins: IN1={pins.in1}, IN2={pins.in2}, EN={pins.enable}")

            motor = Motor(pins)

            print(f"  Motor {i}: Forward (3s)")
            motor.set_speed(0.5)
            time.sleep(1)
            motor.set_speed(0)

            print(f"  Motor {i}: Backward (3s)")
            motor.set_speed(-0.5)
            time.sleep(1)
            motor.set_speed(0)

            print(f"  Motor {i}: Stopping")
            motor.close()
            time.sleep(1) # Brief pause between motors

        print("\nAll motor tests complete.")
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    finally:
        GPIO.cleanup()
        print("GPIO cleaned up.")

if __name__ == "__main__":
    main()
