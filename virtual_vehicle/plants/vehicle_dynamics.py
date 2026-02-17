
import math
from virtual_vehicle.plants.base_plant import BasePlant

class VehicleDynamics(BasePlant):
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
        self.L = 2.5  # Wheelbase
        self.track_width = 1.6 # meters
        self.mass = 1500.0 # kg
        self.Iz = 2500.0 # Inertia z-axis
        
        # Friction
        self.mu_left = 1.0
        self.mu_right = 1.0

        # Subscribe to actuator commands
        bus.register(self)

    def receive_message(self, msg_id, data, sender):
        if msg_id == 'STEERING_CMD':
            self.steering_angle = data
        elif msg_id == 'ACCEL_CMD':
            self.throttle = data
        elif msg_id == 'BRAKE_CMD':
            self.brake = data
        elif msg_id == 'SET_ENV_MU':
            self.mu_left = data.get('mu_l', 1.0)
            self.mu_right = data.get('mu_r', 1.0)

    def update_physics(self, dt):
        # Simple Bicycle Model (Kinematic)
        v = self.state['v']
        yaw = self.state['yaw']
        delta = self.steering_angle
        
        # Calculate acceleration
        # Engine Force
        f_drive = self.throttle * 3000.0 # Max thrust 3000N
        
        # Braking Forces (Independent per side)
        # Simplified: Brake input 0-1 maps to max brake force per wheel
        # Total mass 1500kg. 1g decel ~= 15000N. Per side ~= 7500N.
        max_brake_per_side = 8000.0 # N
        f_brake_l = self.brake * max_brake_per_side * self.mu_left
        f_brake_r = self.brake * max_brake_per_side * self.mu_right
        
        total_brake = f_brake_l + f_brake_r
        
        # Net Longitudinal Force
        f_long = f_drive - total_brake
        accel = f_long / self.mass
        
        # Disturbance Moment from Split-Mu Braking
        # If Left brakes harder (f_brake_l > f_brake_r), car rotates Left (+Yaw)
        # Moment = (Force_Left - Force_Right) * (Track / 2)
        # However, braking force opposes motion.
        # Left wheel drag pulls left side back -> Turn Left.
        moment_split_mu = (f_brake_l - f_brake_r) * (self.track_width / 2.0)
        
        # Updates
        self.state['x'] += v * math.cos(yaw) * dt
        self.state['y'] += v * math.sin(yaw) * dt
        self.state['yaw'] += self.state['yaw_rate'] * dt
        
        # Update speed
        v += accel * dt
        if v < 0: 
            v = 0
        self.state['v'] = v
        
        # Lateral Dynamics (simplified)
        # Ideal Yaw Rate = v / L * tan(delta)
        ideal_yaw_rate = (v / self.L) * math.tan(delta)
        
        # Friction Limit (Tire Saturation)
        # Max lateral accel approx 9.8 m/s^2 (1g) on dry road
        max_yaw_rate = 9.8 / (v + 0.1) # Avoid div by zero
        
        # Cap ideal yaw rate
        if abs(ideal_yaw_rate) > max_yaw_rate:
             ideal_yaw_rate = math.copysign(max_yaw_rate, ideal_yaw_rate) * 1.5 # Allow some oversteer/slip

        # Actual Yaw Rate lags behind ideal (representing inertia/tire flex)
        # dy/dt = (ideal - actual) / time_constant
        # Cornering stiffness depends on friction. Lower mu = less stiffness = slower correction/damping.
        avg_mu = (self.mu_left + self.mu_right) / 2.0
        # Time constant increases as mu decreases. 
        # Base tau = 0.2s (Dry). 
        # New tau = 0.2 / avg_mu
        tau = 0.2 / max(avg_mu, 0.1) 
        
        yaw_accel_steering = (ideal_yaw_rate - self.state['yaw_rate']) / tau
        
        # Add disturbance from split-mu
        yaw_accel_disturbance = moment_split_mu / self.Iz
        
        self.state['yaw_rate'] += (yaw_accel_steering + yaw_accel_disturbance) * dt
        
        # Slip Angle (difference between heading and velocity vector)
        # Simplified: proportional to lateral accel (v * yaw_rate)
        lateral_accel = v * self.state['yaw_rate']
        self.state['slip_angle'] = lateral_accel * 0.05 # arbitrary coeff (deg per m/s^2)

        # Efficiency Calculation
        # Power Out = Force * Velocity
        # Power In = Power Out / Efficiency (0.85 for motor/inverter)
        power_out = f_drive * v # Watts
        if power_out > 0:
            power_in = power_out / 0.85
        else:
            # Regen (simplified): 50% regen efficiency
            power_in = power_out * 0.5 
            
        # I = P / V (Nominal 400V for calculation)
        current_demand = power_in / 400.0 
        self.bus.broadcast('LOAD_CURRENT', current_demand, sender=self.name)

    def publish_sensor_data(self):
        # Simulate producing sensor signals
        self.bus.broadcast('WHEEL_SPEED', self.state['v'], sender=self.name)
        self.bus.broadcast('YAW_RATE', self.state['yaw_rate'], sender=self.name)
        self.bus.broadcast('LATERAL_ACCEL', self.state['v'] * self.state['yaw_rate'], sender=self.name)
        self.bus.broadcast('GPS_POS', {'x': self.state['x'], 'y': self.state['y']}, sender=self.name)
        
        # Broadcast Acceleration for Airbag ECU
        # In a real car, this comes from an IMU or specialized crash sensor
        # We use the previous calculated accel from update_physics
        accel_x = (self.state['v'] - self.state.get('prev_v', self.state['v'])) / 0.05 # Approximate derivation
        self.state['prev_v'] = self.state['v']
        self.bus.broadcast('ACCEL_X', accel_x, sender=self.name)
