# rl_engine/training/train_multi.py

"""
MULTI-AGENT TRAINING SCRIPT

WHY WE CAN'T USE model.learn() HERE:
  SB3's model.learn() drives its own loop internally.
  For multi-agent we need to:
    1. Step the environment once
    2. Route each intersection's observation to the right agent
    3. Store all 4 transitions manually
    4. Trigger training updates for all 4 agents

  So we write our own training loop — it's actually simpler to
  understand than single-agent because every step is explicit.

TRAINING LOOP STRUCTURE:
  for each episode:
      obs = env.reset()
      while not done:
          actions = manager.predict_all(obs)        # all 4 agents decide
          next_obs, rewards, done, info = env.step(actions)
          manager.store_transitions(...)            # fill replay buffers
          manager.train_step()                      # gradient update
          obs = next_obs
      log episode stats
  save all models
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

import numpy as np
from datetime import datetime
from rl_engine.environment.multi_intersection_env import MultiIntersectionEnv, INTERSECTIONS
from rl_engine.agents.multi_agent_manager import MultiAgentManager

TOTAL_EPISODES  = 200      # ~6.5 hours on CPU — good starting point
LOG_DIR         = "data/logs"
MODEL_DIR       = "rl_engine/models"
PRINT_EVERY     = 5        # print summary every N episodes
os.makedirs(LOG_DIR,   exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)


def train():
    run_name = f"multi_dqn_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print("=" * 60)
    print(f"  🚦 MULTI-INTERSECTION DQN TRAINING")
    print(f"  Run: {run_name}")
    print(f"  Episodes: {TOTAL_EPISODES}")
    print(f"  Intersections: A, B, C, D (2×2 grid)")
    print("=" * 60)

    env     = MultiIntersectionEnv(use_gui=False)
    manager = MultiAgentManager(env)

    best_avg_reward = -np.inf
    all_episode_rewards = []

    print(f"\n  {'Ep':>4} | {'Avg Reward':>10} | "
          f"{'A wait':>7} | {'B wait':>7} | "
          f"{'C wait':>7} | {'D wait':>7} | {'ε':>5}")
    print("  " + "─" * 60)

    for episode in range(1, TOTAL_EPISODES + 1):
        obs  = env.reset()
        done = False

        episode_rewards = {i: 0.0 for i in INTERSECTIONS}
        episode_waits   = {i: []  for i in INTERSECTIONS}

        while not done:
            # All 4 agents decide simultaneously
            actions = manager.predict_all(obs, deterministic=False)

            # Step simulation
            next_obs, rewards, done, info = env.step(actions)

            # Store transitions for all agents
            manager.store_and_train(obs, actions, rewards, next_obs, done)

            # Track stats
            for tl_id in INTERSECTIONS:
                episode_rewards[tl_id] += rewards[tl_id]
                wait = sum(info[tl_id]["raw_state"]["wait"].values())
                episode_waits[tl_id].append(wait)

            obs = next_obs

        # ── EPISODE COMPLETE ──────────────────────────────────────────────
        avg_reward = np.mean(list(episode_rewards.values()))
        all_episode_rewards.append(avg_reward)

        # Save best model
        if avg_reward > best_avg_reward:
            best_avg_reward = avg_reward
            manager.save_all(MODEL_DIR, f"{run_name}_best")

        # Print progress
        if episode % PRINT_EVERY == 0:
            avg_waits = {
                i: np.mean(episode_waits[i]) if episode_waits[i] else 0
                for i in INTERSECTIONS
            }
            eps = manager.get_epsilon()
            print(
                f"  {episode:>4} | {avg_reward:>10.2f} | "
                f"{avg_waits['A']:>6.1f}s | "
                f"{avg_waits['B']:>6.1f}s | "
                f"{avg_waits['C']:>6.1f}s | "
                f"{avg_waits['D']:>6.1f}s | "
                f"{eps:.3f}"
            )

    # ── TRAINING DONE ─────────────────────────────────────────────────────
    env.close()
    manager.save_all(MODEL_DIR, f"{run_name}_final")

    print("\n" + "=" * 60)
    print("✅ Multi-agent training complete!")
    print(f"   Best avg reward:  {best_avg_reward:.2f}")
    print(f"   Final avg reward: {np.mean(all_episode_rewards[-10:]):.2f}")
    print(f"   Models saved to:  {MODEL_DIR}/")
    print("=" * 60)

    return run_name


if __name__ == "__main__":
    train()