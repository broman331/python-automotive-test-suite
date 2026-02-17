
import pytest
from virtual_vehicle.sim.engine import SimulationEngine
from virtual_vehicle.plants.vehicle_dynamics import VehicleDynamics
from virtual_vehicle.utilities.report_generator import ReportGenerator

class TestDynamics:
    @pytest.fixture
    def dynamics_setup(self):
        sim = SimulationEngine(time_step=0.05)
        vehicle = VehicleDynamics('VehicleDynamics', sim.bus)
        sim.add_plant(vehicle)
        return sim, vehicle

    def generate_report(self, sim, test_name, result="PASS"):
        reporter = ReportGenerator()
        reporter.generate(test_name, sim.bus.get_log(), result=result)

    def test_split_mu_braking_instability(self, dynamics_setup):
        """
        Scenario: Braking on split friction surface (Ice on Right).
        Expected: Vehicle pulls to the Left due to differential braking force.
        """
        sim, vehicle = dynamics_setup

        # Initial State
        vehicle.state['v'] = 25.0 # ~90 km/h

        # Set Split-Mu Environment (Left=Dry, Right=Ice)
        sim.bus.broadcast('SET_ENV_MU', {'mu_l': 1.0, 'mu_r': 0.2}, sender='TestHarness')
        sim.step()

        print("\n--- SPLIT-MU BRAKING TEST START ---")

        # Apply Brakes
        sim.bus.broadcast('BRAKE_CMD', 0.5, sender='TestHarness')

        max_yaw_rate = 0.0
        drift_direction = 0 # +ve is Left, -ve is Right

        for i in range(40): # 2 seconds
            sim.step()
            yaw_rate = vehicle.state['yaw_rate']
            if abs(yaw_rate) > abs(max_yaw_rate):
                max_yaw_rate = yaw_rate

            print(f"Time {i*0.05:.2f}s | Speed: {vehicle.state['v']:.2f} | YawRate: {yaw_rate:.4f}")

        print(f"Max Yaw Rate: {max_yaw_rate:.4f}")

        self.generate_report(sim, "Dyn_SplitMu_Instability")

        # Verification
        # 1. Yaw Rate should be significant (instability)
        assert abs(max_yaw_rate) > 0.1, "Split-mu braking should cause significant yaw/drift"

        # 2. Direction check: Left wheels brake harder -> Pull to Left -> Positive Yaw Rate
        assert max_yaw_rate > 0, "Vehicle should pull to the Left (High friction side)"
