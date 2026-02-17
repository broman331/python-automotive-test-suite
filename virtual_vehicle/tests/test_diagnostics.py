"""
Test Suite for UDS (ISO 14229) Diagnostics.
Verifies Gateway ECU handling of services 0x10, 0x22, 0x27, 0x31.
"""
import pytest
from virtual_vehicle.sim.engine import SimulationEngine
from virtual_vehicle.ecus.gateway import GatewayECU
from virtual_vehicle.utilities.report_generator import ReportGenerator

class TestDiagnostics:
    """Test cases for UDS protocol implementation."""
    
    @pytest.fixture
    def uds_setup(self):
        """Setup simulation with Gateway ECU."""
        sim = SimulationEngine(time_step=0.1)
        gateway = GatewayECU('Gateway', sim.bus)
        sim.add_ecu(gateway)
        return sim, gateway

    def generate_report(self, sim, test_name, result="PASS"):
        """Helper to generate HTML report."""
        reporter = ReportGenerator()
        reporter.generate(test_name, sim.bus.get_log(), result=result)

    def test_session_control(self, uds_setup):
        """
        Scenario: Tester requests Diagnostic Session Control (0x10).
        Expected: Gateway switches session and returns positive response (0x50).
        """
        sim, _ = uds_setup
        
        # Test Case 1: Default Session (0x01)
        request = {'sid': 0x10, 'sub_fn': 0x01}
        sim.bus.broadcast('UDS_REQUEST', request, sender='TestHarness')
        sim.step()
        
        logs = sim.bus.get_log()
        response = next((l for l in logs if l['id'] == 'UDS_RESPONSE'), None)
        
        assert response is not None, "Gateway did not respond to UDS request"
        assert response['data']['sid'] == 0x50, "Incorrect Response Service ID"
        assert response['data']['sub_fn'] == 0x01
        
        # Test Case 2: Invalid Sub-function
        request = {'sid': 0x10, 'sub_fn': 0xFF}
        sim.bus.broadcast('UDS_REQUEST', request, sender='TestHarness')
        sim.step()
        
        logs = list(sim.bus.get_log())[-10:] # Get recent logs
        response = next((l for l in logs if l['id'] == 'UDS_RESPONSE' and l['data']['sid'] == 0x7F), None)
        
        assert response is not None, "Gateway did not send Negative Response"
        assert response['data']['nrc'] == 0x12, "Incorrect NRC for invalid sub-function"
        
        self.generate_report(sim, "UDS_Session_Control")

    def test_read_data_by_identifier(self, uds_setup):
        """
        Scenario: Tester requests Read Data By ID (0x22).
        Expected: Gateway returns value for known DIDs (VIN, Voltage).
        """
        sim, _ = uds_setup
        
        # Test Case 1: Read VIN (0xF190)
        request = {'sid': 0x22, 'did': 0xF190}
        sim.bus.broadcast('UDS_REQUEST', request, sender='TestHarness')
        sim.step()
        
        logs = list(sim.bus.get_log())[-10:]
        response = next((l for l in logs if l['id'] == 'UDS_RESPONSE' and l['data']['sid'] == 0x62), None)
        
        assert response is not None
        assert response['data']['data'] == "1FA-VIRTUAL-CAR-001"
        
        self.generate_report(sim, "UDS_Read_Data")

    def test_security_access(self, uds_setup):
        """
        Scenario: Tester requests Security Access (0x27).
        Expected: Seed generation -> Key validation -> Unlock.
        """
        sim, gateway = uds_setup
        
        # 1. Request Seed (0x01)
        req_seed = {'sid': 0x27, 'sub_fn': 0x01}
        sim.bus.broadcast('UDS_REQUEST', req_seed, sender='TestHarness')
        sim.step()
        
        logs = list(sim.bus.get_log())[-10:]
        resp_seed = next((l for l in logs if l['id'] == 'UDS_RESPONSE' and l['data']['sid'] == 0x67), None)
        
        seed = resp_seed['data']['data']
        assert isinstance(seed, int)
        
        # 2. Send Invalid Key (0x02)
        req_key_bad = {'sid': 0x27, 'sub_fn': 0x02, 'data': seed + 999}
        sim.bus.broadcast('UDS_REQUEST', req_key_bad, sender='TestHarness')
        sim.step()
        
        logs = list(sim.bus.get_log())[-10:]
        # Find the *latest* response, start search from end
        resp_bad = None
        for l in reversed(logs):
             if l['id'] == 'UDS_RESPONSE' and l['data']['sid'] == 0x7F:
                 resp_bad = l
                 break
        
        assert resp_bad is not None
        assert resp_bad['data']['nrc'] == 0x35 # Invalid Key
        
        # 3. Send Valid Key (0x02)
        req_key_good = {'sid': 0x27, 'sub_fn': 0x02, 'data': seed + 1}
        sim.bus.broadcast('UDS_REQUEST', req_key_good, sender='TestHarness')
        sim.step()
        
        logs = list(sim.bus.get_log())[-10:]
        resp_good = None
        for l in reversed(logs):
             if l['id'] == 'UDS_RESPONSE' and l['data']['sid'] == 0x67:
                 resp_good = l
                 break
                 
        assert resp_good is not None
        assert resp_good['data']['data'] == "UNLOCKED"
        assert gateway.security_unlocked == True

        self.generate_report(sim, "UDS_Security_Access")

    def test_routine_control(self, uds_setup):
        """
        Scenario: Tester requests Routine Control (0x31) to start a test.
        Expected: Gateway executes routine.
        """
        sim, _ = uds_setup
        
        request = {'sid': 0x31, 'sub_fn': 0x01, 'did': 0x0100} # Start Wiper Test
        sim.bus.broadcast('UDS_REQUEST', request, sender='TestHarness')
        sim.step()
        
        logs = list(sim.bus.get_log())[-10:]
        response = next((l for l in logs if l['id'] == 'UDS_RESPONSE' and l['data']['sid'] == 0x71), None)
        
        assert response is not None
        assert response['data']['data'] == "STARTED"
        
        self.generate_report(sim, "UDS_Routine_Control")
