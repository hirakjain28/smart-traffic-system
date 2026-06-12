# backend/services/rl_service.py

"""
RL SERVICE — Loads and runs the trained DQN model

This service is a thin wrapper around the trained model.
It handles:
  - Loading the model from disk
  - Running inference (predicting actions)
  - Generating human-readable suggestions for the dashboard
  - Graceful handling when no model is found
"""

import os
import sys
import numpy as np
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from backend.config import get_latest_model_path
from rl_engine.environment.traffic_env import TrafficEnv
from rl_engine.agents.dqn_agent import load_dqn_agent
from rl_engine.environment.action_space import ACTION_KEEP, ACTION_SWITCH


class RLService:
    """
    Manages the trained DQN model for inference.
    
    "Inference" = using the trained model to make predictions.
    (As opposed to "training" = updating the model weights)
    
    During inference:
      - Model weights are FROZEN (not updated)
      - We just do a forward pass: state → Q-values → action
      - Very fast (milliseconds)
    """

    def __init__(self):
        self.model      = None
        self.model_path = None
        self._load_model()

    def _load_model(self):
        """Loads the latest trained model from disk."""
        model_path = get_latest_model_path()

        if model_path is None:
            print("⚠️  No trained model found. Running in manual mode.")
            print("   Train a model first: python rl_engine/training/train.py")
            return

        try:
            # Create a dummy environment just to load the model
            # (SB3 needs an env to validate observation/action spaces)
            dummy_env   = TrafficEnv(use_gui=False)
            self.model  = load_dqn_agent(model_path, dummy_env)
            dummy_env.close()
            self.model_path = model_path
            print(f"✅ RL model loaded: {model_path}")
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            self.model = None

    def is_loaded(self) -> bool:
        """Returns True if a model is loaded and ready."""
        return self.model is not None

    def predict(self, state_vector: np.ndarray) -> int:
        """
        Runs inference: given state, returns action (0 or 1).
        
        Parameters:
            state_vector  - numpy array of shape (10,) from observation_space
        
        Returns:
            int  - 0 (KEEP) or 1 (SWITCH)
        """
        if not self.is_loaded():
            return ACTION_KEEP

        action, _ = self.model.predict(state_vector, deterministic=True)
        return int(action)

    def get_suggestion(self, state_vector: np.ndarray,
                       raw_state: dict) -> dict:
        """
        Returns a human-readable suggestion with explanation.
        
        This is shown on the dashboard as:
        "AI recommends: SWITCH — East-West has been waiting 85s"
        
        HOW CONFIDENCE WORKS:
        DQN outputs Q-values for each action.
        Q = [KEEP: -2.1, SWITCH: -8.7]
        Confidence = |Q_best - Q_other| / (|Q_best| + 0.001)
        Higher difference = more confident in recommendation.
        """
        if not self.is_loaded():
            return {
                "action":      "KEEP",
                "confidence":  0.0,
                "reason":      "No AI model loaded",
                "total_wait":  sum(raw_state.get("wait", {}).values()),
            }

        # Get Q-values from model
        # q_values shape: (1, 2) → [Q(KEEP), Q(SWITCH)]
        import torch
        obs_tensor = torch.FloatTensor(state_vector).unsqueeze(0)
        with torch.no_grad():
            q_values = self.model.policy.q_net(obs_tensor).numpy()[0]

        best_action = int(np.argmax(q_values))
        confidence  = abs(q_values[0] - q_values[1]) / (abs(max(q_values)) + 0.001)
        confidence  = min(float(confidence), 1.0)

        # Build human readable reason
        wait   = raw_state.get("wait",  {})
        queue  = raw_state.get("queue", {})
        max_wait_dir = max(wait, key=wait.get) if wait else "unknown"
        max_wait_val = wait.get(max_wait_dir, 0)

        if best_action == ACTION_SWITCH:
            reason = (
                f"Switch recommended — {max_wait_dir.capitalize()} road "
                f"has {max_wait_val:.0f}s total wait"
            )
        else:
            reason = (
                f"Hold recommended — current phase is managing "
                f"traffic efficiently"
            )

        return {
            "action":     "SWITCH" if best_action == ACTION_SWITCH else "KEEP",
            "confidence": round(confidence, 3),
            "reason":     reason,
            "total_wait": round(sum(wait.values()), 1),
            "q_values":   {
                "keep":   round(float(q_values[ACTION_KEEP]),   3),
                "switch": round(float(q_values[ACTION_SWITCH]), 3),
            }
        }