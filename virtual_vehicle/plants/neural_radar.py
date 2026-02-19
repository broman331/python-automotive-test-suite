import random
import math
from virtual_vehicle.plants.radar_generator import RadarGenerator

class NeuralRadar(RadarGenerator):
    """
    Advanced Radar Simulation using Neural Sensor Models.
    Simulates domain gaps (Weather, Time) and sensor imperfections (Ghost Objects, Noise).
    mimicking the behavior of AI-based perception systems.
    """
    def __init__(self, name, bus):
        super().__init__(name, bus)
        
        # Environmental Context
        self.weather = 'CLEAR' # CLEAR, RAIN, FOG, SNOW
        self.time_of_day = 'DAY' # DAY, NIGHT
        
        # Error Profiles (Standard Deviation in meters)
        self.noise_profiles = {
            'CLEAR': 0.1,
            'RAIN': 0.5,
            'FOG': 1.0,
            'SNOW': 2.0
        }
        
        # Ghost Object Probability
        self.ghost_prob = {
            'CLEAR': 0.00,
            'RAIN': 0.05,
            'FOG': 0.10, # Reflections
            'SNOW': 0.05
        }

    def receive_message(self, msg_id, data, sender):
        if msg_id == 'SET_ENV_WEATHER':
            self.weather = data.get('weather', 'CLEAR')
            print(f"[{self.name}] Weather changed to {self.weather}")
        elif msg_id == 'SET_ENV_TIME':
            self.time_of_day = data.get('time', 'DAY')
            print(f"[{self.name}] Time changed to {self.time_of_day}")
        else:
            super().receive_message(msg_id, data, sender)

    def step(self):
        # 1. Start with Ground Truth Objects (from Simulation Engine/Test)
        # In this mock, 'self.objects' is populated by the test runner directly
        # or by a 'WorldModel' if we had one.
        
        noisy_objects = []
        
        current_noise_std = self.noise_profiles.get(self.weather, 0.1)
        
        # 2. Add Noise to Valid Objects
        for obj in self.objects:
            # Distance Noise (Gaussian)
            dist_noise = random.gauss(0, current_noise_std)
            # Speed Noise (Doppler ambiguity in bad weather)
            speed_noise = random.gauss(0, current_noise_std * 0.5)
            
            noisy_obj = obj.copy()
            noisy_obj['dist'] = max(0.0, obj['dist'] + dist_noise)
            noisy_obj['rel_speed'] += speed_noise
            
            # Drop Probability (False Negative)
            # Heavy Rain might miss small objects
            drop_prob = 0.1 if self.weather == 'RAIN' else 0.0
            if random.random() > drop_prob:
                noisy_objects.append(noisy_obj)
                
        # 3. Generate Ghost Objects (False Positives)
        if random.random() < self.ghost_prob.get(self.weather, 0.0):
            # Create a ghost at random distance
            ghost = {
                'id': random.randint(9000, 9999),
                'dist': random.uniform(10.0, 50.0), # Random phantom
                'rel_speed': 0.0,
                'lateral_pos': 0.0 # In path!
            }
            noisy_objects.append(ghost)
            # print(f"[{self.name}] GHOST OBJECT DETECTED!")
            
        # 4. Broadcast
        self.bus.broadcast('RADAR_OBJECTS', noisy_objects, sender=self.name)
