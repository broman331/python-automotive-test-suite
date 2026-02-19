"""
Reinforcement Learning Traffic Agent Test Suite.
Trains an RL Agent to find dangerous cut-in scenarios against the Ego vehicle.
Demonstrates: AI-Driven Adversarial Testing.
"""
import pytest
import random
from virtual_vehicle.sim.engine import SimulationEngine
from virtual_vehicle.plants.vehicle_dynamics import VehicleDynamics
from virtual_vehicle.ecus.adas_ecu import AdasECU
from virtual_vehicle.plants.radar_generator import RadarGenerator
from virtual_vehicle.ai_agents.traffic_agent import TrafficAgent
from virtual_vehicle.utilities.report_generator import ReportGenerator

class TestRLTraffic:
    """
    Trains an agent over multiple episodes to learn "Cut-In" behavior.
    Then verifies if ADAS can handle the learnt adversary.
    """
    
    @pytest.fixture
    def setup_sim(self):
        sim = SimulationEngine(time_step=0.1)
        vehicle = VehicleDynamics('VehicleDynamics', sim.bus)
        radar = RadarGenerator('RadarGen', sim.bus)
        adas = AdasECU('ADAS_ECU', sim.bus)
        
        sim.add_plant(vehicle)
        sim.add_plant(radar)
        sim.add_ecu(adas)
        
        return sim, vehicle, radar, adas

    def generate_report(self, sim, test_name, result="PASS"):
        ReportGenerator().generate(test_name, list(sim.bus.get_log()), result)

    def test_rl_agent_training(self, setup_sim):
        """
        Scenario: Train RL Agent to cut in front of Ego.
        Episodes: 100 Training Episodes.
        Verification: Run 1 Evaluation Episode with trained policy.
        """
        sim, vehicle, radar, adas = setup_sim
        
        initial_pos = {'x': 0.0, 'y': 3.5} # START ALONGSIDE EGO!
        initial_speed = 25.0 # Faster than Ego (20)
        
        # 1. Random Seed for Reproducibility
        random.seed(42)
        
        agent = TrafficAgent(agent_id=999, initial_pos=initial_pos, initial_speed=initial_speed)
        agent.alpha = 0.5 # Aggressive learning
        
        print("\n--- RL Training Start ---")
        
        # Training Loop (1000 Episodes)
        agent.epsilon = 0.5 # High exploration initially
        
        for episode in range(1000):
            # Decay Epsilon but keep min 0.1
            if episode % 100 == 0 and agent.epsilon > 0.1:
                agent.epsilon -= 0.05
                
            # Reset Episode
            vehicle.state['v'] = 20.0
            vehicle.state['x'] = 0.0
            vehicle.state['y'] = 0.0
            
            agent.x = 0.0 # Start WITH Ego
            agent.y = 3.5
            agent.v = 25.0
            
            # Run Episode (max 100 steps = 10s)
            for step in range(50):
                # Ego State for Agent
                ego_state = {'x': vehicle.state['x'], 'y': vehicle.state['y'], 'v': vehicle.state['v']}
                
                # Update Agent (Action -> Reward -> Learn)
                # Mock reward calculation inside update based on proximity
                agent.update(0.1, ego_state)
                
                # Update Ego Physics (Simple constant speed for training target)
                vehicle.update_physics(0.1) 
                
        print(f"--- Training Complete. Q-Table Size: {len(agent.q_table)} states ---")
        
        # Evaluation Episode (Run continuously with full SIM)
        print("\n--- Evaluation Episode ---")
        
        # Reset for Eval
        vehicle.state['v'] = 20.0
        vehicle.state['x'] = 0.0
        radar.objects = []
        adas.aeb_triggered = False
        
        agent.x = -20.0
        agent.y = 3.5
        agent.v = 28.0 # Give it a speed advantage
        agent.epsilon = 0.0 # Greedy policy (No exploration)
        
        collision = False
        
        for _ in range(100): # 10 seconds
            sim.step() # Steps Vehicle, Radar, ADAS
            
            # Step Agent Manually
            ego_state = {'x': vehicle.state['x'], 'y': vehicle.state['y'], 'v': vehicle.state['v']}
            agent.update(0.1, ego_state)
            
            # Update Radar with Agent Position
            radar.objects = [] # Clear
            # Calculate relative pos
            rel_dist = agent.x - vehicle.state['x']
            
            # Only visible if in front? No, radar sees 360 in this simple model, 
            # but usually we care about front. Let's add it regardless.
            radar.add_object(
                obj_id=agent.id,
                dist=rel_dist,
                rel_speed=agent.v - vehicle.state['v'],
                lateral_pos=agent.y
            )
            
            if _ % 10 == 0:
                print(f"Time {_ * 0.1:.1f}s | Agent X: {agent.x:.1f} Y: {agent.y:.1f} | Ego X: {vehicle.state['x']:.1f}")

            # Collision Check
            if rel_dist < 4.0 and abs(agent.y) < 1.0: # Physical collision box
                 print("  [RL] COLLISION! Agent hit Ego!")
                 collision = True
                 break

        self.generate_report(sim, "RL_Agent_Evaluation", result="FAIL" if collision else "PASS")
        
        # Verify the agent successfully merged (y ~ 0)
        assert abs(agent.y) < 1.0, f"Agent failed to learn cut-in! Final Y: {agent.y}"
        assert not collision, "Agent caused a collision (too aggressive!)"
