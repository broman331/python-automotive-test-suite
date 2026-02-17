
import pytest
from virtual_vehicle.sim.engine import SimulationEngine
from virtual_vehicle.plants.vehicle_dynamics import VehicleDynamics
from virtual_vehicle.plants.battery import BatteryPlant
from virtual_vehicle.utilities.drive_cycle import DriveCycle, DriverModel
from virtual_vehicle.utilities.report_generator import ReportGenerator

class TestEfficiency:
    @pytest.fixture
    def eff_setup(self):
        sim = SimulationEngine(time_step=0.1)
        vehicle = VehicleDynamics('VehicleDynamics', sim.bus)
        battery = BatteryPlant('HvBattery', sim.bus)
        sim.add_plant(vehicle)
        sim.add_plant(battery)
        return sim, vehicle, battery

    def generate_report(self, sim, test_name, result="PASS"):
        reporter = ReportGenerator()
        reporter.generate(test_name, sim.bus.get_log(), result=result)

    def test_wltp_cycle(self, eff_setup):
        """
        Scenario: Run Micro-WLTP cycle.
        Expected: Follow speed profile, calculate energy consumption.
        """
        sim, vehicle, battery = eff_setup
        cycle = DriveCycle()
        driver = DriverModel(sim.bus)

        total_energy_kwh = 0.0
        total_dist_km = 0.0

        print("\n--- WLTP EFFICIENCY TEST START ---")

        # Run Cycle (60s)
        duration = 60
        steps = int(duration / 0.1)

        for i in range(steps):
            t = i * 0.1
            target_v = cycle.get_target_speed(t)
            current_v = vehicle.state['v']

            # Driver Control
            driver.step(target_v, current_v, 0.1)

            # Step Sim
            sim.step()

            # Accumulate Metrics
            # Energy (Power * dt). Power = V * I.
            # Battery current is positive for discharge.
            # Voltage ~400V. Current ~Amps.
            if hasattr(battery, 'current') and getattr(battery, 'current') > 0:
                 # Only count discharge or regeneration? Net energy.
                 p_kw = (battery.voltage * battery.current) / 1000.0
                 e_kwh = (p_kw * 0.1) / 3600.0
                 total_energy_kwh += e_kwh

            dist_km = (current_v * 0.1) / 1000.0
            total_dist_km += dist_km

            if i % 100 == 0:
                print(f"T={t:.1f}s | Tgt={target_v:.1f}m/s | Act={current_v:.1f}m/s | Energy={total_energy_kwh:.6f}kWh")

        consumption = (total_energy_kwh / total_dist_km) * 100.0 if total_dist_km > 0 else 0

        print(f"\nTotal Distance: {total_dist_km:.3f} km")
        print(f"Total Energy: {total_energy_kwh:.6f} kWh")
        print(f"Consumption: {consumption:.2f} kWh/100km")

        self.generate_report(sim, "Eff_WLTP_Cycle")

        assert total_dist_km > 0.4, f"Vehicle didn't move enough ({total_dist_km:.3f}km)"
        assert consumption > 10.0 and consumption < 30.0, f"Unrealistic consumption: {consumption:.2f} kWh/100km"
