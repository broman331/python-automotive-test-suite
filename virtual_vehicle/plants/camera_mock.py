
from virtual_vehicle.plants.base_plant import BasePlant
import math
import random

class CameraPlant(BasePlant):
    def __init__(self, name, bus):
        super().__init__(name, bus)
        # Lane Geometry (Synthetic)
        self.lane_width = 3.5
        self.offset_from_center = 0.0
        self.heading_error = 0.0 # Angle relative to lane
        self.curvature = 0.0
        self.noise_level = 0.0 # 0.0 to 1.0 (1.0 = Total Occlusion)

    def update_physics(self, dt):
        # We need to know vehicle lateral motion to update offset
        # But for now, we'll let the vehicle dynamics "drive" this state 
        # via a message or shared state if possible.
        # Ideally, Camera should just read vehicle state and transform to lane coordinates.
        pass

    def receive_message(self, msg_id, data, sender):
        if msg_id == 'GPS_POS':
            # Simplified: Assume straight road along X-axis at Y=0
            # Offset = Y
            self.offset_from_center = data['y']
        elif msg_id == 'YAW':
            # Simplified: Lane heading is 0.0
            self.heading_error = data
        elif msg_id == 'SET_ENV_VISIBILITY':
            # 1.0 = Clear, 0.0 = Blind
            # Map visibility to noise level (inverse)
            self.noise_level = 1.0 - data

    def publish_sensor_data(self):
        # Publish Lane Info
        # confidence: 0.0 - 1.0 (simulating visibility)
        confidence = max(0.0, 1.0 - self.noise_level)
        
        # Add noise to measurements if visibility is poor
        noisy_offset = self.offset_from_center + (random.uniform(-0.5, 0.5) * self.noise_level)
        
        data = {
            'lane_offset': noisy_offset, # +ve = left of center
            'heading_idx': self.heading_error,
            'curvature': self.curvature,
            'confidence': confidence
        }
        self.bus.broadcast('CAMERA_LANE', data, sender=self.name)
