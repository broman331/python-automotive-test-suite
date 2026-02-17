
from virtual_vehicle.ecus.base_ecu import BaseECU

class GatewayECU(BaseECU):
    def __init__(self, name, bus):
        super().__init__(name, bus)
        self.ids_enabled = True

    def receive_message(self, msg_id, data, sender):
        if self.ids_enabled:
            self.detect_intrusion(msg_id, data, sender)

    def detect_intrusion(self, msg_id, data, sender):
        # OTA Handling
        if msg_id == 'OTA_UPDATE':
            self.handle_ota_update(data)
            return

        # OBD Handling (Virtual OBD Port)
        if msg_id == 'OBD_REQUEST':
            self.handle_obd_request(data, sender)
            return

        # V2X Handling
        if msg_id == 'V2X_RX':
            self.handle_v2x_message(data)
            return

        # Simple rule: Only known ECUs can send control commands
        allowed_senders = ['ADAS_ECU', 'BMS_ECU', 'VehicleDynamics', 'TestHarness', 'V2XRadio']
        
        if 'CMD' in msg_id and sender not in allowed_senders:
            print(f"SECURITY ALERT: Unauthorized sender {sender} for {msg_id}")
            self.bus.broadcast('SECURITY_ALERT', {'type': 'UNAUTHORIZED_ACCESS', 'details': f"{sender}->{msg_id}"}, sender=self.name)

    def handle_obd_request(self, request, sender):
        """
        Request: {'mode': 0x01, 'pid': 0x00}
        """
        mode = request.get('mode')
        pid = request.get('pid', 0x00)
        
        response = {'mode': mode + 0x40, 'pid': pid, 'data': None}
        
        if mode == 0x01: # Show Current Data
            if pid == 0x01: # Monitor Status (Readiness)
                # Simulating "Everything Ready" (Mil off, 0 DTCs, Readiness complete)
                response['data'] = 0x00 
            elif pid == 0x0C: # Engine RPM (Simulated as Motor RPM)
                # Need to read from bus or cache. For now return mock.
                response['data'] = 3000 # rpm
                
        elif mode == 0x03: # Show DTCs
            # Simulate one stored DTC
            response['data'] = ['P0123']
            
        elif mode == 0x09: # Vehicle Info
            if pid == 0x02: # VIN
                response['data'] = "1FA-VIRTUAL-CAR-001"
                
        self.bus.broadcast('OBD_RESPONSE', response, sender=self.name)

    def handle_v2x_message(self, bsm):
        """
        Process V2X Basic Safety Messages.
        """
        # Simplified Intersection Movement Assist (IMA)
        # If another vehicle is close and moving fast -> Warn Driver
        # In a real system, we'd calculate Time-To-Collision based on trajectories.
        # Here, just check flag or proximity.
        
        # Threat detection simulation
        if bsm.get('id') == 'RemoteVehicle_1' and bsm.get('speed') > 10.0:
            print(f"V2X WARNING: Collision Risk with {bsm['id']}!")
            self.bus.broadcast('HMI_WARNING', 'INTERSECTION_COLLISION_RISK', sender=self.name)

    def handle_ota_update(self, payload):
        """
        Payload: {'version': '2.0', 'signature': 'valid_sig', 'binary': '...'}
        """
        print(f"GATEWAY: Received OTA Update v{payload.get('version')}")
        
        # 1. Verify Signature
        if payload.get('signature') != 'valid_sig':
            print("GATEWAY: OTA Signature Verification FAILED! Rejecting.")
            self.bus.broadcast('OTA_STATUS', 'FAILED_SIG_VERIFY', sender=self.name)
            return
        
        # 2. Simulate Flashing (A/B Partition)
        print("GATEWAY: Signature Verified. Flashing to Partition B...")
        try:
            # Simulate chance of flash failure
            if payload.get('binary') == 'corrupt_chunk':
                raise IOError("Flash Write Error")
            
            self.current_version = payload.get('version')
            print(f"GATEWAY: Update Complete. Rebooting into v{self.current_version}")
            self.bus.broadcast('OTA_STATUS', 'SUCCESS', sender=self.name)
            
        except IOError:
            print("GATEWAY: Flash Failed! Rolling back to previous version.")
            self.rollback()

    def rollback(self):
        # Simulate rollback
        print("GATEWAY: Rollback successful. System restored.")
        self.bus.broadcast('OTA_STATUS', 'ROLLBACK_COMPLETE', sender=self.name)

    def step(self, dt):
        pass
