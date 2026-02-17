
import pytest
from virtual_vehicle.sim.engine import SimulationEngine
from virtual_vehicle.plants.vehicle_dynamics import VehicleDynamics
from virtual_vehicle.plants.camera_mock import CameraPlant
from virtual_vehicle.ecus.adas_ecu import AdasECU
from virtual_vehicle.utilities.report_generator import ReportGenerator

class TestPerception:
    @pytest.fixture
    def perc_setup(self):
        sim = SimulationEngine(time_step=0.05)
        vehicle = VehicleDynamics('VehicleDynamics', sim.bus)
        camera = CameraPlant('Camera', sim.bus)
        adas = AdasECU('ADAS_ECU', sim.bus)

        sim.add_plant(vehicle)
        sim.add_plant(camera)
        sim.add_ecu(adas)

        return sim, vehicle, camera

    def generate_report(self, sim, test_name, result="PASS"):
        reporter = ReportGenerator()
        reporter.generate(test_name, sim.bus.get_log(), result=result)

    def test_lka_centering(self, perc_setup):
        """
        Scenario: Vehicle starts with 1.0m lateral offset.
        Expected: LKA steers to reduce offset to near zero.
        """
        sim, vehicle, camera = perc_setup

        # Initial Conditions
        vehicle.state['v'] = 20.0
        vehicle.state['y'] = 1.0 # 1m offset

        print("\n--- LKA CENTERING TEST START ---")

        initial_offset = vehicle.state['y']
        min_offset = initial_offset

        for i in range(100): # 5 seconds
            # Update Camera with current vehicle pos
            camera.receive_message('GPS_POS', {'x': vehicle.state['x'], 'y': vehicle.state['y']}, 'VehicleDynamics')
            camera.receive_message('YAW', vehicle.state['yaw'], 'VehicleDynamics')

            sim.step()

            current_offset = abs(vehicle.state['y'])
            if current_offset < min_offset:
                min_offset = current_offset

            if i % 10 == 0:
                print(f"Time {i*0.05:.2f}s | Offset: {vehicle.state['y']:.3f}m | Steer: {vehicle.steering_angle:.3f} rad")

        self.generate_report(sim, "Perc_LKA_Centering")

        print(f"Final Offset: {vehicle.state['y']:.3f}m")

        # Verification
        assert min_offset < 0.2, f"LKA failed to center vehicle. Min offset was {min_offset:.2f}m"
        assert abs(vehicle.state['y']) < 0.5, "Vehicle drifted too far (unstable LKA)"
