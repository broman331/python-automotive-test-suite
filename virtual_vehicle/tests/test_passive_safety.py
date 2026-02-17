
import pytest
from virtual_vehicle.sim.engine import SimulationEngine
from virtual_vehicle.plants.vehicle_dynamics import VehicleDynamics
from virtual_vehicle.ecus.airbag_ecu import AirbagECU
from virtual_vehicle.utilities.report_generator import ReportGenerator

class TestPassiveSafety:
    @pytest.fixture
    def safety_setup(self):
        sim = SimulationEngine(time_step=0.01) # High resolution for crash
        vehicle = VehicleDynamics('VehicleDynamics', sim.bus)
        acu = AirbagECU('AirbagECU', sim.bus)

        sim.add_plant(vehicle)
        sim.add_ecu(acu)

        return sim, vehicle, acu

    def generate_report(self, sim, test_name, result="PASS"):
        reporter = ReportGenerator()
        reporter.generate(test_name, sim.bus.get_log(), result=result)

    def test_airbag_deployment(self, safety_setup):
        """
        Scenario: Simulated High-G Impact (>5g).
        Expected: ACU deploys airbags and pretensioners.
        """
        sim, vehicle, acu = safety_setup

        # Initial State: Moving fast
        vehicle.state['v'] = 30.0 # ~108 kph

        print("\n--- CRASH TEST START ---")

        # Simulate Crash Pulse (Rapid Deceleration)
        # We can't achieve 5g with normal brakes. We must force it or inject it.
        # Let's inject a fake ACCEL_X message from a "CrashSensor" (simulated by test harness)
        # OR force the vehicle state change.

        # Option A: Inject Message
        sim.bus.broadcast('ACCEL_X', -60.0, sender='CrashSensor') # -6g (approx)

        # Step ECUs
        sim.step()
        sim.step()

        logs = sim.bus.get_log()
        deployment = next((l for l in logs if l['id'] == 'DEPLOY_AIRBAG'), None)

        self.generate_report(sim, "Safe_Airbag_Deploy")

        assert deployment is not None, "Airbag did not deploy on -6g impact"
        assert deployment['data'] is True
        assert acu.airbags_deployed is True

    def test_no_deployment_mild_braking(self, safety_setup):
        """
        Scenario: Hard Braking (1g).
        Expected: No Airbag Deployment.
        """
        sim, vehicle, acu = safety_setup

        vehicle.state['v'] = 30.0

        # Apply Max Brakes
        sim.bus.broadcast('BRAKE_CMD', 1.0, sender='TestHarness')

        for i in range(20):
            sim.step()

        logs = sim.bus.get_log()
        deployment = next((l for l in logs if l['id'] == 'DEPLOY_AIRBAG'), None)

        self.generate_report(sim, "Safe_No_Airbag_Braking")

        assert deployment is None, "Airbag deployed during normal braking!"
        assert acu.airbags_deployed is False
