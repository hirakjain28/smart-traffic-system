# rl_engine/utils/logger.py

"""
TRAFFIC LOGGER — Saves training data to CSV for analysis

WHY LOG EVERYTHING?
Training a neural network is like a black box.
Without logs, you don't know:
  - Is it actually improving?
  - When did it start learning?
  - What's the average wait time per episode?
  - Are constraints being triggered too often?

We log every episode to a CSV file so we can:
  - Plot learning curves
  - Compare different hyperparameter runs
  - Debug bad training runs
  - Show results in the dashboard later
"""

import os
import csv
from datetime import datetime


class TrafficLogger:
    """
    Logs training episode data to a CSV file.
    
    Each row = one training episode containing:
      - episode number
      - total reward
      - average waiting time
      - number of switches made
      - number of constraint overrides
      - epsilon value (how random the agent was)
    """

    def __init__(self, log_dir="data/logs", run_name=None):
        """
        Parameters:
            log_dir   - folder to save log files
            run_name  - name for this training run (auto-generated if None)
        """
        os.makedirs(log_dir, exist_ok=True)

        # Auto-generate run name from timestamp if not provided
        if run_name is None:
            run_name = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.run_name = run_name
        self.log_path = os.path.join(log_dir, f"{run_name}.csv")

        # ── CSV HEADER ────────────────────────────────────────────────────────
        self.columns = [
            "episode",
            "total_reward",
            "avg_wait_time",
            "total_wait_time",
            "num_switches",
            "num_overrides",
            "steps",
            "epsilon",
            "timestamp",
        ]

        # Create the CSV file and write header
        with open(self.log_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.columns)
            writer.writeheader()

        # In-memory storage for plotting
        self.episode_data = []
        self.episode_count = 0

        print(f"📝 Logger initialized: {self.log_path}")

    def log_episode(self, total_reward, avg_wait, total_wait,
                    num_switches, num_overrides, steps, epsilon):
        """
        Logs one complete episode to the CSV file.
        Call this at the end of each training episode.
        """
        self.episode_count += 1

        row = {
            "episode":       self.episode_count,
            "total_reward":  round(total_reward, 4),
            "avg_wait_time": round(avg_wait, 2),
            "total_wait_time": round(total_wait, 2),
            "num_switches":  num_switches,
            "num_overrides": num_overrides,
            "steps":         steps,
            "epsilon":       round(epsilon, 4),
            "timestamp":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Write to CSV
        with open(self.log_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.columns)
            writer.writerow(row)

        # Store in memory
        self.episode_data.append(row)

    def get_recent_avg(self, last_n=10):
        """
        Returns average reward and wait time over the last N episodes.
        Used to print progress during training.
        """
        if not self.episode_data:
            return 0.0, 0.0

        recent = self.episode_data[-last_n:]
        avg_reward = sum(r["total_reward"] for r in recent) / len(recent)
        avg_wait   = sum(r["avg_wait_time"] for r in recent) / len(recent)
        return avg_reward, avg_wait

    def print_summary(self):
        """Prints a summary of all logged episodes."""
        if not self.episode_data:
            print("No episodes logged yet.")
            return

        rewards = [r["total_reward"] for r in self.episode_data]
        waits   = [r["avg_wait_time"] for r in self.episode_data]

        print(f"\n📊 Training Summary ({self.episode_count} episodes)")
        print(f"   Best reward:    {max(rewards):.3f}")
        print(f"   Worst reward:   {min(rewards):.3f}")
        print(f"   Avg reward:     {sum(rewards)/len(rewards):.3f}")
        print(f"   Best avg wait:  {min(waits):.1f}s")
        print(f"   Log saved to:   {self.log_path}")