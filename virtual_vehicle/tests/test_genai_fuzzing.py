"""
Generative AI Fuzzing Test Suite.
Uses the ScenarioGenerator to create dynamic, adversarial test cases.
Demonstrates: AI as the Adversary.
"""
import pytest
from virtual_vehicle.sim.engine import SimulationEngine
from virtual_vehicle.plants.vehicle_dynamics import VehicleDynamics
from virtual_vehicle.ecus.adas_ecu import AdasECU
from virtual_vehicle.plants.radar_generator import RadarGenerator
from virtual_vehicle.ai_agents.scenario_generator import ScenarioGenerator
from virtual_vehicle.utilities.report_generator import ReportGenerator

class TestGenAIFuzzing:
    """
    Runs batches of procedurally generated scenarios to test ADAS robustness.
    """
    
    @pytest.fixture
    def setup_sim(self):
        sim = SimulationEngine(time_step=0.05)
        vehicle = VehicleDynamics('VehicleDynamics', sim.bus)
        radar = RadarGenerator('RadarGen', sim.bus)
        adas = AdasECU('ADAS_ECU', sim.bus)
        
        sim.add_plant(vehicle)
        sim.add_plant(radar)
        sim.add_ecu(adas)
        
        return sim, vehicle, radar, adas

    def generate_report(self, sim, test_name, result="PASS"):
        ReportGenerator().generate(test_name, list(sim.bus.get_log()), result)

    def test_adversarial_braking_scenarios(self, setup_sim):
        """
        Scenario: GenAI creates 5 variants of a "Braking Event".
        Varies: Initial Speed, Friction, Cut-In distance.
        Pass Criteria: Collisions must be 0 (unless physics makes it impossible).
        """
        sim, vehicle, radar, adas = setup_sim
        gen_ai = ScenarioGenerator(seed=42) # Deterministic seed for reproducibility
        
        base_scenario = {
            'initial_speed': 25.0, # ~90 km/h
            'environment': {'mu': 1.0},
            'traffic': []
        }
        
        # Generate 5 scenarios with "ADVERSARIAL" profile
        scenarios = gen_ai.generate_batch(base_scenario, count=5, profile_name='ADVERSARIAL')
        
        failures = []
        
        print("\n--- GenAI Fuzzing Start ---")
        for i, scenario in enumerate(scenarios):
            print(f"Running Variant {i+1}: Speed={scenario['initial_speed']:.2f}, Env={scenario.get('environment')}, Traffic={len(scenario['traffic'])}")
            
            # 1. Reset Simulation State (Partial reset logic)
            vehicle.state['v'] = scenario['initial_speed']
            vehicle.state['x'] = 0.0
            vehicle.state['y'] = 0.0
            radar.objects = [] # Clear old objects
            adas.aeb_triggered = False
            
            # 2. Apply Environment
            if 'mu' in scenario['environment']:
                sim.bus.broadcast('SET_ENV_MU', {'mu': scenario['environment']['mu']}, sender='GenAI')
            if 'mu_l' in scenario['environment']: 
                 sim.bus.broadcast('SET_ENV_MU', scenario['environment'], sender='GenAI')

            # 3. Setup Traffic
            for obj in scenario['traffic']:
                radar.add_object(
                    obj_id=obj['id'], 
                    dist=obj['dist'], 
                    rel_speed=obj['rel_speed'], 
                    lateral_pos=obj['lateral_pos']
                )

            # 4. Run Simulation Episode
            collision = False
            min_ttc = 100.0
            
            for _ in range(60): # 3 seconds
                sim.step()
                
                # Check for Cut-In Behavior (Teleporting laterally for simplicity)
                for obj in scenario['traffic']:
                    if obj.get('behavior') == 'CUT_IN' and _ == 20: # Trigger at 1s
                         # Find the radar object and move it to 0.0 lateral
                         for r_obj in radar.objects:
                             if r_obj['id'] == obj['id']:
                                 r_obj['lat'] = 0.0 # Cut in!
                                 print(f"  [GenAI] Object {obj['id']} CUT-IN!")

                # Collision Check
                if radar.objects and radar.objects[0]['dist'] <= 0:
                    collision = True
                    break
            
            if collision:
                failures.append(f"Variant {i+1} Resulted in Collision! Params: {scenario}")
                self.generate_report(sim, f"GenAI_Fail_Variant_{i+1}", result="FAIL")
            else:
                 self.generate_report(sim, f"GenAI_Pass_Variant_{i+1}", result="PASS")

        # Assert no collisions in generated batch
        if failures:
            pytest.fail(f"GenAI found {len(failures)} failures:\n" + "\n".join(failures))
