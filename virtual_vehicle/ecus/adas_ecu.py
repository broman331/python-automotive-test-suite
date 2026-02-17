
from virtual_vehicle.ecus.base_ecu import BaseECU

class AdasECU(BaseECU):
    def __init__(self, name, bus):
        super().__init__(name, bus)
        self.aeb_triggered = False
        self.ttc_threshold = 2.5 # seconds

    def receive_message(self, msg_id, data, sender):
        if msg_id == 'RADAR_OBJECTS':
            try:
                self.process_radar(data)
            except Exception as e:
                print(f"ADAS ERROR: Malformed Radar Data: {e}")
                self.release_aeb()
        elif msg_id == 'CAMERA_LANE':
            self.process_lane(data)

    def process_lane(self, lane_data):
        # LKA Logic (Simple P-Controller)
        confidence = lane_data.get('confidence', 1.0)
        
        # SOTIF / Safety Check: If confidence is low, disengage LKA
        if confidence < 0.6:
            print("ADAS: Lane Confidence Low. Disabling LKA.")
            return

        offset = lane_data['lane_offset']
        heading = lane_data.get('heading_idx', 0.0)
        
        # Control Law: Steer to zero out offset and heading error
        # steer = -Kp * offset - Kd * heading
        kp = 0.05 # Steer 0.05 rad per 1m offset
        kd = 1.5 # Steer 1.5 rad per 1 rad heading
        
        # Only active if enabled (speed > 60kph typically, but always on for test)
        steer_cmd = -(kp * offset + kd * heading)
        
        # Limit steering rate/max angle
        steer_cmd = max(-0.5, min(0.5, steer_cmd))
        
        self.bus.broadcast('STEERING_CMD', steer_cmd, sender=self.name)

    def process_radar(self, objects):
        if not isinstance(objects, list):
             raise ValueError("Data is not a list")
        
        min_ttc = float('inf')
        
        for obj in objects:
            dist = obj['dist']
            rel_speed = obj['rel_speed'] # m/s (negative = closing)
            lat_pos = obj.get('lat_pos', 0.0)

            # Filter out objects not in our lane (assuming lane width ~3.5m, so +/- 1.75m)
            if abs(lat_pos) > 1.75:
                continue

            if rel_speed < 0:
                ttc = -dist / rel_speed
                if ttc < min_ttc:
                    min_ttc = ttc
        
        if min_ttc < self.ttc_threshold:
            print(f"ADAS ALERT: TTC {min_ttc:.2f}s. Emergency Braking!")
            self.trigger_aeb()
        else:
            if self.aeb_triggered:
                self.release_aeb()

    def trigger_aeb(self):
        self.aeb_triggered = True
        self.bus.broadcast('BRAKE_CMD', 1.0, sender=self.name) # 100% braking

    def release_aeb(self):
        self.aeb_triggered = False
        self.bus.broadcast('BRAKE_CMD', 0.0, sender=self.name)

    def step(self, dt):
        pass
