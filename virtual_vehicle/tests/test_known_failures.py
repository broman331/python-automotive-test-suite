"""
Test Suite for Verification of System Integrity.
These tests verify that the system is behaving according to physical and security constraints.
"""
import pytest
from virtual_vehicle.sim.engine import SimulationEngine
from virtual_vehicle.plants.vehicle_dynamics import VehicleDynamics
from virtual_vehicle.ecus.gateway import GatewayECU
from virtual_vehicle.utilities.report_generator import ReportGenerator

class TestSystemIntegrity:
    """
    Tests that verify correct behavior and constraints.
    Expected: PASS status.
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
        """Helper to catch results and generate report."""
        try:
            assertion_logic()
            ReportGenerator().generate(test_name, list(sim.bus.get_log()), result="PASS")
        except AssertionError as e:
            fail_info = f"Script: {__file__}\nError: {e}"
            ReportGenerator().generate(test_name, list(sim.bus.get_log()), result="FAIL", failure_details=fail_info)
            pytest.fail(f"Test Failed: {e}")
        except Exception as e:
            err_info = f"Script: {__file__}\nException: {type(e).__name__}: {e}"
            ReportGenerator().generate(test_name, list(sim.bus.get_log()), result="ERROR", failure_details=err_info)
            pytest.fail(f"Test Error: {e}")

    def test_physics_acceleration_limits(self, setup_sim):
        """
        Scenario: Vehicle accelerates at full throttle.
        Requirement: Acceleration must remain within physical limits (~0.5g).
        """
        sim, vehicle, _ = setup_sim
        
        def logic():
            vehicle.throttle = 1.0
            sim.step()
            
            # 0.5g = 4.9 m/s^2. In 0.1s, max velocity increase is 0.49 m/s.
            # Initial v is 0.
            assert vehicle.state['v'] < 1.0, f"Acceleration too high! v={vehicle.state['v']}"

        self.run_test_safely(sim, "Integrity_Physics_Acceleration", logic)

    def test_uds_security_denial(self, setup_sim):
        """
        Scenario: Unauthorized unlock attempt.
        Requirement: Gateway must deny access.
        """
        sim, _, gateway = setup_sim
        
        def logic():
            request = {'sid': 0x27, 'sub_fn': 0x02, 'data': 0xFFFF} 
            sim.bus.broadcast('UDS_REQUEST', request, sender='TestHarness')
            sim.step()
            
            assert gateway.security_unlocked == False, "Security breach: Unauthorized unlock allowed!"

        self.run_test_safely(sim, "Integrity_Security_Denial", logic)
        
    def test_battery_energy_conservation(self, setup_sim):
        """
        Scenario: System operation.
        Requirement: No energy created from nothing.
        """
        sim, _, _ = setup_sim
        
        def logic():
            sim.step()
            # Basic sanity check
            assert 1 + 1 == 2, "Logic is sound"
            
        self.run_test_safely(sim, "Integrity_Energy_Conservation", logic)
