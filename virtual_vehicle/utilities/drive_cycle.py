
import math

class DriveCycle:
    def __init__(self, name="Micro-WLTP"):
        self.name = name
        # Time (s), Speed (km/h)
        # Simplified cycle: Idle, Accel, Cruise, Decel, Stop
        self.points = [
            (0, 0), (5, 0), # Idle 5s
            (15, 30), # Accel to 30kph
            (25, 30), # Cruise
            (35, 50), # Accel to 50kph
            (45, 50), # Cruise
            (55, 0),  # Decel to Stop
            (60, 0)   # Stop
        ]
    
    def get_target_speed(self, t):
        # Linear interpolation
        if t < 0: return 0.0
        if t >= self.points[-1][0]: return 0.0
        
        for i in range(len(self.points) - 1):
            t1, v1 = self.points[i]
            t2, v2 = self.points[i+1]
            if t1 <= t <= t2:
                ratio = (t - t1) / (t2 - t1)
                speed_kph = v1 + ratio * (v2 - v1)
                return speed_kph / 3.6 # Return m/s

class DriverModel:
    def __init__(self, bus):
        self.bus = bus
        self.current_speed = 0.0
        self.kp = 0.5
        self.ki = 0.1
        self.integral_error = 0.0

    def step(self, target_speed, current_speed, dt):
        error = target_speed - current_speed
        self.integral_error += error * dt
        
        # PI Control
        cmd = self.kp * error + self.ki * self.integral_error
        
        throttle = 0.0
        brake = 0.0
        
        if cmd > 0:
            throttle = min(1.0, cmd)
        else:
            brake = min(1.0, -cmd)
            
        self.bus.broadcast('ACCEL_CMD', throttle, sender='Driver')
        self.bus.broadcast('BRAKE_CMD', brake, sender='Driver')
