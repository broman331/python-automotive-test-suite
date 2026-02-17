
class FaultInjector:
    def __init__(self):
        self.active_faults = []

    def inject(self, fault_type, target_id=None, duration=0):
        """
        fault_type: 'DROP', 'CORRUPT', 'DELAY'
        target_id: Message ID to target
        """
        self.active_faults.append({'type': fault_type, 'target': target_id, 'duration': duration})
        print(f"INJECTING FAULT: {fault_type} on {target_id}")

    def process(self, msg_id, data, sender):
        drop = False
        for fault in self.active_faults:
            if fault['target'] == msg_id or fault['target'] == 'ALL':
                if fault['type'] == 'DROP':
                    drop = True
                    print(f"FAULT: Dropped message {msg_id}")
                elif fault['type'] == 'CORRUPT':
                    data = "CORRUPTED_DATA"
                    print(f"FAULT: Corrupted message {msg_id}")
        return msg_id, data, drop
