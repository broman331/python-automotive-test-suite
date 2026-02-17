
from virtual_vehicle.ecus.base_ecu import BaseECU

class BmsECU(BaseECU):
    def __init__(self, name, bus):
        super().__init__(name, bus)
        self.contactors_closed = False
        self.soc_estimate = 100.0
        self.max_temp_limit = 60.0 # deg C
        self.min_voltage_limit = 320.0 # V
        self.max_voltage_limit = 420.0 # V

    def receive_message(self, msg_id, data, sender):
        if msg_id == 'HV_VOLTAGE':
            self.check_voltage(data)
        elif msg_id == 'HV_TEMP':
            self.check_temp(data)
        elif msg_id == 'HV_CURRENT':
            pass # Use for precise SoC calcs in future

    def check_voltage(self, voltage):
        if voltage < self.min_voltage_limit:
            print(f"BMS ALERT: Undervoltage ({voltage:.2f}V). Opening contactors.")
            self.open_contactors()
        elif voltage > self.max_voltage_limit:
            print(f"BMS ALERT: Overvoltage ({voltage:.2f}V). Opening contactors.")
            self.open_contactors()

    def check_temp(self, temp):
        if temp > self.max_temp_limit:
            print(f"BMS ALERT: Overheating ({temp:.2f}C). Opening contactors.")
            self.open_contactors()
    
    def open_contactors(self):
        self.contactors_closed = False
        self.bus.broadcast('CONTACTOR_STATE', False, sender=self.name)

    def close_contactors(self):
        self.contactors_closed = True
        self.bus.broadcast('CONTACTOR_STATE', True, sender=self.name)

    def step(self, dt):
        # Periodic tasks (e.g. balancing, SoC broadcast)
        self.bus.broadcast('BMS_SOC', self.soc_estimate, sender=self.name)
