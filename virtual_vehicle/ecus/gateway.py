"""
Gateway ECU for inter-network communication and security.
"""
from virtual_vehicle.ecus.base_ecu import BaseECU

class GatewayECU(BaseECU):
    """
    Central Gateway ECU.
    Handles Intrusion Detection (IDS), Secure OTA, OBD-II services, and V2X routing.
    """
    def __init__(self, name, bus):
        super().__init__(name, bus)
        self.ids_enabled = True
        self.current_version = "1.0"

    def receive_message(self, msg_id, data, sender):
        """Monitor bus traffic for security threats and handle special requests."""
        if self.ids_enabled:
            self.detect_intrusion(msg_id, data, sender)

    def detect_intrusion(self, msg_id, data, sender):
        """Check message origin and handle core gateway services."""
        # OTA Handling
        if msg_id == 'OTA_UPDATE':
            self.handle_ota_update(data)
            return

        # OBD Handling (Virtual OBD Port)
        if msg_id == 'OBD_REQUEST':
            self.handle_obd_request(data)
            return

        # V2X Handling
        if msg_id == 'V2X_RX':
            self.handle_v2x_message(data)
            return

        # Simple rule: Only known ECUs can send control commands
        allowed_senders = ['ADAS_ECU', 'BMS_ECU', 'VehicleDynamics', 'TestHarness', 'V2XRadio']

        if 'CMD' in msg_id and sender not in allowed_senders:
            print(f"SECURITY ALERT: Unauthorized sender {sender} for {msg_id}")
            self.bus.broadcast('SECURITY_ALERT', {
                'type': 'UNAUTHORIZED_ACCESS',
                'details': f"{sender}->{msg_id}"
            }, sender=self.name)

    def handle_obd_request(self, request):
        """Process Virtual OBD-II requests (Modes 01, 03, 09)."""
        mode = request.get('mode')
        pid = request.get('pid', 0x00)

        response = {'mode': mode + 0x40, 'pid': pid, 'data': None}

        if mode == 0x01: # Show Current Data
            if pid == 0x01: # Monitor Status (Readiness)
                response['data'] = 0x00
            elif pid == 0x0C: # Engine RPM (Simulated)
                response['data'] = 3000
        elif mode == 0x03: # Show DTCs
            response['data'] = ['P0123']
        elif mode == 0x09: # Vehicle Info
            if pid == 0x02: # VIN
                response['data'] = "1FA-VIRTUAL-CAR-001"

        self.bus.broadcast('OBD_RESPONSE', response, sender=self.name)

    def handle_v2x_message(self, bsm):
        """Process incoming V2X Basic Safety Messages (BSM)."""
        # Simplified Intersection Movement Assist (IMA)
        if bsm.get('id') == 'RemoteVehicle_1' and bsm.get('speed') > 10.0:
            print(f"V2X WARNING: Collision Risk with {bsm['id']}!")
            self.bus.broadcast('HMI_WARNING', 'INTERSECTION_COLLISION_RISK', sender=self.name)

    def handle_ota_update(self, payload):
        """Execute Flash-Over-The-Air (FOTA) procedure with signature verification."""
        print(f"GATEWAY: Received OTA Update v{payload.get('version')}")

        # 1. Verify Signature
        if payload.get('signature') != 'valid_sig':
            print("GATEWAY: OTA Signature Verification FAILED! Rejecting.")
            self.bus.broadcast('OTA_STATUS', 'FAILED_SIG_VERIFY', sender=self.name)
            return

        # 2. Simulate Flashing (A/B Partition)
        print("GATEWAY: Signature Verified. Flashing to Partition B...")
        try:
            if payload.get('binary') == 'corrupt_chunk':
                raise IOError("Flash Write Error")

            self.current_version = payload.get('version')
            print(f"GATEWAY: Update Complete. Rebooting into v{self.current_version}")
            self.bus.broadcast('OTA_STATUS', 'SUCCESS', sender=self.name)

        except IOError:
            print("GATEWAY: Flash Failed! Rolling back to previous version.")
            self.rollback()

    def rollback(self):
        """Restore previous system version upon flash failure."""
        print("GATEWAY: Rollback successful. System restored.")
        self.bus.broadcast('OTA_STATUS', 'ROLLBACK_COMPLETE', sender=self.name)

    def step(self, dt):
        """Periodic logic update."""
        pass
