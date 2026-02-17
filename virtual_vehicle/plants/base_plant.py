
class BasePlant:
    def __init__(self, name, bus):
        self.name = name
        self.bus = bus
        self.bus.register(self)
        self.state = {}

    def receive_message(self, msg_id, data, sender):
        """Callback for receiving messages. Override in subclasses."""
        pass

    def update_physics(self, dt):
        """Update the physical state of the plant. Override in subclasses."""
        pass

    def publish_sensor_data(self):
        """Publish sensor readings to the bus. Override in subclasses."""
        pass
