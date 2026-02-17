
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from virtual_vehicle.sim.engine import SimulationEngine
from virtual_vehicle.plants.vehicle_dynamics import VehicleDynamics
from virtual_vehicle.plants.battery import BatteryPlant
from virtual_vehicle.plants.radar_generator import RadarGenerator
from virtual_vehicle.ecus.bms import BmsECU
from virtual_vehicle.ecus.adas_ecu import AdasECU
from virtual_vehicle.ecus.gateway import GatewayECU
from virtual_vehicle.sim.fault_injector import FaultInjector

def run_integration_test():
    # 1. Setup Simulation
    sim = SimulationEngine(time_step=0.1)

    # 2. Add Plants
    vehicle = VehicleDynamics('VehicleDynamics', sim.bus)
    vehicle.state['v'] = 20.0 # Start at 20 m/s (72 km/h)

    battery = BatteryPlant('BatteryPlant', sim.bus)
    radar = RadarGenerator('RadarGen', sim.bus)

    sim.add_plant(vehicle)
    sim.add_plant(battery)
    sim.add_plant(radar)

    # 3. Add ECUs
    bms = BmsECU('BMS_ECU', sim.bus)
    adas = AdasECU('ADAS_ECU', sim.bus)
    gateway = GatewayECU('Gateway', sim.bus)

    sim.add_ecu(bms)
    sim.add_ecu(adas)
    sim.add_ecu(gateway)

    # 4. Setup Fault Injector (Optional)
    injector = FaultInjector()
    sim.bus.set_fault_injector(injector)

    # 5. Scenario: Stationary Obstacle
    # Object 100m away, we are approaching at 20m/s (rel_speed = -20)
    radar.add_object(obj_id=1, dist=100.0, rel_speed=-20.0)

    print("--- STARTING SCENARIO: APPROACHING OBSTACLE ---")

    # Run for 6 seconds (Impact would be at 5s without braking)
    # We expect AEB to trigger around 2.5s TTC (distance = 50m)

    for i in range(60):
        sim.step()

        # Log status
        current_v = vehicle.state['v']
        current_dist = radar.objects[0]['dist'] if radar.objects else -1

        print(f"Time: {i*0.1:.1f}s | Speed: {current_v:.2f} m/s | Obstacle Dist: {current_dist:.1f} m")

        if current_dist < 0 and current_dist > -100:
            print("!!! COLLISION !!!")
            break

        if current_v <= 0:
            print("--- VEHICLE STOPPED ---")
            break

if __name__ == "__main__":
    run_integration_test()
