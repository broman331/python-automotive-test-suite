
import pytest
from virtual_vehicle.sim.engine import SimulationEngine
from virtual_vehicle.ecus.gateway import GatewayECU
from virtual_vehicle.utilities.report_generator import ReportGenerator

class TestCybersecurity:
    @pytest.fixture
    def ota_setup(self):
        sim = SimulationEngine(time_step=0.1)
        gateway = GatewayECU('Gateway', sim.bus)
        sim.add_ecu(gateway)
        return sim, gateway

    def generate_report(self, sim, test_name):
        reporter = ReportGenerator()
        reporter.generate(test_name, sim.bus.get_log(), result="PASS")

    def test_secure_ota_success(self, ota_setup):
        sim, gateway = ota_setup
        
        # Send valid update
        payload = {'version': '2.0', 'signature': 'valid_sig', 'binary': '101010'}
        sim.bus.broadcast('OTA_UPDATE', payload, sender='TestHarness')
        sim.step()
        
        # Check logs for SUCCESS
        logs = sim.bus.get_log()
        success = any(l['id'] == 'OTA_STATUS' and l['data'] == 'SUCCESS' for l in logs)
        
        self.generate_report(sim, "Sec_OTA_Success")
        assert success, "Valid OTA update should succeed"

    def test_ota_signature_fail(self, ota_setup):
        sim, gateway = ota_setup
        
        # Send invalid signature
        payload = {'version': '2.0', 'signature': 'evil_hacker', 'binary': 'rm -rf /'}
        sim.bus.broadcast('OTA_UPDATE', payload, sender='TestHarness')
        sim.step()
        
        logs = sim.bus.get_log()
        rejected = any(l['id'] == 'OTA_STATUS' and l['data'] == 'FAILED_SIG_VERIFY' for l in logs)
        
        self.generate_report(sim, "Sec_OTA_SigFail")
        assert rejected, "Invalid OTA signature should be rejected"

    def test_ota_rollback(self, ota_setup):
        sim, gateway = ota_setup
        
        # Send corrupted binary
        payload = {'version': '2.0', 'signature': 'valid_sig', 'binary': 'corrupt_chunk'}
        sim.bus.broadcast('OTA_UPDATE', payload, sender='TestHarness')
        sim.step()
        
        logs = sim.bus.get_log()
        rollback = any(l['id'] == 'OTA_STATUS' and l['data'] == 'ROLLBACK_COMPLETE' for l in logs)
        
        self.generate_report(sim, "Sec_OTA_Rollback")
        assert rollback, "Flash failure should trigger rollback"
