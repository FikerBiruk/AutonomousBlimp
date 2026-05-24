import RPi.GPIO as GPIO
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

# Motor pin mapping from your PCB
MOTOR_PINS = [
    MotorPins(21, 13),  # M1
    MotorPins(20, 6),   # M2
    MotorPins(16, 5),   # M3
    MotorPins(19, 26),  # M4
]

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Create motor objects
motors = [Motor(p) for p in MOTOR_PINS]

def write_motors(m1, m2, m3, m4):
    motors[0].set_speed(m1)
    motors[1].set_speed(m2)
    motors[2].set_speed(m3)
    motors[3].set_speed(m4)
