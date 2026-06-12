# rl_engine/training/callbacks.py

"""
TRAINING CALLBACKS — Custom hooks into the training loop

WHAT IS A CALLBACK?
Stable Baselines3 calls your callback functions at specific points:
  - Every N steps (to log progress)
  - At the end of each episode (to save best model)
  - At the end of training (to generate plots)

Think of it like event listeners in web development.

OUR CALLBACK DOES:
  1. Every episode: log reward, wait time, switches, overrides to CSV
  2. Every 5 episodes: print progress to terminal
  3. Whenever reward improves: save a checkpoint of the model
  4. End of training: generate the reward/wait time plot

WHY SAVE BEST MODEL SEPARATELY?
  Training can degrade! The agent sometimes "forgets" good strategies.
  We save a checkpoint whenever we see the best reward so far.
  Even if training degrades later, we have the best version saved.
"""

import os
import numpy as np
from stable_baselines3.common.callbacks import BaseCallback
from rl_engine.utils.logger import TrafficLogger
from rl_engine.utils.plotter import plot_training_results


class TrafficTrainingCallback(BaseCallback):
    """
    Custom callback for logging and saving during DQN training.
    
    Inherits from BaseCallback (Stable Baselines3).
    We override _on_step() which is called every environment step.
    """

    def __init__(self,
                 log_dir="data/logs",
                 model_dir="rl_engine/models",
                 run_name=None,
                 print_freq=5,       # print progress every N episodes
                 verbose=1):

        super().__init__(verbose)

        self.log_dir   = log_dir
        self.model_dir = model_dir
        self.run_name  = run_name
        self.print_freq = print_freq

        os.makedirs(model_dir, exist_ok=True)

        # Initialize logger
        self.logger_obj = TrafficLogger(log_dir=log_dir, run_name=run_name)

        # Tracking variables (reset each episode)
        self._episode_reward    = 0.0
        self._episode_waits     = []
        self._episode_switches  = 0
        self._episode_overrides = 0
        self._episode_steps     = 0
        self._episode_count     = 0

        # Best reward seen so far (for saving best model)
        self._best_reward = -np.inf

    def _on_step(self):
        """
        Called by SB3 after EVERY environment step.
        
        self.locals contains:
          - 'rewards'  : reward from this step
          - 'infos'    : info dict from env.step()
          - 'dones'    : True if episode ended this step
        
        Returns True to continue training, False to stop.
        """

        # ── COLLECT STEP DATA ─────────────────────────────────────────────────
        reward = self.locals["rewards"][0]
        info   = self.locals["infos"][0]
        done   = self.locals["dones"][0]

        self._episode_reward  += reward
        self._episode_steps   += 1

        # Collect wait time from info dict
        if "total_wait" in info:
            self._episode_waits.append(info["total_wait"])

        # Count switches and overrides
        if "action_taken" in info and "SWITCH" in info["action_taken"]:
            self._episode_switches += 1
        if info.get("action_overridden", False):
            self._episode_overrides += 1

        # ── END OF EPISODE ────────────────────────────────────────────────────
        if done:
            self._episode_count += 1

            # Calculate episode statistics
            avg_wait   = np.mean(self._episode_waits) if self._episode_waits else 0.0
            total_wait = np.sum(self._episode_waits)  if self._episode_waits else 0.0

            # Get current epsilon from the model
            epsilon = self.model.exploration_rate

            # Log to CSV
            self.logger_obj.log_episode(
                total_reward  = self._episode_reward,
                avg_wait      = avg_wait,
                total_wait    = total_wait,
                num_switches  = self._episode_switches,
                num_overrides = self._episode_overrides,
                steps         = self._episode_steps,
                epsilon       = epsilon,
            )

            # ── SAVE BEST MODEL ───────────────────────────────────────────────
            if self._episode_reward > self._best_reward:
                self._best_reward = self._episode_reward
                best_path = os.path.join(self.model_dir, f"{self.run_name}_best")
                self.model.save(best_path)
                if self.verbose:
                    print(f"  💾 New best model saved! Reward: {self._episode_reward:.3f}")

            # ── PRINT PROGRESS ────────────────────────────────────────────────
            if self._episode_count % self.print_freq == 0:
                avg_r, avg_w = self.logger_obj.get_recent_avg(last_n=self.print_freq)
                print(
                    f"  Episode {self._episode_count:>4} | "
                    f"Reward: {avg_r:>8.3f} | "
                    f"Avg Wait: {avg_w:>6.1f}s | "
                    f"Switches: {self._episode_switches:>3} | "
                    f"ε: {epsilon:.3f}"
                )

            # ── RESET EPISODE TRACKERS ────────────────────────────────────────
            self._episode_reward    = 0.0
            self._episode_waits     = []
            self._episode_switches  = 0
            self._episode_overrides = 0
            self._episode_steps     = 0

        return True  # Continue training

    def _on_training_end(self):
        """Called once when training finishes."""
        print("\n🏁 Training complete!")
        self.logger_obj.print_summary()

        # Generate plots
        print("\n📊 Generating training plots...")
        plot_training_results(
            log_path=self.logger_obj.log_path,
            save_dir=self.log_dir
        )