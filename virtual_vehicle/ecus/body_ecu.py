from .base_ecu import BaseECU
import os
import json

class BodyECU(BaseECU):
    """
    Simulates a Body Control Module or Instrument Cluster.
    Manages Odometer and Trip meters.
    """
    def __init__(self, name, bus, storage_path="odometer_nvm.json"):
        super().__init__(name, bus)
        self.storage_path = storage_path
        self.total_mileage = 0.0 # meters
        self.trip_meter = 0.0 # meters
        self.dt = 0.05 # Initial guess
        
        # Load persistent data if exists
        self.load_from_nvm()

    def step(self, dt):
        """Update internal clock tracking."""
        self.dt = dt

    def receive_message(self, msg_id, data, sender):
        if msg_id == 'WHEEL_SPEED':
            # Distance = Speed * Time
            speed_mps = abs(float(data))
            
            increment = speed_mps * self.dt
            self.total_mileage += increment
            self.trip_meter += increment
            
        elif msg_id == 'RESET_TRIP':
            self.trip_meter = 0.0
            print(f"[{self.name}] Trip meter reset.")

    def update(self):
        """Broadcast odometer periodic data."""
        self.bus.broadcast('ODOMETER_DATA', {
            'total_km': self.total_mileage / 1000.0,
            'trip_km': self.trip_meter / 1000.0
        }, sender=self.name)

    def load_from_nvm(self):
        """Mock reading from Non-Volatile Memory."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    self.total_mileage = data.get('total_mileage', 0.0)
                    # Trip meter also often persists
                    self.trip_meter = data.get('trip_meter', 0.0)
            except Exception:
                pass

    def save_to_nvm(self):
        """Mock writing to Non-Volatile Memory."""
        with open(self.storage_path, 'w') as f:
            json.dump({
                'total_mileage': self.total_mileage,
                'trip_meter': self.trip_meter
            }, f)
