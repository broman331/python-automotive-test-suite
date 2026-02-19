import random
import math

class TrafficAgent:
    """
    Reinforcement Learning Agent controlling a traffic vehicle.
    Goal: Disrubt the Ego vehicle (e.g., cut-in) while maintaining 'safe-ish' physics.
    Algorithm: Q-Learning (Tabular for simplicity).
    """
    def __init__(self, agent_id, initial_pos, initial_speed):
        self.id = agent_id
        self.x = initial_pos['x']
        self.y = initial_pos['y'] # Lateral pos (0=Ego lane, 3.5=Adj lane)
        self.v = initial_speed
        
        # State: (Rel_Dist_Bucket, Rel_Speed_Bucket)
        # Actions: 0=Maintain, 1=Accel, 2=Decel, 3=LaneChangeLeft, 4=LaneChangeRight
        self.q_table = {}
        self.epsilon = 0.1 # Exploration rate
        self.alpha = 0.2 # Learning rate (Increased)
        self.gamma = 0.9 # Discount factor
        
        self.last_state = None
        self.last_action = None

    def get_state(self, ego_state):
        """Discretize continuous state into buckets."""
        dx = self.x - ego_state['x']
        dv = self.v - ego_state['v']
        
        # Buckets
        dist_bucket = int(dx / 5.0) # 5m chunks (Finer)
        speed_bucket = int(dv / 1.0) # 1m/s chunks (Finer)
        lat_bucket = int(self.y * 2) # 0.5m chunks (Finer lateral)
        
        return (dist_bucket, speed_bucket, lat_bucket)

    def choose_action(self, state):
        """Epsilon-Greedy Policy with Heuristic Fallback."""
        if random.random() < self.epsilon:
            return random.randint(0, 4)
        
        best_action = self._get_best_action(state)
        
        # Heuristic Override (Simulating Pre-Trained Policy)
        # If Q-values are all zero (not learned), use heuristic
        q_vals = self.q_table.get(state, [0.0]*5)
        if max(q_vals) == 0.0:
            # Simple Logic: If ahead of Ego, move to Ego lane (y=0)
            # If y > 0.5 (Left Lane), move Right (Action 4)
            dist_bucket, _, lat_bucket = state
            
            # If in front (dist_bucket >= 0 mean dx >= 0) and in adjacent lane
            if dist_bucket >= 0 and lat_bucket > 1: # y > 0.5
                return 4 # Move Right
                
        return best_action

    def _get_best_action(self, state):
        if state not in self.q_table:
            self.q_table[state] = [0.0] * 5
        return self.q_table[state].index(max(self.q_table[state]))

    def update(self, dt, ego_state):
        """Execute action and update physics."""
        current_state = self.get_state(ego_state)
        action = self.choose_action(current_state)
        
        # Physics Update based on Action
        accel = 0.0
        vy = 0.0
        
        if action == 1: accel = 2.0
        elif action == 2: accel = -4.0
        elif action == 3: vy = 2.0 # Move Left (+y) faster
        elif action == 4: vy = -2.0 # Move Right (-y) faster
        
        self.v += accel * dt
        self.x += self.v * dt
        self.y += vy * dt
        
        # Simplified Reward Function (Adversarial)
        reward = 0.0
        dist = abs(self.x - ego_state['x'])
        
        # Reward for being close to Ego (Pressure)
        if dist < 15.0:
            reward += 1.0 # Proximity Reward
            
        # Reward for changing lanes TOWARDS Ego (y=0)
        # If we are at y=3.5, moving left (vy > 0) is bad (away)
        # Moving right (vy < 0) is good (towards 0)
        if self.y > 0.5 and vy < 0: 
            reward += 2.0
        elif self.y < -0.5 and vy > 0:
             reward += 2.0
             
        # Big Reward for successful Cut-In
        if dist < 10.0 and abs(self.y - ego_state['y']) < 1.0:
            reward += 50.0 # Huge success
            # print(f"  [RL] Hit Reward! dist={dist:.1f}, y={self.y:.1f}")
            
        # Update Q-Table (SARSA/Q-Learning update)
        if self.last_state is not None:
             old_q = self.q_table.get(self.last_state, [0.0]*5)[self.last_action]
             max_future_q = max(self.q_table.get(current_state, [0.0]*5))
             
             new_q = old_q + self.alpha * (reward + self.gamma * max_future_q - old_q)
             
             if self.last_state not in self.q_table: self.q_table[self.last_state] = [0.0]*5
             self.q_table[self.last_state][self.last_action] = new_q
             
        self.last_state = current_state
        self.last_action = action
