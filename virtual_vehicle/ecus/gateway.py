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
        self.diagnostic_session = 0x01
        self.security_seed = 0x0000
        self.security_unlocked = False

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

        # UDS Handling
        if msg_id == 'UDS_REQUEST':
            self.handle_diagnostic_request(data, 'UDS')
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
        # ... (OBD Logic unchanged, can coexist)
        self.handle_diagnostic_request(request, 'OBD')

    def handle_diagnostic_request(self, request, protocol='OBD'):
        """Unified Diagnostic Handler."""
        if protocol == 'OBD':
            self._process_obd(request)
        elif protocol == 'UDS':
            self._process_uds(request)

    def _process_obd(self, request):
        mode = request.get('mode')
        pid = request.get('pid', 0x00)
        response = {'mode': mode + 0x40, 'pid': pid, 'data': None}

        if mode == 0x01: # Show Current Data
            if pid == 0x01: # Monitor Status
                response['data'] = 0x00
            elif pid == 0x0C: # Engine RPM
                response['data'] = 3000
        elif mode == 0x03: # Show DTCs
            response['data'] = ['P0123']
        elif mode == 0x09: # Vehicle Info
            if pid == 0x02: # VIN
                response['data'] = "1FA-VIRTUAL-CAR-001"

        self.bus.broadcast('OBD_RESPONSE', response, sender=self.name)

    def _process_uds(self, request):
        """
        Handle UDS (ISO 14229) Services.
        Request: {'sid': 0x10, 'sub_fn': 0x01, 'did': 0x1234, 'data': []}
        """
        sid = request.get('sid')
        sub_fn = request.get('sub_fn', 0x00)
        did = request.get('did', 0x0000)
        
        response = {'sid': sid + 0x40, 'sub_fn': sub_fn, 'data': None}
        nrc = None # Negative Response Code

        # Service 0x10: Diagnostic Session Control
        if sid == 0x10:
            if sub_fn in [0x01, 0x02, 0x03]: # Default, Programming, Extended
                self.diagnostic_session = sub_fn
                response['data'] = {'p2_server': 50, 'p2_star_server': 500}
            else:
                nrc = 0x12 # Sub-function not supported

        # Service 0x22: Read Data By Identifier
        elif sid == 0x22:
            if did == 0xF190: # VIN
                response['data'] = "1FA-VIRTUAL-CAR-001"
            elif did == 0x0200: # Battery Voltage (Mock)
                response['data'] = 400.5
            else:
                nrc = 0x31 # Request Limit Exceeded (or simply not found)

        # Service 0x27: Security Access
        elif sid == 0x27:
            if sub_fn == 0x01: # Request Seed
                self.security_seed = 0x1234
                response['data'] = self.security_seed
            elif sub_fn == 0x02: # Send Key
                key = request.get('data', [])
                # Simple algo: key = seed + 1
                if key == (self.security_seed + 1):
                    self.security_unlocked = True
                    response['data'] = "UNLOCKED"
                else:
                    nrc = 0x35 # Invalid Key

        # Service 0x31: Routine Control
        elif sid == 0x31:
            if sub_fn == 0x01: # Start Routine
                if did == 0x0100: # WIPER_TEST
                    print("GATEWAY: Executing Wiper Test Routine...")
                    response['data'] = "STARTED"
                else:
                    nrc = 0x31
            else:
                 nrc = 0x12

        else:
             nrc = 0x11 # Service Not Supported

        # Send Positive or Negative Response
        if nrc:
            err_resp = {'sid': 0x7F, 'request_sid': sid, 'nrc': nrc}
            self.bus.broadcast('UDS_RESPONSE', err_resp, sender=self.name)
        else:
            self.bus.broadcast('UDS_RESPONSE', response, sender=self.name)

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
