
import pytest
from virtual_vehicle.sim.engine import SimulationEngine
from virtual_vehicle.plants.vehicle_dynamics import VehicleDynamics
from virtual_vehicle.plants.radar_generator import RadarGenerator
from virtual_vehicle.ecus.adas_ecu import AdasECU
from virtual_vehicle.utilities.report_generator import ReportGenerator

class TestScenarios:
    @pytest.fixture
    def sim_setup(self):
        sim = SimulationEngine(time_step=0.1)
        vehicle = VehicleDynamics('VehicleDynamics', sim.bus)
        radar = RadarGenerator('RadarGen', sim.bus)
        adas = AdasECU('ADAS_ECU', sim.bus)

        sim.add_plant(vehicle)
        sim.add_plant(radar)
        sim.add_ecu(adas)

        return sim, vehicle, radar, adas

    def generate_report(self, sim, test_name):
        reporter = ReportGenerator()
        reporter.generate(test_name, sim.bus.get_log(), result="PASS") # Assuming pass if we get here

    def test_stationary_obstacle(self, sim_setup):
        sim, vehicle, radar, adas = sim_setup
        vehicle.state['v'] = 20.0
        radar.add_object(obj_id=1, dist=100.0, rel_speed=-20.0, lateral_pos=0.0)

        # Run simulation
        collision = False
        aeb_triggered = False

        for _ in range(60):
            sim.step()
            if adas.aeb_triggered:
                aeb_triggered = True
            if vehicle.state['v'] == 0:
                break

        assert aeb_triggered, "AEB should have triggered"
        assert vehicle.state['v'] == 0, "Vehicle should have stopped"
        assert radar.objects[0]['dist'] > 0, "Collision should have been avoided"

        self.generate_report(sim, "Stationary_Obstacle")

    def test_cut_in_scenario(self, sim_setup):
        sim, vehicle, radar, adas = sim_setup
        vehicle.state['v'] = 20.0

        # Object starts in adjacent lane (3m right), closing in
        # moving left (-1.0 m/s lateral speed)
        radar.add_object(obj_id=2, dist=60.0, rel_speed=-10.0, lateral_pos=3.0, lateral_speed=-1.0)

        aeb_trigger_time = None

        for i in range(50): # 5 seconds
            sim.step()

            # Check if AEB triggers
            if adas.aeb_triggered and aeb_trigger_time is None:
                aeb_trigger_time = i * 0.1
                print(f"AEB Triggered at {aeb_trigger_time}s")

        # Logic Analysis:
        # Lateral pos starts at 3.0. Speed -1.0.
        # It crosses 1.75m boundary at t = (3.0 - 1.75) / 1.0 = 1.25s.
        # So AEB should NOT be triggered before 1.25s.

        assert aeb_trigger_time is not None, "AEB should eventually trigger"
        assert aeb_trigger_time > 1.0, f"AEB triggered too early ({aeb_trigger_time}s) - Phantom Braking suspected"

        self.generate_report(sim, "Cut_In_Scenario")

    def test_moose_test_esc_activation(self):
        # Setup specific for Moose Test (needs ESC ECU)
        sim = SimulationEngine(time_step=0.05) # Higher fidelity
        vehicle = VehicleDynamics('VehicleDynamics', sim.bus)

        # Import dynamically to avoid circular imports in fixture if not needed
        from virtual_vehicle.ecus.esc_ecu import EscECU
        esc = EscECU('ESC_ECU', sim.bus)

        sim.add_plant(vehicle)
        sim.add_ecu(esc)

        # Initial Conditions: 80 km/h
        vehicle.state['v'] = 22.2

        esc_triggered = False
        max_yaw_rate = 0.0

        print("\n--- MOOSE TEST START ---")
        for i in range(40): # 2 seconds
            # Simulate rapid steering input (Sine wave)
            # t = 0 to 0.5s: Steer Left
            # t = 0.5 to 1.0s: Steer Right
            t = i * 0.05
            if t < 0.5:
                vehicle.steering_angle = 0.5 # rad (~28 deg)
            elif t < 1.0:
                vehicle.steering_angle = -0.5
            else:
                vehicle.steering_angle = 0.0

            sim.step()

            yaw_rate = vehicle.state['yaw_rate']
            if abs(yaw_rate) > max_yaw_rate:
                max_yaw_rate = abs(yaw_rate)

            if esc.esc_active:
                esc_triggered = True
                print(f"Time {t:.2f}s: ESC Active! Yaw Rate: {yaw_rate:.2f}")

        print(f"Max Yaw Rate: {max_yaw_rate:.2f}")

        assert esc_triggered, "ESC should have activated during severe maneuver"
        assert max_yaw_rate < 2.0, "Vehicle spun out! (Yaw rate too high)"

        # Manually instantiate reporter since sim_setup fixture is not used here
        reporter = ReportGenerator()
        reporter.generate("Moose_Test", sim.bus.get_log(), result="PASS")
