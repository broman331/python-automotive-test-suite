"""
Test Suite for EV Charging (CCS / ISO 15118).
"""
import pytest
from virtual_vehicle.sim.engine import SimulationEngine
from virtual_vehicle.plants.battery import BatteryPlant
from virtual_vehicle.plants.charging_station import ChargingStation
from virtual_vehicle.ecus.bms import BmsECU
from virtual_vehicle.utilities.report_generator import ReportGenerator

class TestCharging:
    """Test cases for DC Fast Charging."""
    
    @pytest.fixture
    def charging_setup(self):
        sim = SimulationEngine(time_step=0.1)
        battery = BatteryPlant('BatteryPlant', sim.bus)
        charger = ChargingStation('DC_Charger', sim.bus)
        bms = BmsECU('BMS_ECU', sim.bus)
        
        sim.add_plant(battery)
        sim.add_plant(charger)
        sim.add_ecu(bms)
        
        return sim, bms, charger, battery

    def generate_report(self, sim, test_name, result="PASS"):
        reporter = ReportGenerator()
        reporter.generate(test_name, list(sim.bus.get_log()), result=result)

    def test_plug_in_and_handshake(self, charging_setup):
        """
        Scenario: Driver plugs in charger.
        Expected: BMS detects connection, closes contactors, and enters Handshake.
        """
        sim, bms, charger, _ = charging_setup
        
        # Ensure SoC is below target to trigger charge
        bms.soc_estimate = 50.0

        # 1. Start Simulation
        sim.step()
        assert bms.charging_state == 'IDLE'
        
        # 2. Plug in Cable
        charger.connect_cable()
        sim.step()
        sim.step()
        
        # 3. Verify Handshake
        assert bms.charging_state == 'HANDSHAKE' or bms.charging_state == 'CHARGING'
        assert bms.contactors_closed == True
        
        self.generate_report(sim, "Charging_Handshake")

    def test_charging_session(self, charging_setup):
        """
        Scenario: Normal Charging Session (SoC < Target).
        Expected: Charger outputs voltage/current requested by BMS.
        """
        sim, bms, charger, battery = charging_setup
        
        bms.soc_estimate = 50.0 # Force low SoC
        
        # 1. Plug in
        charger.connect_cable()
        for _ in range(5):
            sim.step()
            
        # 2. Verify Charging Status
        assert bms.charging_state == 'CHARGING'
        assert charger.state == 'CHARGING'
        assert charger.voltage_supply > 300.0
        assert charger.current_supply > 0.0
        
        self.generate_report(sim, "Charging_Session")
        
    def test_charging_stop_soc_limit(self, charging_setup):
        """
        Scenario: Battery reaches target SoC.
        Expected: BMS stops charging and opens contactors.
        """
        sim, bms, charger, _ = charging_setup
        
        bms.soc_estimate = 89.0 # Near target (90%)
        bms.target_soc = 90.0
        
        charger.connect_cable()
        
        # Simulating charging...
        charging_active = False
        stopped = False
        
        for _ in range(20):
            sim.step()
            if bms.charging_state == 'CHARGING':
                charging_active = True
                # Artificially increase SoC to simulate fast charging
                bms.soc_estimate += 0.2 
            
            if charging_active and bms.charging_state == 'IDLE':
                stopped = True
                break
                
        assert charging_active, "Did not enter charging state"
        assert stopped, "Did not stop charging when SoC limit reached"
        assert bms.contactors_closed == False
        
        self.generate_report(sim, "Charging_Stop_Limit")
