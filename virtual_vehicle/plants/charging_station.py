"""
Charging Station Plant Model.
Simulates DC Fast Charging (CCS) interaction.
"""
from virtual_vehicle.plants.base_plant import BasePlant

class ChargingStation(BasePlant):
    """
    Simulates a DC Fast Charger (EVSE).
    Handles cable connection, state negotiation, and power delivery.
    """
    def __init__(self, name, bus):
        super().__init__(name, bus)
        self.connected = False
        self.state = 'DISCONNECTED' # DISCONNECTED, CONNECTED, CHARGING, ERROR
        self.voltage_supply = 0.0 # V
        self.current_supply = 0.0 # A
        self.max_power = 150000.0 # 150 kW

        # Subscribe to BMS Charging Requests
        bus.register(self)

    def receive_message(self, msg_id, data, sender):
        """Handle charging requests from BMS."""
        if msg_id == 'CHARGE_REQUEST':
            self.handle_charge_request(data)
        elif msg_id == 'CONTACTOR_STATE':
            if not data and self.state == 'CHARGING':
                # BMS opened contactors during charge -> Emergency Stop
                print("CHARGER: Contactors opened unexpectedly. Emergency Stop.")
                self.state = 'ERROR'
                self.stop_charging()

    def connect_cable(self):
        """Simulate plugin event."""
        self.connected = True
        self.state = 'CONNECTED'
        print("CHARGER: Cable Connected. Waiting for BMS...")
        self.bus.broadcast('CHARGER_STATUS', {'state': 'CONNECTED', 'max_power': self.max_power}, sender=self.name)

    def handle_charge_request(self, req):
        """
        Request: {'voltage_target': 400.0, 'current_target': 200.0, 'charging_enabled': True}
        """
        if not self.connected:
            return

        enabled = req.get('charging_enabled', False)
        
        if enabled:
            v_req = req.get('voltage_target', 0.0)
            i_req = req.get('current_target', 0.0)
            
            # Hardware Limits
            p_req = v_req * i_req
            if p_req > self.max_power:
                i_req = self.max_power / v_req
                print(f"CHARGER: Limiting power to {self.max_power/1000}kW")

            self.voltage_supply = v_req
            self.current_supply = i_req
            self.state = 'CHARGING'
            
            # Broadcast output to Battery Plant (simulated physical connection)
            self.bus.broadcast('CHARGER_OUTPUT', {'voltage': self.voltage_supply, 'current': self.current_supply}, sender=self.name)
        else:
            self.stop_charging()

    def stop_charging(self):
        self.voltage_supply = 0.0
        self.current_supply = 0.0
        if self.state != 'ERROR':
            self.state = 'CONNECTED'
        self.bus.broadcast('CHARGER_OUTPUT', {'voltage': 0.0, 'current': 0.0}, sender=self.name)

    def update_physics(self, dt):
        pass

    def publish_sensor_data(self):
        pass
