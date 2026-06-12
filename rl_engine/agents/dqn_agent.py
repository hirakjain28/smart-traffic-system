# rl_engine/agents/dqn_agent.py

"""
DQN AGENT — Deep Q-Network configuration and setup

WHAT IS DQN?
DQN = Deep Q-Network (DeepMind, 2015)
It combines Q-learning (classic RL) with a neural network.

CLASSIC Q-LEARNING PROBLEM:
  A Q-table stores Q(state, action) for every possible state.
  Our state has 10 floats → infinite possible states → table is impossible.

DQN SOLUTION:
  Replace the table with a neural network.
  Input:  state vector (10 floats)
  Output: Q-value for each action (2 floats)
  
  Network learns to APPROXIMATE Q(state, action) for any state.

OUR NETWORK ARCHITECTURE:
  Input Layer:    10 neurons  (one per state feature)
       ↓
  Hidden Layer 1: 64 neurons  (learns low-level patterns)
       ↓
  Hidden Layer 2: 64 neurons  (learns high-level patterns)
       ↓
  Output Layer:   2 neurons   (Q-value for KEEP, Q-value for SWITCH)

WHY 64-64?
  Small enough to train fast on CPU.
  Large enough to capture the patterns in our 10-feature state.
  We can increase if performance is poor.

KEY DQN HYPERPARAMETERS EXPLAINED:
  
  learning_rate: How fast the network updates weights
    Too high → unstable, oscillates, never converges
    Too low  → learns very slowly
    0.001 is a good starting point
  
  buffer_size: How many past experiences to store
    10,000 = stores last ~28 hours of simulated traffic
    Larger = more diverse training data = more stable
  
  learning_starts: Don't train until we have this many experiences
    1,000 = fill buffer first, then start learning
    Prevents training on too little data early on
  
  batch_size: How many experiences to sample per training step
    64 = standard, balances speed vs stability
  
  gamma (discount factor): How much to value FUTURE rewards
    0.95 = care a lot about future (good for traffic — decisions
           have delayed consequences)
    0.0  = only care about immediate reward (shortsighted)
    1.0  = infinite future horizon (unstable)
  
  exploration_fraction: How quickly epsilon decays
    0.3 = spend 30% of training exploring (first 15,000 steps)
    
  target_update_interval: How often to sync target network
    DQN uses TWO networks:
    - "online" network: updated every step
    - "target" network: updated every N steps (stable reference)
    This prevents the moving-target problem.
    500 = update target every 500 steps
"""

from stable_baselines3 import DQN
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
import torch
import torch.nn as nn
import gymnasium as gym


# ── DQN HYPERPARAMETERS ───────────────────────────────────────────────────────
# These are the knobs you can tune to improve training performance
DQN_CONFIG = {
    # Neural network architecture
    # "MlpPolicy" = Multi-Layer Perceptron (standard feedforward network)
    "policy": "MlpPolicy",

    # How fast the network learns
    # Range: 0.0001 (slow stable) to 0.01 (fast unstable)
    "learning_rate": 0.001,

    # Size of the replay buffer (number of transitions to store)
    "buffer_size": 10_000,

    # Don't start training until this many experiences are collected
    "learning_starts": 1_000,

    # Number of experiences sampled per training update
    "batch_size": 64,

    # Discount factor — how much future rewards matter
    # 0.95 = care about reward 20 steps ahead
    "gamma": 0.95,

    # How often to update the target network (every N steps)
    "target_update_interval": 500,

    # Fraction of total timesteps spent exploring (epsilon > 0.1)
    "exploration_fraction": 0.3,

    # Starting epsilon (100% random at start)
    "exploration_initial_eps": 1.0,

    # Final epsilon (always keep 5% random exploration)
    "exploration_final_eps": 0.05,

    # Neural network layer sizes [hidden1, hidden2]
    "policy_kwargs": dict(net_arch=[64, 64]),

    # Print training info every N steps
    "verbose": 1,
}
# ─────────────────────────────────────────────────────────────────────────────


def build_dqn_agent(env, tensorboard_log=None):
    """
    Creates and returns a configured DQN agent.
    
    Parameters:
        env              - our TrafficEnv instance
        tensorboard_log  - folder to save TensorBoard logs (optional)
    
    Returns:
        model  - a Stable Baselines3 DQN model ready to train
    
    HOW STABLE BASELINES3 WORKS:
    SB3 wraps PyTorch to give us clean RL algorithms.
    DQN("MlpPolicy", env) creates:
      - A neural network with the architecture we specify
      - A replay buffer of size buffer_size
      - An optimizer (Adam by default)
      - All the DQN update logic
    
    We just call model.learn(total_timesteps=N) and it handles everything.
    """
    print("🧠 Building DQN Agent...")
    print(f"   Network architecture: {DQN_CONFIG['policy_kwargs']['net_arch']}")
    print(f"   Learning rate:        {DQN_CONFIG['learning_rate']}")
    print(f"   Replay buffer size:   {DQN_CONFIG['buffer_size']:,}")
    print(f"   Batch size:           {DQN_CONFIG['batch_size']}")
    print(f"   Gamma (discount):     {DQN_CONFIG['gamma']}")
    print(f"   Exploration: {DQN_CONFIG['exploration_initial_eps']} → {DQN_CONFIG['exploration_final_eps']}")

    model = DQN(
        policy=DQN_CONFIG["policy"],
        env=env,
        learning_rate=DQN_CONFIG["learning_rate"],
        buffer_size=DQN_CONFIG["buffer_size"],
        learning_starts=DQN_CONFIG["learning_starts"],
        batch_size=DQN_CONFIG["batch_size"],
        gamma=DQN_CONFIG["gamma"],
        target_update_interval=DQN_CONFIG["target_update_interval"],
        exploration_fraction=DQN_CONFIG["exploration_fraction"],
        exploration_initial_eps=DQN_CONFIG["exploration_initial_eps"],
        exploration_final_eps=DQN_CONFIG["exploration_final_eps"],
        policy_kwargs=DQN_CONFIG["policy_kwargs"],
        verbose=DQN_CONFIG["verbose"],
        tensorboard_log=tensorboard_log,
    )

    print(f"✅ DQN Agent built successfully!")
    print(f"   Total parameters: {sum(p.numel() for p in model.policy.parameters()):,}")

    return model


def load_dqn_agent(model_path, env):
    """
    Loads a previously trained DQN model from disk.
    
    Parameters:
        model_path  - path to the .zip file saved during training
        env         - the environment to attach the model to
    
    Returns:
        model  - loaded DQN model ready for inference or continued training
    
    WHY .zip?
    SB3 saves models as .zip files containing:
      - policy_weights.pth  (the neural network weights)
      - replay_buffer data  (optional)
      - training config     (hyperparameters)
    """
    print(f"📂 Loading DQN model from: {model_path}")
    model = DQN.load(model_path, env=env)
    print(f"✅ Model loaded successfully!")
    return model