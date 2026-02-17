"""
Radar sensor simulation.
"""
from virtual_vehicle.plants.base_plant import BasePlant

class RadarGenerator(BasePlant):
    """
    Simulates a radar sensor that provides a list of detected objects with relative kinematics.
    """
    def __init__(self, name, bus):
        super().__init__(name, bus)
        # Simplified object list: [{'id': 1, 'dist': 100.0, 'rel_speed': -10.0}]
        # rel_speed: negative = closing in
        self.objects = []

    def add_object(self, obj_id, dist, rel_speed, lateral_pos=0.0, lateral_speed=0.0):
        """Add a synthetic object to the radar's field of view."""
        self.objects.append({
            'id': obj_id,
            'dist': dist,
            'rel_speed': rel_speed,
            'lat_pos': lateral_pos,
            'lat_speed': lateral_speed
        })

    def update_physics(self, dt):
        """Update the distance and lateral position of all detected objects."""
        # Update object positions based on relative speed
        for obj in self.objects:
            obj['dist'] += obj['rel_speed'] * dt
            obj['lat_pos'] += obj['lat_speed'] * dt

            # Remove objects that are behind us or too far
            if obj['dist'] < -10 or obj['dist'] > 200:
                self.objects.remove(obj)

    def publish_sensor_data(self):
        """Broadcast the list of detected objects to the virtual bus."""
        self.bus.broadcast('RADAR_OBJECTS', self.objects, sender=self.name)
