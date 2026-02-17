"""
Test Suite for Verification of Failure Reporting.
These tests are INTENTIONALLY designed to fail to demonstrate
reporting capabilities for regressions and defects.
"""
import pytest
from virtual_vehicle.sim.engine import SimulationEngine
from virtual_vehicle.plants.vehicle_dynamics import VehicleDynamics
from virtual_vehicle.ecus.gateway import GatewayECU
from virtual_vehicle.utilities.report_generator import ReportGenerator

class TestKnownFailures:
    """
    Tests that simulate software defects or invalid requirements.
    Expected: FAIL status in reports and pytest summary.
    """
    
    @pytest.fixture
    def setup_sim(self):
        sim = SimulationEngine(time_step=0.1)
        vehicle = VehicleDynamics('VehicleDynamics', sim.bus)
        gateway = GatewayECU('Gateway', sim.bus)
        sim.add_plant(vehicle)
        sim.add_ecu(gateway)
        return sim, vehicle, gateway

    def run_test_safely(self, sim, test_name, assertion_logic):
        """Helper to catch failures and generate report."""
        try:
            assertion_logic()
            ReportGenerator().generate(test_name, list(sim.bus.get_log()), result="PASS")
        except AssertionError as e:
            fail_info = f"Script: {__file__}\nError: {e}"
            ReportGenerator().generate(test_name, list(sim.bus.get_log()), result="FAIL", failure_details=fail_info)
            pytest.fail(f"Test Failed as Expected: {e}")
        except Exception as e:
            err_info = f"Script: {__file__}\nException: {type(e).__name__}: {e}"
            ReportGenerator().generate(test_name, list(sim.bus.get_log()), result="ERROR", failure_details=err_info)
            pytest.fail(f"Test Error: {e}")

    def test_impossible_physics_acceleration(self, setup_sim):
        """
        Scenario: Vehicle accelerates from 0 to 100 m/s in 0.1s.
        Reality: Physics model limits acceleration based on power/mass.
        Failure Reason: Assertion expects unrealistic performance.
        """
        sim, vehicle, _ = setup_sim
        
        def logic():
            vehicle.throttle = 1.0
            sim.step() # 0.1s step
            
            # Expect unrealistic speed (e.g. 0 -> 100m/s in 0.1s = 100g)
            # Actual physics: ~0.5g max for this car
            assert vehicle.state['v'] > 50.0, "Vehicle did not reach warp speed (Impossible Physics)"

        self.run_test_safely(sim, "Fail_Impossible_Acceleration", logic)

    def test_invalid_uds_security_bypass(self, setup_sim):
        """
        Scenario: Attacker tries to unlock ECU without Seed/Key exchange.
        Reality: Gateway rejects invalid access.
        Failure Reason: Test asserts access is granted immediately (Security Hole check).
        """
        sim, _, gateway = setup_sim
        
        def logic():
             # Attacker sends Unlock command directly
            request = {'sid': 0x27, 'sub_fn': 0x02, 'data': 0xFFFF} 
            sim.bus.broadcast('UDS_REQUEST', request, sender='TestHarness')
            sim.step()
            
            # Assertion expects success (which would be a security bug)
            assert gateway.security_unlocked == True, "ECU refused unauthorized unlock (Security is working, so this test fails)"

        self.run_test_safely(sim, "Fail_Security_Bypass", logic)
        
    def test_battery_infinite_capacity(self, setup_sim):
        """
        Scanario: Discharge battery.
        Failure Reason: Assert SoC remains 100% (Perpetual Motion).
        """
        sim, _, _ = setup_sim
        # Need BMS for this, let's mock message or just check logic if appropriate
        # For simplicity, just force a fail in logic
        
        def logic():
            sim.step()
            # Verify entropy reversal
            assert 1 == 2, "Thermodynamics laws still apply"
            
        self.run_test_safely(sim, "Fail_Infinite_Energy", logic)
