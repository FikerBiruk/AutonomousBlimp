import time

class PID:
    def __init__(self, kp, ki, kd, setpoint=0.0, output_limits=(-1.0, 1.0)):
        self.kp = kp
        self.ki = ki
        self.kd = kd

        self.setpoint = setpoint
        self.output_limits = output_limits  # (min, max)

        self._integral = 0.0
        self._prev_error = 0.0
        self._prev_time = None

    def reset(self):
        self._integral = 0.0
        self._prev_error = 0.0
        self._prev_time = None

    def update(self, measurement):
        now = time.monotonic()
        error = self.setpoint - measurement

        if self._prev_time is None:
            dt = 0.0
        else:
            dt = now - self._prev_time

        # Proportional
        p = self.kp * error

        # Integral
        if dt > 0:
            self._integral += error * dt
        i = self.ki * self._integral

        # Derivative
        d = 0.0
        if dt > 0:
            d = self.kd * (error - self._prev_error) / dt

        # Raw output
        output = p + i + d

        # Clamp
        min_out, max_out = self.output_limits
        output = max(min_out, min(max_out, output))

        # Save state
        self._prev_error = error
        self._prev_time = now

        return output
