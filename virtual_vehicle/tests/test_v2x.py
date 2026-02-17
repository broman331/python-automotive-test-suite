
import pytest
from virtual_vehicle.sim.engine import SimulationEngine
from virtual_vehicle.plants.v2x_radio import V2XRadio
from virtual_vehicle.ecus.gateway import GatewayECU
from virtual_vehicle.utilities.report_generator import ReportGenerator

class TestV2X:
    @pytest.fixture
    def v2x_setup(self):
        sim = SimulationEngine(time_step=0.1)
        radio = V2XRadio('V2XRadio', sim.bus)
        gateway = GatewayECU('Gateway', sim.bus)
        sim.add_plant(radio)
        sim.add_ecu(gateway)
        return sim, radio, gateway

    def generate_report(self, sim, test_name, result="PASS"):
        reporter = ReportGenerator()
        reporter.generate(test_name, sim.bus.get_log(), result=result)

    def test_bsm_broadcast(self, v2x_setup):
        """
        Scenario: Radio should broadcast BSM at 10Hz.
        """
        sim, radio, gateway = v2x_setup

        # Run for 0.5s -> 5 BSMs
        print("\n--- V2X BSM TEST START ---")
        for i in range(5):
            sim.step()

        logs = sim.bus.get_log()
        bsm_count = sum(1 for l in logs if l['id'] == 'V2X_RX' and l['sender'] == 'V2XRadio')

        self.generate_report(sim, "V2X_BSM_Running")

        assert bsm_count >= 4, f"Expected ~5 BSMs, got {bsm_count}"

    def test_ima_warning(self, v2x_setup):
        """
        Scenario: Remote vehicle broadcasts BSM indicating collision course.
        Expected: Gateway issues HMI Warning.
        """
        sim, radio, gateway = v2x_setup

        # Inject Fake V2X Message from "RemoteVehicle_1"
        fake_bsm = {
            'msg_type': 'BSM',
            'id': 'RemoteVehicle_1',
            'speed': 15.0, # Fast approach
            'lat': 37.7749,
            'lon': -122.4194
        }
        sim.bus.broadcast('V2X_RX', fake_bsm, sender='RemoteVehicle_1')

        sim.step()

        logs = sim.bus.get_log()
        warning = next((l for l in logs if l['id'] == 'HMI_WARNING'), None)

        self.generate_report(sim, "V2X_IMA_Warning")

        assert warning is not None, "Gateway did not issue HMI Warning for V2X threat"
        assert warning['data'] == 'INTERSECTION_COLLISION_RISK'
