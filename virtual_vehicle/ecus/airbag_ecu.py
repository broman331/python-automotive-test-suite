
from virtual_vehicle.ecus.base_ecu import BaseECU
import time

class AirbagECU(BaseECU):
    """
    Airbag Control Unit (ACU).
    Monitors acceleration and deploys airbags/pretensioners during a crash.
    """
    def __init__(self, name, bus):
        super().__init__(name, bus)
        self.crash_threshold_g = -5.0 # 5g deceleration
        self.airbags_deployed = False
        self.pretensioners_deployed = False
        self.deployment_time = None

    def receive_message(self, msg_id, data, sender):
        if msg_id == 'ACCEL_X':
            # Data is in m/s^2. Convert to G.
            accel_g = data / 9.81
            self.check_crash(accel_g)

    def check_crash(self, accel_g):
        if accel_g < self.crash_threshold_g and not self.airbags_deployed:
            self.deploy_safety_systems()

    def deploy_safety_systems(self):
        print(f"ACU: CRASH DETECTED! Deploying Safety Systems at {time.time()}")
        self.airbags_deployed = True
        self.pretensioners_deployed = True
        self.deployment_time = time.time()

        # Broadcast Critical Safety Messages
        self.bus.broadcast('DEPLOY_AIRBAG', True, sender=self.name)
        self.bus.broadcast('DEPLOY_SEATBELT', True, sender=self.name)
        self.bus.broadcast('POST_CRASH_ALERT', {'loc': 'GPS_DATA_HERE'}, sender=self.name)

    def step(self, dt):
        pass
