"""
Battery Management System (BMS) ECU logic.
"""
from virtual_vehicle.ecus.base_ecu import BaseECU

class BmsECU(BaseECU):
    """
    Battery Management System ECU.
    Responsible for safety monitoring (Voltage, Temperature) and contactor control.
    """
    def __init__(self, name, bus):
        super().__init__(name, bus)
        self.contactors_closed = False
        self.soc_estimate = 100.0
        self.max_temp_limit = 60.0 # deg C
        self.min_voltage_limit = 320.0 # V
        self.max_voltage_limit = 420.0 # V

    def receive_message(self, msg_id, data, sender):
        """Monitor battery telemetry and check for safety violations."""
        if msg_id == 'HV_VOLTAGE':
            self.check_voltage(data)
        elif msg_id == 'HV_TEMP':
            self.check_temp(data)
        elif msg_id == 'HV_CURRENT':
            pass # Use for precise SoC calcs in future

    def check_voltage(self, voltage):
        """Verify that current battery voltage is within safe operating limits."""
        if voltage < self.min_voltage_limit:
            print(f"BMS ALERT: Undervoltage ({voltage:.2f}V). Opening contactors.")
            self.open_contactors()
        elif voltage > self.max_voltage_limit:
            print(f"BMS ALERT: Overvoltage ({voltage:.2f}V). Opening contactors.")
            self.open_contactors()

    def check_temp(self, temp):
        """Verify that battery temperature is within safe operating limits."""
        if temp > self.max_temp_limit:
            print(f"BMS ALERT: Overheating ({temp:.2f}C). Opening contactors.")
            self.open_contactors()

    def open_contactors(self):
        """Disconnect the high voltage battery from the load."""
        self.contactors_closed = False
        self.bus.broadcast('CONTACTOR_STATE', False, sender=self.name)

    def close_contactors(self):
        """Connect the high voltage battery to the load."""
        self.contactors_closed = True
        self.bus.broadcast('CONTACTOR_STATE', True, sender=self.name)

    def step(self, dt):
        """Periodic logic to broadcast SoC estimate."""
        # Periodic tasks (e.g. balancing, SoC broadcast)
        self.bus.broadcast('BMS_SOC', self.soc_estimate, sender=self.name)
