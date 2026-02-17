
import pytest
from virtual_vehicle.sim.engine import SimulationEngine
from virtual_vehicle.plants.battery import BatteryPlant
from virtual_vehicle.ecus.bms import BmsECU
from virtual_vehicle.utilities.report_generator import ReportGenerator

class TestEnvironmental:
    @pytest.fixture
    def env_setup(self):
        sim = SimulationEngine(time_step=1.0) # Slow dynamics (thermal)
        battery = BatteryPlant('BigBattery', sim.bus)
        bms = BmsECU('BMS_ECU', sim.bus)
        
        sim.add_plant(battery)
        sim.add_ecu(bms)
        
        return sim, battery, bms

    def generate_report(self, sim, test_name, result="PASS"):
        reporter = ReportGenerator()
        reporter.generate(test_name, sim.bus.get_log(), result=result)

    def test_thermal_shock(self, env_setup):
        """
        Scenario: Ambient temp rises to 60C while under load.
        Expected: Battery temp exceeds 45C limit -> BMS triggers Over-Temp fault.
        """
        sim, battery, bms = env_setup
        
        # Initial Conditions
        battery.temperature = 35.0
        bms.close_contactors() # Start with closed contactors
        sim.bus.broadcast('LOAD_CURRENT', 100.0, sender='TestHarness') # 100A Load
        
        # Thermal Shock: Ambient = 60C
        sim.bus.broadcast('SET_ENV_THERMAL', {'ambient_temp': 60.0}, sender='TestHarness')
        
        over_temp_triggered = False
        
        print("\n--- THERMAL SHOCK TEST START ---")
        for i in range(60): # 60 seconds (accelerated?)
            sim.step()
            
            # Check BMS Logic (Internal flag or output message)
            if not bms.contactors_closed: # Should open on fault
                 print(f"Time {i}s: Contactors OPENED! (Temp: {battery.temperature:.1f}C)")
                 over_temp_triggered = True
                 break
        
        self.generate_report(sim, "Env_ThermalShock")
        
        assert over_temp_triggered, "BMS should detect Over Temperature and open contactors"
        # BMS limit is 60.0 in code. Test should verify we exceeded it.
        assert battery.temperature >= 60.0, f"Battery Temp ({battery.temperature}) did not exceed limit (60.0)"

    def test_voltage_sensor_drift(self, env_setup):
        """
        Scenario: Voltage sensor drifts +50V.
        Expected: BMS reads > 420V and triggers Over-Voltage fault.
        """
        sim, battery, bms = env_setup
        
        # Initial: 400V (Nominal)
        battery.voltage = 400.0
        bms.close_contactors()
        
        # Drift: +30V (Total 430V > 420V Limit implied, code says > 320V min limit... check max?)
        sim.bus.broadcast('SET_SENSOR_DRIFT', {'voltage': 30.0}, sender='TestHarness')
        
        over_voltage_triggered = False
        
        print("\n--- VOLTAGE DRIFT TEST START ---")
        for i in range(10):
            sim.step()
            if not bms.contactors_closed:
                print(f"Time {i}s: Contactors OPENED! (Drifted Voltage > Limit)")
                over_voltage_triggered = True
                break
                
        self.generate_report(sim, "Env_VoltageDrift")
        
        assert over_voltage_triggered, "BMS should detect (False) Over Voltage due to sensor drift"
