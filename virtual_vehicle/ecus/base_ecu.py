
class BaseECU:
    def __init__(self, name, bus):
        self.name = name
        self.bus = bus
        self.bus.register(self)

    def send_message(self, msg_id, data):
        """Sends a message to the bus."""
        self.bus.broadcast(msg_id, data, sender=self.name)

    def receive_message(self, msg_id, data, sender):
        """Callback for receiving messages. Override in subclasses."""
        pass

    def step(self, dt):
        """Execute one time step of logic. Override in subclasses."""
        pass
