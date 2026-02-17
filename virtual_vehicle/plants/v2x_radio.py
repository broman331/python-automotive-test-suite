
from virtual_vehicle.plants.base_plant import BasePlant
import random

class V2XRadio(BasePlant):
    """
    Simulates a V2X (Vehicle-to-Everything) Radio.
    Broadcasts Basic Safety Messages (BSM) containing vehicle state.
    """
    def __init__(self, name, bus):
        super().__init__(name, bus)
        self.bsm_interval = 0.1 # 10Hz
        self.time_since_last_bsm = 0.0
        self.vehicle_state = {
            'lat': 37.7749, 
            'lon': -122.4194,
            'speed': 0.0,
            'heading': 0.0
        }

    def update_physics(self, dt):
        """
        Update radio state and broadcast BSM if interval elapsed.
        """
        self.time_since_last_bsm += dt
        if self.time_since_last_bsm >= self.bsm_interval:
            self.broadcast_bsm()
            self.time_since_last_bsm = 0.0

    def receive_message(self, msg_id, data, sender):
        """
        Receive vehicle state updates from VehicleDynamics.
        """
        if msg_id == 'GPS_POS':
            # Simplified: Map X/Y to Lat/Lon
            self.vehicle_state['lat'] = 37.7749 + (data['y'] * 0.00001)
            self.vehicle_state['lon'] = -122.4194 + (data['x'] * 0.00001)
        elif msg_id == 'WHEEL_SPEED':
            self.vehicle_state['speed'] = data
        elif msg_id == 'YAW':
            self.vehicle_state['heading'] = data

    def broadcast_bsm(self):
        """
        Construct and broadcast a Basic Safety Message (BSM).
        """
        bsm = {
            'msg_type': 'BSM',
            'id': self.name,
            'sec_mark': int(self.time_since_last_bsm * 1000), # ms
            'lat': self.vehicle_state['lat'],
            'lon': self.vehicle_state['lon'],
            'speed': self.vehicle_state['speed'],
            'heading': self.vehicle_state['heading'],
            'accel_set': {'lon': 0.0, 'lat': 0.0, 'vert': 0.0, 'yaw': 0.0},
            'brakes': {'traction': 'off', 'abs': 'off', 'scs': 'off'}
        }
        self.bus.broadcast('V2X_RX', bsm, sender=self.name)
