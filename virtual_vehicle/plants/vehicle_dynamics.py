"""
Vehicle dynamics physics model.
"""
import math
from virtual_vehicle.plants.base_plant import BasePlant

class VehicleDynamics(BasePlant):
    """
    Simulates longitudinal and lateral vehicle dynamics using a kinematic bicycle model.
    """
    def __init__(self, name, bus):
        super().__init__(name, bus)
        # State: [x, y, yaw, velocity, yaw_rate]
        self.state = {
            'x': 0.0,
            'y': 0.0,
            'yaw': 0.0,
            'v': 0.0,
            'yaw_rate': 0.0
        }
        # Inputs
        self.steering_angle = 0.0
        self.throttle = 0.0
        self.brake = 0.0
        # Parameters
        self.wheelbase = 2.5  # Wheelbase (L)
        self.track_width = 1.6 # meters
        self.mass = 1500.0 # kg
        self.inertia_z = 2500.0 # Inertia z-axis (Iz)

        # Friction
        self.mu_left = 1.0
        self.mu_right = 1.0

        # Subscribe to actuator commands
        bus.register(self)

    def receive_message(self, msg_id, data, sender):
        """Handle incoming actuator commands and environment updates."""
        if msg_id == 'STEERING_CMD':
            self.steering_angle = data
        elif msg_id == 'ACCEL_CMD':
            self.throttle = data
        elif msg_id == 'BRAKE_CMD':
            self.brake = data
        elif msg_id == 'SET_ENV_MU':
            self.mu_left = data.get('mu_l', 1.0)
            self.mu_right = data.get('mu_r', 1.0)

    def _calculate_longitudinal_force(self):
        """Calculate net longitudinal force from engine and brakes."""
        f_drive = self.throttle * 3000.0
        max_brake_per_side = 8000.0
        f_brake_l = self.brake * max_brake_per_side * self.mu_left
        f_brake_r = self.brake * max_brake_per_side * self.mu_right
        return f_drive - (f_brake_l + f_brake_r), (f_brake_l - f_brake_r)

    def update_physics(self, dt):
        """Update vehicle state using kinematic bicycle model equations."""
        v = self.state['v']
        yaw = self.state['yaw']

        f_long, f_diff_brake = self._calculate_longitudinal_force()
        accel = f_long / self.mass

        # Updates
        self.state['x'] += v * math.cos(yaw) * dt
        self.state['y'] += v * math.sin(yaw) * dt
        self.state['yaw'] += self.state['yaw_rate'] * dt
        self.state['v'] = max(0, v + accel * dt)

        # Lateral Dynamics
        ideal_yaw_rate = (self.state['v'] / self.wheelbase) * math.tan(self.steering_angle)
        max_yaw_rate = 9.8 / (self.state['v'] + 0.1)

        if abs(ideal_yaw_rate) > max_yaw_rate:
            ideal_yaw_rate = math.copysign(max_yaw_rate, ideal_yaw_rate) * 1.5

        avg_mu = (self.mu_left + self.mu_right) / 2.0
        tau = 0.2 / max(avg_mu, 0.1)

        yaw_accel_steering = (ideal_yaw_rate - self.state['yaw_rate']) / tau
        # Moment = Force_Diff * (Track / 2)
        yaw_accel_disturbance = (f_diff_brake * (self.track_width / 2.0)) / self.inertia_z

        self.state['yaw_rate'] += (yaw_accel_steering + yaw_accel_disturbance) * dt
        self.state['slip_angle'] = (self.state['v'] * self.state['yaw_rate']) * 0.05

        # Efficiency logic
        power_out = (self.throttle * 3000.0) * self.state['v']
        power_in = (power_out / 0.85) if power_out > 0 else (power_out * 0.5)
        self.bus.broadcast('LOAD_CURRENT', power_in / 400.0, sender=self.name)

    def publish_sensor_data(self):
        """Broadcast telemetry and derived sensor data."""
        self.bus.broadcast('WHEEL_SPEED', self.state['v'], sender=self.name)
        self.bus.broadcast('YAW_RATE', self.state['yaw_rate'], sender=self.name)
        self.bus.broadcast('LATERAL_ACCEL', self.state['v'] * self.state['yaw_rate'], sender=self.name)
        self.bus.broadcast('GPS_POS', {'x': self.state['x'], 'y': self.state['y']}, sender=self.name)

        # Acceleration for Airbag ECU
        accel_x = (self.state['v'] - self.state.get('prev_v', self.state['v'])) / 0.05
        self.state['prev_v'] = self.state['v']
        self.bus.broadcast('ACCEL_X', accel_x, sender=self.name)
