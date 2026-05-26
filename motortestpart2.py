#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
from dataclasses import dataclass

PWM_FREQUENCY = 1000  # Hz

@dataclass(frozen=True)
class MotorPins:
    in1: int
    in2: int

class Motor:
    def __init__(self, pins: MotorPins):
        self.pins = pins

        GPIO.setup(pins.in1, GPIO.OUT)
        GPIO.setup(pins.in2, GPIO.OUT)

        # PWM on both pins
        self.pwm_in1 = GPIO.PWM(pins.in1, PWM_FREQUENCY)
        self.pwm_in2 = GPIO.PWM(pins.in2, PWM_FREQUENCY)

        self.pwm_in1.start(0)
        self.pwm_in2.start(0)

    def set_speed(self, speed: float):
        speed = max(-1.0, min(1.0, speed))
        duty = abs(speed) * 100

        if speed > 0:
            # Forward: IN1 = PWM, IN2 = LOW
            self.pwm_in1.ChangeDutyCycle(duty)
            self.pwm_in2.ChangeDutyCycle(0)

        elif speed < 0:
            # Reverse: IN1 = LOW, IN2 = PWM
            self.pwm_in1.ChangeDutyCycle(0)
            self.pwm_in2.ChangeDutyCycle(duty)

        else:
            # Stop
            self.pwm_in1.ChangeDutyCycle(0)
            self.pwm_in2.ChangeDutyCycle(0)

    def stop(self):
        self.set_speed(0)

    def close(self):
        self.stop()
        self.pwm_in1.stop()
        self.pwm_in2.stop()

# DRV8212P pin mapping from your PCB docs
MOTORS = [
    MotorPins(21, 13),  # Motor 1
    MotorPins(20, 6),   # Motor 2
    MotorPins(16, 5),   # Motor 3
    MotorPins(19, 26),  # Motor 4
]

def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    print("Starting DRV8212 Motor Test...")

    try:
        for i, pins in enumerate(MOTORS, start=1):
            print(f"\n--- Testing Motor {i} ---")
            print(f"Pins: IN1={pins.in1}, IN2={pins.in2}")

            motor = Motor(pins)

            print("  Forward (1s)")
            motor.set_speed(0.6)
            time.sleep(1)

            print("  Backward (1s)")
            motor.set_speed(-0.6)
            time.sleep(1)

            print("  Stop")
            motor.stop()
            motor.close()

            time.sleep(0.5)

        print("\nAll motor tests complete.")

    finally:
        GPIO.cleanup()
        print("GPIO cleaned up.")

if __name__ == "__main__":
    main()
