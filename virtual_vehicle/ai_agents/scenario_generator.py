import random
import json
import math

class ScenarioGenerator:
    """
    Mock Generative AI for creating adversarial test scenarios.
    Uses 'risk profiles' to fuzz parameters within realistic bounds.
    """
    def __init__(self, seed=None):
        if seed:
            random.seed(seed)
        
        # Risk Profiles define "Temperature" of generation
        self.profiles = {
            'CONSERVATIVE': {
                'speed_variance': 0.05, # +/- 5%
                'friction_min': 0.8,
                'aggression': 0.1 # Low probability of cutting in
            },
            'ADVERSARIAL': {
                'speed_variance': 0.30, # +/- 30%
                'friction_min': 0.2, # Ice patches
                'aggression': 0.8 # High probability of cutting in
            },
            'CHAOS': {
                'speed_variance': 0.50,
                'friction_min': 0.1,
                'aggression': 1.0
            }
        }

    def generate_scenario(self, base_scenario, profile_name='ADVERSARIAL'):
        """
        Fuzzes a base scenario configuration based on the selected profile.
        """
        profile = self.profiles.get(profile_name, self.profiles['CONSERVATIVE'])
        
        # Deep copy base to avoid mutation
        scenario = json.loads(json.dumps(base_scenario))
        
        # 1. Fuzz Ego Vehicle Speed
        if 'initial_speed' in scenario:
            variance = profile['speed_variance']
            factor = random.uniform(1.0 - variance, 1.0 + variance)
            scenario['initial_speed'] *= factor
            
        # 2. Fuzz Environment Friction (Split-Mu or Low-Mu)
        if random.random() < profile['aggression']:
            # Create dangerous friction
            mu = random.uniform(profile['friction_min'], 0.9)
            scenario['environment'] = {'mu': mu}
            
            # 20% chance of Split-Mu in Adversarial mode
            if profile_name == 'ADVERSARIAL' and random.random() < 0.2:
                 scenario['environment'] = {'mu_l': 1.0, 'mu_r': 0.2}

        # 3. Add Traffic Objects (if supported)
        if 'traffic' not in scenario:
            scenario['traffic'] = []
            
        # In Adversarial mode, inject a cut-in vehicle
        if random.random() < profile['aggression']:
            # Calculate a "Critical" distance based on speed (Time To Collision ~ 1.5s)
            speed = scenario.get('initial_speed', 20.0)
            dist = speed * random.uniform(1.0, 2.0) 
            
            cut_in_vehicle = {
                'id': random.randint(100, 999),
                'dist': dist,
                'rel_speed': -5.0, # Slower than ego
                'lateral_pos': random.choice([-3.0, 3.0]), # Adjacent lane
                'behavior': 'CUT_IN' # Special flag for test runner
            }
            scenario['traffic'].append(cut_in_vehicle)
            
        return scenario

    def generate_batch(self, base_scenario, count=5, profile_name='ADVERSARIAL'):
        """Generates a batch of unique scenarios."""
        return [self.generate_scenario(base_scenario, profile_name) for _ in range(count)]
