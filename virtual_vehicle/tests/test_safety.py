
import pytest
from virtual_vehicle.sim.engine import SimulationEngine
from virtual_vehicle.plants.vehicle_dynamics import VehicleDynamics
from virtual_vehicle.plants.radar_generator import RadarGenerator
from virtual_vehicle.ecus.adas_ecu import AdasECU
from virtual_vehicle.sim.fault_injector import FaultInjector
from virtual_vehicle.utilities.report_generator import ReportGenerator

class TestSafety:
    @pytest.fixture
    def safety_setup(self):
        sim = SimulationEngine(time_step=0.1)
        vehicle = VehicleDynamics('VehicleDynamics', sim.bus)
        radar = RadarGenerator('RadarGen', sim.bus)
        adas = AdasECU('ADAS_ECU', sim.bus)
        
        sim.add_plant(vehicle)
        sim.add_plant(radar)
        sim.add_ecu(adas)
        
        # Add Fault Injector
        injector = FaultInjector()
        sim.bus.set_fault_injector(injector)
        
        return sim, vehicle, radar, adas, injector

    def generate_report(self, sim, test_name, result="PASS"):
        reporter = ReportGenerator()
        reporter.generate(test_name, sim.bus.get_log(), result=result)

    def test_brake_command_loss(self, safety_setup):
        """
        Scenario: AEB is needed, but BRAKE_CMD messages are dropped.
        Expected: Collision (demonstrates hazard). ADAS logic works, but actuation fails.
        """
        sim, vehicle, radar, adas, injector = safety_setup
        
        # Setup Collision Scenario
        vehicle.state['v'] = 20.0
        radar.add_object(obj_id=1, dist=60.0, rel_speed=-20.0) # 3s to impact
        
        # Inject Fault: Drop BRAKE_CMD messages
        injector.inject(fault_type='DROP', target_id='BRAKE_CMD')
        
        collision = False
        for _ in range(50):
            sim.step()
            if vehicle.state['v'] == 0:
                break
            # Check for collision (dist < 0)
            if radar.objects and radar.objects[0]['dist'] < 0:
                collision = True
                break
        
        self.generate_report(sim, "Safety_BrakeCmdLoss", result="FAIL" if collision else "PASS")
        
        assert adas.aeb_triggered, "ADAS should have TRIED to brake"
        assert collision, "With brakes failed, collision SHOULD occur (validating the fault injector)"

    def test_radar_data_corruption(self, safety_setup):
        """
        Scenario: Radar sends corrupted data.
        Expected: ADAS ECU catches error, does not crash, and does not trigger unsafe AEB.
        """
        sim, vehicle, radar, adas, injector = safety_setup
        
        vehicle.state['v'] = 20.0
        # No physical objects
        
        # Inject Fault: Corrupt RADAR_OBJECTS messages
        injector.inject(fault_type='CORRUPT', target_id='RADAR_OBJECTS')
        
        # Trigger a radar update
        radar.publish_sensor_data()
        sim.step()
        sim.step()
        
        self.generate_report(sim, "Safety_RadarCorruption")
        
        # Correct behavior: System remains stable, no crash, AEB off
        assert not adas.aeb_triggered, "AEB should NOT trigger on corrupted data"
        # We also implicitly check (by the test finishing) that the ECU code didn't raise an unhandled exception
