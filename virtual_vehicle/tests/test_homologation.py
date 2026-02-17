
import pytest
from virtual_vehicle.sim.engine import SimulationEngine
from virtual_vehicle.ecus.gateway import GatewayECU
from virtual_vehicle.utilities.report_generator import ReportGenerator

class TestHomologation:
    @pytest.fixture
    def obd_setup(self):
        sim = SimulationEngine(time_step=0.1)
        gateway = GatewayECU('Gateway', sim.bus)
        sim.add_ecu(gateway)
        return sim, gateway

    def generate_report(self, sim, test_name, result="PASS"):
        reporter = ReportGenerator()
        reporter.generate(test_name, sim.bus.get_log(), result=result)

    def test_read_vin(self, obd_setup):
        """
        Scenario: Scan tool requests VIN (Mode 09, PID 02).
        Expected: Gateway responds with correct VIN.
        """
        sim, gateway = obd_setup
        
        # Send Request
        sim.bus.broadcast('OBD_REQUEST', {'mode': 0x09, 'pid': 0x02}, sender='ScanTool')
        sim.step()
        
        # Check Response
        logs = sim.bus.get_log()
        response = next((l['data'] for l in logs if l['id'] == 'OBD_RESPONSE'), None)
        
        self.generate_report(sim, "Homo_ReadVIN")
        
        assert response is not None, "Gateway did not respond to OBD request"
        assert response['data'] == "1FA-VIRTUAL-CAR-001", f"Incorrect VIN: {response['data']}"

    def test_read_dtc(self, obd_setup):
        """
        Scenario: Scan tool requests Stored DTCs (Mode 03).
        Expected: Gateway returns list of DTCs.
        """
        sim, gateway = obd_setup
        
        sim.bus.broadcast('OBD_REQUEST', {'mode': 0x03}, sender='ScanTool')
        sim.step()
        
        logs = sim.bus.get_log()
        response = next((l['data'] for l in logs if l['id'] == 'OBD_RESPONSE'), None)
        
        self.generate_report(sim, "Homo_ReadDTC")
        
        assert response is not None
        assert 'P0123' in response['data'], "Expected mock DTC P0123"

    def test_readiness_monitor(self, obd_setup):
        """
        Scenario: Check Monitor Status (Mode 01, PID 01).
        Expected: Returns 0x00 (All Ready).
        """
        sim, gateway = obd_setup
        
        sim.bus.broadcast('OBD_REQUEST', {'mode': 0x01, 'pid': 0x01}, sender='ScanTool')
        sim.step()
        
        logs = sim.bus.get_log()
        response = next((l['data'] for l in logs if l['id'] == 'OBD_RESPONSE'), None)
        
        self.generate_report(sim, "Homo_Readiness")
        
        assert response is not None
        assert response['data'] == 0x00, "Expected Readiness Status 0x00"
