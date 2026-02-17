"""
Advanced Dynamics Test Suite.
Verifies Understeer/Oversteer behavior and stability limits.
"""
import pytest
from virtual_vehicle.sim.engine import SimulationEngine
from virtual_vehicle.plants.vehicle_dynamics import VehicleDynamics
from virtual_vehicle.utilities.report_generator import ReportGenerator

class TestDynamicsAdvanced:
    """Test cases for vehicle stability and handling."""
    
    @pytest.fixture
    def dynamics_setup(self):
        sim = SimulationEngine(time_step=0.05)
        vehicle = VehicleDynamics('VehicleDynamics', sim.bus)
        sim.add_plant(vehicle)
        return sim, vehicle

    def generate_report(self, sim, test_name, result="PASS"):
        reporter = ReportGenerator()
        reporter.generate(test_name, list(sim.bus.get_log()), result=result)

    def test_understeer_behavior(self, dynamics_setup):
        """
        Scenario: High speed cornering with low front friction.
        Expected: Vehicle path radius > Ideal radius (Understeer).
        Yaw Rate should be less than Ideal Yaw Rate.
        """
        sim, vehicle = dynamics_setup
        
        # 1. Setup Understeer Condition (Low Front Friction)
        vehicle.track_width = 1.6
        vehicle.mu_left = 0.5 # Front/Rear split isn't direct in my detailed model, 
                              # but modifying global mu affects both. 
                              # My simple model doesn't have separate front/rear mu param yet.
                              # I will hack it by saturating front tires earlier in the model logic
                              # OR just relying on the physics that high speed + steering = understeer naturally if not RWD power oversteer.
        
        # Actually my model uses mu_left/mu_right, not front/rear.
        # So I will test "Low Friction Cornering" generally.
        vehicle.mu_left = 0.4
        vehicle.mu_right = 0.4
        
        # 2. Accelerate to 20 m/s
        vehicle.state['v'] = 25.0 
        
        # 3. Constant Steering Input (Step Input)
        vehicle.steering_angle = 0.1 # rad (~5.7 deg)
        steering_applied = False
        
        max_yaw_rate = 0.0
        
        for i in range(40): # 2 seconds
            sim.step()
            yaw_rate = abs(vehicle.state['yaw_rate'])
            if yaw_rate > max_yaw_rate:
                max_yaw_rate = yaw_rate
                
        # Ideal Yaw Rate = v / L * tan(delta)
        # 25 / 2.5 * tan(0.1) ~= 1.0 rad/s
        ideal_yaw = (25.0 / 2.5) * 0.1
        
        # Check Lateral Acceleration instead of Yaw Rate directly
        logs = sim.bus.get_log()
        max_lat_accel = 0.0
        for l in logs:
            if l['id'] == 'LATERAL_ACCEL':
                accel = abs(l['data']) # m/s^2
                if accel > max_lat_accel:
                    max_lat_accel = accel
        
        print(f"Max Lat Accel: {max_lat_accel:.3f} m/s^2")
        
        # Theoretical limit: mu * g = 0.4 * 9.81 = 3.924 m/s^2
        # Allow slight overshoot due to dynamic effects/damping but enforce saturation.
        # It should NOT reach ideal lateral accel (v * ideal_yaw = 25 * 1.0 = 25 m/s^2)
        
        assert max_lat_accel < 5.0, "Lateral Acceleration exceeded friction limits (should be ~4.0)"
        assert max_yaw_rate < ideal_yaw * 0.9, "Yaw Rate did not show understeer behavior"
        
        self.generate_report(sim, "Dynamics_Understeer")

    def test_oversteer_correction(self, dynamics_setup):
        """
        Scenario: Split-Mu Braking induces yaw.
        Expected: Yaw rate develops, then damps out (natural stability).
        """
        sim, vehicle = dynamics_setup
        
        vehicle.state['v'] = 30.0
        vehicle.mu_left = 1.0
        vehicle.mu_right = 0.5
        vehicle.brake = 1.0 # Full braking
        
        # No steering
        vehicle.steering_angle = 0.0
        
        # Simulate
        peak_yaw = 0.0
        final_yaw = 0.0
        
        for i in range(20): # 1 second
            sim.step()
            yaw = vehicle.state['yaw_rate']
            if abs(yaw) > abs(peak_yaw):
                peak_yaw = yaw
            final_yaw = yaw
            
        print(f"Peak Yaw: {peak_yaw:.3f}, Final Yaw: {final_yaw:.3f}")
        
        # Split friction braking creates a moment.
        assert abs(peak_yaw) > 0.05, "No yaw moment generated from split-mu braking"
        # Natural damping should reduce it
        assert abs(final_yaw) < abs(peak_yaw), "Vehicle unstable/spinning out (no damping)"
        
        self.generate_report(sim, "Dynamics_Oversteer_Damping")
