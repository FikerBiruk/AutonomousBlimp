import lgpio
from dataclasses import dataclass

PWM_FREQUENCY = 1000  # Hz

@dataclass(frozen=True)
class MotorPins:
    in1: int
    in2: int

class Motor:
    def __init__(self, h, pins: MotorPins):
        self.h = h
        self.pins = pins

        # Claim pins as outputs
        lgpio.gpio_claim_output(h, pins.in1)
        lgpio.gpio_claim_output(h, pins.in2)

        # Start PWM at 0% duty
        lgpio.tx_pwm(h, pins.in1, PWM_FREQUENCY, 0)
        lgpio.tx_pwm(h, pins.in2, PWM_FREQUENCY, 0)

    def set_speed(self, speed: float):
        # Clamp to [-1, 1]
        speed = max(-1.0, min(1.0, speed))
        duty = abs(speed) * 100  # convert to %

        if speed > 0:
            # Forward
            lgpio.tx_pwm(self.h, self.pins.in1, PWM_FREQUENCY, duty)
            lgpio.tx_pwm(self.h, self.pins.in2, PWM_FREQUENCY, 0)

        elif speed < 0:
            # Reverse
            lgpio.tx_pwm(self.h, self.pins.in1, PWM_FREQUENCY, 0)
            lgpio.tx_pwm(self.h, self.pins.in2, PWM_FREQUENCY, duty)

        else:
            # Stop
            lgpio.tx_pwm(self.h, self.pins.in1, PWM_FREQUENCY, 0)
            lgpio.tx_pwm(self.h, self.pins.in2, PWM_FREQUENCY, 0)

    def stop(self):
        self.set_speed(0)

# Motor pin mapping from your PCB
MOTOR_PINS = [
    MotorPins(21, 13),  # M1 horizontal left
    MotorPins(20, 6),   # M2 vertical left
    MotorPins(16, 5),   # M3 vertical right
    MotorPins(19, 26),  # M4 horizontal right
]

# Open GPIO chip
h = lgpio.gpiochip_open(0)

# Create motor objects
motors = [Motor(h, p) for p in MOTOR_PINS]

def write_motors(m1, m2, m3, m4):
    motors[0].set_speed(m1)
    motors[1].set_speed(m2)
    motors[2].set_speed(m3)
    motors[3].set_speed(m4)
