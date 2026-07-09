# rl_engine/agents/multi_agent_manager.py

"""
PARAMETER-SHARING MULTI-AGENT MANAGER

ONE shared DQN network for all 4 intersections.

WHY THIS IS BETTER FOR OUR CASE:
  Non-stationarity was causing individual agents to diverge badly
  (one intersection hitting 12,000s wait while others were fine).

  Parameter sharing solves this because:
  1. All 4 intersections use the same policy → no conflicting updates
  2. 4x more training data per episode → faster, more stable learning
  3. The shared network learns a GENERAL strategy that works for any
     intersection — this also generalizes better to new intersections
     in Phase 7+ if we ever expand the grid

  Each intersection still gets its own 14-feature observation
  (own state + neighbor summary), so the network CAN specialize
  its behavior based on what it sees — it just shares weights.

TRAINING FLOW:
  Each step → 4 observations → 4 actions → 4 rewards → 4 transitions
  ALL 4 transitions go into ONE replay buffer
  ONE gradient update per step on that shared buffer
"""

import os
import numpy as np
from stable_baselines3 import DQN
from rl_engine.environment.multi_intersection_env import (
    MultiIntersectionEnv, SingleAgentWrapper, INTERSECTIONS
)

ESTIMATED_TOTAL_TIMESTEPS = 360 * 500

DQN_CONFIG = {
    "policy":                  "MlpPolicy",
    "learning_rate":           0.0005,     # slightly lower — more stable
    "buffer_size":             50_000,     # larger buffer — 4x more data flowing in
    "learning_starts":         1_000,
    "batch_size":              128,        # larger batch — more stable gradients
    "gamma":                   0.95,
    "target_update_interval":  1_000,
    "exploration_fraction":    0.25,
    "exploration_initial_eps": 1.0,
    "exploration_final_eps":   0.05,
    "policy_kwargs":           dict(net_arch=[128, 128]),  # slightly bigger network
    "verbose":                 0,
}


class MultiAgentManager:
    """
    One shared DQN for all 4 intersections.
    All intersections contribute to and act from the same network.
    """

    def __init__(self, multi_env: MultiIntersectionEnv):
        self.multi_env        = multi_env
        self._global_timestep = 0
        self._build_shared_agent()

    def _build_shared_agent(self):
        print("🧠 Building shared DQN agent (parameter sharing)...")

        # One wrapper for setup purposes — all intersections use same obs/action space
        wrapper = SingleAgentWrapper(self.multi_env, "A")

        self.shared_agent = DQN(env=wrapper, **DQN_CONFIG)

        # Initialize SB3 internals so agent.train() works
        self.shared_agent._setup_learn(
            total_timesteps=ESTIMATED_TOTAL_TIMESTEPS,
            callback=None,
            reset_num_timesteps=True,
            tb_log_name="DQN_shared",
            progress_bar=False,
        )

        params = sum(
            p.numel() for p in self.shared_agent.policy.parameters()
        )
        print(f"   Architecture: {DQN_CONFIG['policy_kwargs']['net_arch']}")
        print(f"   State size:   14 features (10 own + 4 neighbor)")
        print(f"   Buffer size:  {DQN_CONFIG['buffer_size']:,} "
              f"(shared across all 4 intersections)")
        print(f"   Parameters:   {params:,}")
        print("✅ Shared agent built + initialized")

    def predict_all(self, observations: dict,
                    deterministic=False) -> dict:
        """
        All 4 intersections query the SAME network with their own obs.
        Same weights, different inputs → potentially different actions
        (because the network reads the local traffic state).
        """
        actions = {}
        for tl_id in INTERSECTIONS:
            action, _ = self.shared_agent.predict(
                observations[tl_id], deterministic=deterministic
            )
            actions[tl_id] = int(action)
        return actions

    def store_and_train(self, obs, actions, rewards, next_obs, done):
        """
        Pushes ALL 4 intersection transitions into the ONE shared buffer,
        then does a single gradient update.

        This gives the shared network 4x the training signal per step
        compared to a single-agent setup.
        """
        self._global_timestep += 1

        # Push all 4 transitions into the shared replay buffer
        for tl_id in INTERSECTIONS:
            self.shared_agent.replay_buffer.add(
                obs[tl_id].reshape(1, -1),
                next_obs[tl_id].reshape(1, -1),
                np.array([[actions[tl_id]]]),
                np.array([[rewards[tl_id]]]),
                np.array([[done]]),
                [{}],
            )

        # Update internal SB3 counters
        self.shared_agent.num_timesteps = self._global_timestep
        self.shared_agent._current_progress_remaining = max(
            0.0,
            1.0 - self._global_timestep / ESTIMATED_TOTAL_TIMESTEPS
        )

        # Single gradient update when buffer is ready
        buf  = self.shared_agent.replay_buffer
        if (buf.size() >= self.shared_agent.batch_size and
                buf.size() >= self.shared_agent.learning_starts):
            self.shared_agent.train(
                batch_size=self.shared_agent.batch_size,
                gradient_steps=1
            )

    def save_all(self, model_dir: str, run_name: str):
        """
        Saves the single shared model.
        We still use the _A suffix convention so load_all() works
        without changes in the evaluation script.
        """
        os.makedirs(model_dir, exist_ok=True)
        # Save once but with all 4 suffix names so loader finds them
        for tl_id in INTERSECTIONS:
            path = os.path.join(model_dir, f"{run_name}_{tl_id}")
            self.shared_agent.save(path)
        print(f"💾 Shared model saved as "
              f"{model_dir}/{run_name}_[A/B/C/D].zip")

    @classmethod
    def load_all(cls, model_dir: str, run_name: str,
                 multi_env: MultiIntersectionEnv):
        """Loads the shared model (reads the _A copy)."""
        manager           = cls.__new__(cls)
        manager.multi_env = multi_env
        manager._global_timestep = 0

        wrapper = SingleAgentWrapper(multi_env, "A")
        path    = os.path.join(model_dir, f"{run_name}_A")
        manager.shared_agent = DQN.load(path, env=wrapper)
        print(f"📂 Shared model loaded from {path}.zip")
        return manager

    def get_epsilon(self):
        return self.shared_agent.exploration_rate