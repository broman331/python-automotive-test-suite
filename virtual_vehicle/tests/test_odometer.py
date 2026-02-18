"""
Comprehensive Test Suite for the Odometer and Trip Meter (Body ECU).
Verifies distance accumulation, monotonicity, persistence, and reset logic.
"""
import pytest
import os
import json
from virtual_vehicle.sim.engine import SimulationEngine
from virtual_vehicle.plants.vehicle_dynamics import VehicleDynamics
from virtual_vehicle.ecus.body_ecu import BodyECU
from virtual_vehicle.utilities.report_generator import ReportGenerator

class TestOdometer:
    
    @pytest.fixture
    def odo_setup(self, tmp_path):
        # Use a temporary file for NVM storage to avoid side effects
        nvm_file = str(tmp_path / "odo_nvm.json")
        sim = SimulationEngine(time_step=0.05)
        vehicle = VehicleDynamics('VehicleDynamics', sim.bus)
        body = BodyECU('BodyECU', sim.bus, storage_path=nvm_file)
        
        sim.add_plant(vehicle)
        sim.add_ecu(body)
        
        return sim, vehicle, body, nvm_file

    def generate_report(self, sim, test_name, result="PASS"):
        ReportGenerator().generate(test_name, list(sim.bus.get_log()), result)

    def test_accumulation_at_constant_speed(self, odo_setup):
        """
        Scenario: Drive at 72 km/h (20 m/s) for 5 seconds.
        Expected: Total distance should be 100 meters (0.1 km).
        """
        sim, vehicle, body, _ = odo_setup
        
        # 1. Start Driving
        vehicle.state['v'] = 20.0 # 20 m/s
        
        # 2. Run for 5 seconds (100 steps at 0.05s)
        for _ in range(100):
            sim.step()
            
        print(f"Total Mileage: {body.total_mileage:.2f} meters")
        
        # Tolerance check (floating point integration might have tiny error)
        assert abs(body.total_mileage - 100.0) < 0.1, f"Expected 100.0m, got {body.total_mileage}m"
        assert abs(body.trip_meter - 100.0) < 0.1
        
        self.generate_report(sim, "Odo_Accumulation_Constant")

    def test_monotonicity_reverse_driving(self, odo_setup):
        """
        Scenario: Drive backwards at 10 m/s.
        Expected: Odometer should still INCREASE.
        """
        sim, vehicle, body, _ = odo_setup
        
        # 1. Drive Backwards
        vehicle.state['v'] = -10.0 
        
        for _ in range(20): # 1 second
            sim.step()
            
        assert body.total_mileage > 0, "Odometer should increase even when driving in reverse"
        assert abs(body.total_mileage - 10.0) < 0.01, f"Expected 10m, got {body.total_mileage}"
        
        self.generate_report(sim, "Odo_Reverse_Monotonicity")

    def test_trip_meter_reset(self, odo_setup):
        """
        Scenario: Accumulate distance, then reset trip meter.
        Expected: Trip meter becomes 0, Odometer remains SAME.
        """
        sim, vehicle, body, _ = odo_setup
        
        # 1. Drive 50 meters
        vehicle.state['v'] = 10.0
        for _ in range(100): # 5 seconds
            sim.step()
            
        initial_total = body.total_mileage
        assert body.trip_meter > 0
        
        # 2. Reset Trip
        sim.bus.broadcast('RESET_TRIP', None, sender='TestHarness')
        # We don't call sim.step() yet because that would immediately add distance
        # We check state immediately
        assert body.trip_meter == 0.0, "Trip meter should be reset to zero"
        
        # 3. Drive one more step and verify it's ONLY that step
        sim.step()
        assert body.trip_meter > 0 and body.trip_meter < 1.0, f"Trip meter should start from 0, got {body.trip_meter}"
        assert body.total_mileage > initial_total, "Total odometer should NOT be reset"
        
        self.generate_report(sim, "Odo_Trip_Reset")

    def test_persistence_across_restarts(self, odo_setup):
        """
        Scenario: Drive, Save to NVM, Restart ECU.
        Expected: Odometer resumes from saved value.
        """
        sim1, vehicle1, body1, nvm_path = odo_setup
        
        # 1. Run simulation 1
        vehicle1.state['v'] = 20.0
        for _ in range(20): # 1 second
            sim1.step()
        
        captured_mileage = body1.total_mileage
        assert captured_mileage > 0
        
        # 2. Persist data
        body1.save_to_nvm()
        
        # 3. Create NEW simulation/ECU using same storage
        sim2 = SimulationEngine(time_step=0.05)
        body2 = BodyECU('BodyECU_v2', sim2.bus, storage_path=nvm_path)
        
        assert body2.total_mileage == captured_mileage, f"Persistence failed! Expected {captured_mileage}, got {body2.total_mileage}"
        
        # 4. Continue driving
        sim2.add_ecu(body2)
        # Mock speed on sim2 bus
        sim2.bus.broadcast('WHEEL_SPEED', 10.0, sender='External')
        sim2.step()
        
        assert body2.total_mileage > captured_mileage, "Odometer should continue from persisted value"
        
        self.generate_report(sim1, "Odo_Persistence_Verification")

    def test_high_mileage_overflow_safety(self, tmp_path):
        """
        Scenario: Set odometer to just below a typical display limits (999,999 km).
        Expected: No crash or negative rollover (within Python limits).
        """
        nvm_file = str(tmp_path / "overflow_odo.json")
        high_val = 999_999_000.0 # 999,999 km in meters
        
        with open(nvm_file, 'w') as f:
            json.dump({'total_mileage': high_val, 'trip_meter': high_val}, f)
            
        sim = SimulationEngine(time_step=0.05)
        body = BodyECU('HighOdoECU', sim.bus, storage_path=nvm_file)
        
        # Drive 1000m
        sim.bus.broadcast('WHEEL_SPEED', 10.0, sender='Test')
        for _ in range(2000): # 100 seconds
            sim.step()
            
        assert body.total_mileage > high_val
        print(f"Odometer after overflow test: {body.total_mileage/1000.0:.3f} km")
        
        self.generate_report(sim, "Odo_High_Mileage_Stability")
