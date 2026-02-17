
import collections

class VirtualBus:
    """
    Simulates a vehicle network (CAN/Ethernet) for message broadcasting.
    """
    def __init__(self):
        self.nodes = []
        self.message_log = collections.deque(maxlen=1000)
        self.fault_injector = None

    def register(self, node):
        """Register a node (ECU or Plant) to the bus."""
        self.nodes.append(node)
        print(f"Node registered: {node.name}")

    def set_fault_injector(self, injector):
        """Attach a FaultInjector to the bus."""
        self.fault_injector = injector

    def broadcast(self, msg_id, data, sender):
        """Broadcasts a message to all registered nodes except the sender."""
        # Fault Injection Hook
        if hasattr(self, 'fault_injector') and self.fault_injector:
            msg_id, data, drop = self.fault_injector.process(msg_id, data, sender)
            if drop:
                return

        self.message_log.append({'id': msg_id, 'data': data, 'sender': sender})
        for node in self.nodes:
            if node.name != sender:
                node.receive_message(msg_id, data, sender)

    def get_log(self):
        return list(self.message_log)
