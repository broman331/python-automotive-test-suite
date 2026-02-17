"""
Plant model for High Voltage Battery.
"""
from virtual_vehicle.plants.base_plant import BasePlant

class BatteryPlant(BasePlant):
    """
    Simulates a high voltage battery pack including SoC, voltage sag, and thermals.
    """
    def __init__(self, name, bus, capacity_kwh=60):
        super().__init__(name, bus)
        self.capacity_kwh = capacity_kwh
        self.current_capacity = capacity_kwh
        self.voltage = 400.0  # Nominal
        self.current = 0.0
        self.temperature = 25.0
        self.internal_resistance = 0.05

        # Environmental / Fault Injection
        self.ambient_temp = 25.0
        self.drift_voltage = 0.0
        self.drift_current = 0.0
        self.drift_temp = 0.0

    def receive_message(self, msg_id, data, sender):
        """Process incoming current demands and environmental conditions."""
        if msg_id == 'LOAD_CURRENT':
            self.current = data
        elif msg_id == 'SET_ENV_THERMAL':
            self.ambient_temp = data.get('ambient_temp', 25.0)
        elif msg_id == 'SET_SENSOR_DRIFT':
            self.drift_voltage = data.get('voltage', 0.0)
            self.drift_current = data.get('current', 0.0)
            self.drift_temp = data.get('temp', 0.0)

    def update_physics(self, dt):
        """Update SoC, voltage sag, and thermal state."""
        # SoC Calculation (Coulomb Counting)
        # Power = V * I. Energy = Power * time.
        # Simplified: Capacity is degraded by current draw.
        # Note: Positive current = discharge
        energy_change_kwh = (self.voltage * self.current * dt) / (1000 * 3600)
        self.current_capacity -= energy_change_kwh

        # Simple thermal model (I^2 * R heating + Cooling)
        heat_gen = (self.current ** 2) * self.internal_resistance
        cooling = (self.temperature - self.ambient_temp) * 0.1 # Dynamic Ambient cooling/heating
        temp_change = (heat_gen - cooling) * dt * 0.01 # Arbitrary thermal mass
        self.temperature += temp_change

        # Voltage sag under load
        self.voltage = 400.0 - (self.current * self.internal_resistance)

    def publish_sensor_data(self):
        """Publish battery telemetry to the virtual bus."""
        self.bus.broadcast('HV_VOLTAGE', self.voltage + self.drift_voltage, sender=self.name)
        self.bus.broadcast('HV_CURRENT', self.current + self.drift_current, sender=self.name)
        self.bus.broadcast('HV_TEMP', self.temperature + self.drift_temp, sender=self.name)
