"""
Core Simulation Engine.
"""
import time
from virtual_vehicle.sim.bus import VirtualBus

class SimulationEngine:
    """
    Manages the simulation clock, plants, and ECUs.
    """
    def __init__(self, time_step=0.01):
        self.dt = time_step
        self.bus = VirtualBus()
        self.ecus = []
        self.plants = []
        self.running = False

    def add_ecu(self, ecu):
        """Add an ECU to the simulation."""
        self.ecus.append(ecu)

    def add_plant(self, plant):
        """Add a Plant model to the simulation."""
        self.plants.append(plant)

    def step(self):
        """Advance the simulation by one time step."""
        # 1. Update Physics (Plants)
        for plant in self.plants:
            plant.update_physics(self.dt)
            plant.publish_sensor_data()

        # 2. Update Logic (ECUs)
        for ecu in self.ecus:
            # ECUs read messages via callbacks (already handled by bus broadcast)
            ecu.step(self.dt)

    def run(self, duration):
        """Run the simulation for a specific duration in seconds."""
        self.running = True
        steps = int(duration / self.dt)
        print(f"Starting simulation for {duration}s ({steps} steps)...")

        for i in range(steps):
            if not self.running:
                break
            self.step()
            # Optional: Real-time pacing could be added here
            # time.sleep(self.dt)

        print("Simulation complete.")

    def stop(self):
        self.running = False
