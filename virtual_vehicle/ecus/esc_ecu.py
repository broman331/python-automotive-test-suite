
from virtual_vehicle.ecus.base_ecu import BaseECU

class EscECU(BaseECU):
    def __init__(self, name, bus):
        super().__init__(name, bus)
        self.esc_active = False

    def receive_message(self, msg_id, data, sender):
        if msg_id == 'YAW_RATE':
            self.check_stability(data)

    def check_stability(self, yaw_rate):
        # Simply threshold logic for now
        # In real ESC, we compare yaw_rate vs steering_angle model
        if abs(yaw_rate) > 0.5: # rad/s (~28 deg/s)
            if not self.esc_active:
                print(f"ESC ACTIVATED: High Yaw Rate ({yaw_rate:.2f} rad/s)")
                self.activate_esc()
        else:
            if self.esc_active:
                self.deactivate_esc()

    def activate_esc(self):
        self.esc_active = True
        self.bus.broadcast('ESC_STATUS', 'ACTIVE', sender=self.name)
        # In a real system, we would send individual brake commands here
        self.bus.broadcast('BRAKE_CMD', 0.8, sender=self.name) # Apply strong braking to stabilize

    def deactivate_esc(self):
        self.esc_active = False
        self.bus.broadcast('ESC_STATUS', 'INACTIVE', sender=self.name)
        self.bus.broadcast('BRAKE_CMD', 0.0, sender=self.name)

    def step(self, dt):
        pass
