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
        new_v = v + accel * dt
        # Clamp at zero if we cross it (braking/acceleration limit)
        if (v > 0 and new_v < 0) or (v < 0 and new_v > 0):
            new_v = 0
            
        self.state['v'] = new_v

        # Lateral Dynamics (Enhanced Bicycle Model)
        # Calculate tire slip angles
        if v > 1.0:
            # Alpha F = Steering - (Vy + lf*omega) / Vx
            alpha_f = self.steering_angle - (self.state['yaw_rate'] * 1.25) / v # assuming Vy~0
            
            # Alpha R = - (Vy - lr*omega) / Vx
            # If Vy~0, Alpha R = - (-lr*omega) / Vx = + lr*omega / Vx
            alpha_r = (self.state['yaw_rate'] * 1.25) / v
        else:
            alpha_f = 0
            alpha_r = 0

        # Cornering Stiffness (Linear region)
        C_alpha_f = 60000.0 # N/rad
        C_alpha_r = 60000.0 # N/rad

        # Lateral Forces with Saturation (Brush Model Approximation)
        # Max Force = Normal Load * mu
        # Assume 50/50 weight dist for simplicity
        F_z_f = self.mass * 9.81 * 0.5 
        F_z_r = self.mass * 9.81 * 0.5
        
        Fy_max_f = F_z_f * self.mu_left
        Fy_max_r = F_z_r * self.mu_right
        
        # Raw Linear Force
        Fy_f_raw = C_alpha_f * alpha_f
        Fy_r_raw = C_alpha_r * alpha_r
        
        # Saturation
        Fy_f = max(-Fy_max_f, min(Fy_max_f, Fy_f_raw))
        Fy_r = max(-Fy_max_r, min(Fy_max_r, Fy_r_raw))

        # Understeer Gradient (K_us)
        # Yaw Moment sum
        moment_friction = Fy_f * (self.wheelbase/2) - Fy_r * (self.wheelbase/2)
        
        # Add disturbance from split-mu braking
        yaw_accel_disturbance = (f_diff_brake * (self.track_width / 2.0)) / self.inertia_z
        
        # Total Yaw Accel
        yaw_accel = moment_friction / self.inertia_z + yaw_accel_disturbance
        self.state['yaw_rate'] += yaw_accel * dt
        
        # Damping (natural tire scrub and air resistance to rotation)
        self.state['yaw_rate'] *= 0.98 

        self.state['slip_angle'] = alpha_r # Approx slip angle at CG

        # Calculate Lateral Acceleration (Sensor)
        # Ay = (Fy_f + Fy_r) / m
        self.state['lat_accel'] = (Fy_f + Fy_r) / self.mass

        # Efficiency logic
        power_out = (self.throttle * 3000.0) * self.state['v']
        power_in = (power_out / 0.85) if power_out > 0 else (power_out * 0.5)
        self.bus.broadcast('LOAD_CURRENT', power_in / 400.0, sender=self.name)

    def publish_sensor_data(self):
        """Broadcast telemetry and derived sensor data."""
        self.bus.broadcast('WHEEL_SPEED', self.state['v'], sender=self.name)
        self.bus.broadcast('YAW_RATE', self.state['yaw_rate'], sender=self.name)
        self.bus.broadcast('LATERAL_ACCEL', self.state.get('lat_accel', 0.0), sender=self.name)
        self.bus.broadcast('GPS_POS', {'x': self.state['x'], 'y': self.state['y']}, sender=self.name)

        # Acceleration for Airbag ECU
        accel_x = (self.state['v'] - self.state.get('prev_v', self.state['v'])) / 0.05
        self.state['prev_v'] = self.state['v']
        self.bus.broadcast('ACCEL_X', accel_x, sender=self.name)
