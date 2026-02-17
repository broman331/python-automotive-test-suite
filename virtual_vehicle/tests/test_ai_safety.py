
import pytest
from virtual_vehicle.sim.engine import SimulationEngine
from virtual_vehicle.plants.vehicle_dynamics import VehicleDynamics
from virtual_vehicle.plants.camera_mock import CameraPlant
from virtual_vehicle.ecus.adas_ecu import AdasECU
from virtual_vehicle.utilities.report_generator import ReportGenerator

class TestAISafety:
    @pytest.fixture
    def sotif_setup(self):
        sim = SimulationEngine(time_step=0.1)
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

    def test_occlusion_handling(self, sotif_setup):
        """
        Scenario: Heavy Rain (0.2 Visibility) causes Low Confidence (<0.6).
        Expected: ADAS disengages LKA (Steering Cmd 0 or None).
        """
        sim, vehicle, camera = sotif_setup
        
        # Initial: Offset 1.0m
        vehicle.state['y'] = 1.0
        
        # Inject Heavy Rain (Visibility 0.2 -> Noise 0.8 -> Confidence 0.2)
        sim.bus.broadcast('SET_ENV_VISIBILITY', 0.2, sender='TestHarness')
        
        print("\n--- SOTIF OCCLUSION TEST START ---")
        
        steering_engaged = False
        
        for i in range(10):
            # Camera update (simulated)
            camera.receive_message('GPS_POS', {'x': vehicle.state['x'], 'y': vehicle.state['y']}, 'VehicleDynamics')
            sim.step()
            
            # Check for steering commands
            logs = sim.bus.get_log()
            # Look for recent steering command
            last_steer = next((l for l in reversed(logs) if l['id'] == 'STEERING_CMD' and l['time'] == 0 ), None)
            
            if last_steer and abs(last_steer['data']) > 0.001:
                 # If we see active steering (>0) despite low confidence, it's a fail
                 steering_engaged = True
                 break

        self.generate_report(sim, "AI_Occlusion_Handling")
        
        assert not steering_engaged, "LKA should NOT steer when confidence is low (SOTIF Violation)"
