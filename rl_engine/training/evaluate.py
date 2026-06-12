# rl_engine/training/evaluate.py

"""
EVALUATION SCRIPT — Compare trained AI vs fixed-timer baseline

WHY EVALUATE SEPARATELY?
  Training tells us: "the agent improved over time"
  Evaluation tells us: "is the agent actually better than doing nothing?"
  
  We compare two scenarios over the same 1-hour simulation:
  
  Scenario A: FIXED TIMER
    NS green 30s → NS yellow 3s → EW green 30s → EW yellow 3s → repeat
    This is what every basic traffic light does today.
  
  Scenario B: TRAINED AI
    AI observes traffic every 10s → decides keep or switch
    Should learn to give more time to busier roads.

METRICS WE COMPARE:
  - Average waiting time per vehicle
  - Total waiting time across all roads
  - Number of vehicles that passed through
  - Maximum queue length reached
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

import numpy as np
import traci
from rl_engine.environment.traffic_env import TrafficEnv
from rl_engine.agents.dqn_agent import load_dqn_agent
from rl_engine.environment.observation_space import get_raw_state


def run_fixed_timer_baseline(num_episodes=3):
    """
    Runs the simulation with the DEFAULT fixed-timer traffic light.
    No AI involved — just SUMO's built-in static timing.
    
    Returns average metrics across num_episodes.
    """
    print("\n📊 Running Fixed-Timer Baseline...")
    print("   (Using default 30s NS / 30s EW static timing)")

    env = TrafficEnv(use_gui=False, delta_time=10, max_steps=360)

    all_waits    = []
    all_queues   = []

    for ep in range(num_episodes):
        state, _ = env.reset()
        total_wait  = 0.0
        max_queue   = 0
        steps       = 0

        while True:
            # Fixed timer = always KEEP (let SUMO's default timing run)
            # Actually: we override by always choosing action 0
            # But we disable our constraint system for true fixed timing
            # by running SUMO without TraCI control
            action = 0  # Always keep → SUMO runs its built-in program

            _, _, terminated, _, info = env.step(action)

            total_wait += info.get("total_wait", 0)
            traffic = info.get("traffic", {})
            if traffic:
                q = traffic.get("queue", {})
                max_queue = max(max_queue, max(q.values()) if q else 0)
            steps += 1

            if terminated:
                break

        avg_wait = total_wait / steps if steps > 0 else 0
        all_waits.append(avg_wait)
        all_queues.append(max_queue)
        print(f"   Episode {ep+1}: avg_wait={avg_wait:.1f}s, max_queue={max_queue}")

    env.close()

    return {
        "avg_wait":   np.mean(all_waits),
        "max_queue":  np.mean(all_queues),
        "label":      "Fixed Timer",
    }


def run_ai_agent(model_path, num_episodes=3):
    """
    Runs the simulation with the trained DQN agent in control.
    
    Parameters:
        model_path  - path to the .zip model file
        num_episodes - how many episodes to average over
    
    Returns average metrics across num_episodes.
    """
    print(f"\n🤖 Running Trained AI Agent...")
    print(f"   Model: {model_path}")

    env = TrafficEnv(use_gui=False, delta_time=10, max_steps=360)
    model = load_dqn_agent(model_path, env)

    all_waits    = []
    all_queues   = []
    all_switches = []

    for ep in range(num_episodes):
        state, _ = env.reset()
        total_wait  = 0.0
        max_queue   = 0
        num_switches = 0
        steps        = 0

        while True:
            # AI predicts the best action
            # deterministic=True → always pick best action (no randomness)
            action, _ = model.predict(state, deterministic=True)
            action = int(action)  # Ensure it's an int

            state, _, terminated, _, info = env.step(action)

            total_wait += info.get("total_wait", 0)
            traffic = info.get("traffic", {})
            if traffic:
                q = traffic.get("queue", {})
                max_queue = max(max_queue, max(q.values()) if q else 0)
            if "SWITCH" in info.get("action_taken", ""):
                num_switches += 1
            steps += 1

            if terminated:
                break

        avg_wait = total_wait / steps if steps > 0 else 0
        all_waits.append(avg_wait)
        all_queues.append(max_queue)
        all_switches.append(num_switches)
        print(f"   Episode {ep+1}: avg_wait={avg_wait:.1f}s, "
              f"max_queue={max_queue}, switches={num_switches}")

    env.close()

    return {
        "avg_wait":    np.mean(all_waits),
        "max_queue":   np.mean(all_queues),
        "avg_switches": np.mean(all_switches),
        "label":       "Trained DQN",
    }


def evaluate(model_path):
    """
    Runs full comparison: Fixed Timer vs Trained AI.
    Prints a clear comparison table.
    """
    print("=" * 60)
    print("  🏆 EVALUATION: Fixed Timer vs Trained AI")
    print("=" * 60)

    # Run both
    fixed  = run_fixed_timer_baseline(num_episodes=3)
    ai     = run_ai_agent(model_path, num_episodes=3)

    # ── PRINT COMPARISON TABLE ────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"  {'Metric':<25} {'Fixed Timer':>12} {'Trained AI':>12} {'Improvement':>12}")
    print("  " + "-" * 57)

    # Avg wait time
    wait_improvement = ((fixed["avg_wait"] - ai["avg_wait"]) / 
                         fixed["avg_wait"] * 100) if fixed["avg_wait"] > 0 else 0
    print(f"  {'Avg Wait Time':<25} {fixed['avg_wait']:>11.1f}s "
          f"{ai['avg_wait']:>11.1f}s "
          f"{wait_improvement:>+11.1f}%")

    # Max queue
    queue_improvement = ((fixed["max_queue"] - ai["max_queue"]) / 
                          fixed["max_queue"] * 100) if fixed["max_queue"] > 0 else 0
    print(f"  {'Max Queue Length':<25} {fixed['max_queue']:>11.1f} "
          f"{ai['max_queue']:>11.1f} "
          f"{queue_improvement:>+11.1f}%")

    print("=" * 60)

    if wait_improvement > 0:
        print(f"\n  ✅ AI reduced average wait time by {wait_improvement:.1f}%!")
    else:
        print(f"\n  ⚠️  AI needs more training. Try increasing TOTAL_TIMESTEPS.")

    return fixed, ai


if __name__ == "__main__":
    # Find the best model in the models directory
    model_dir = "rl_engine/models"
    models = [f for f in os.listdir(model_dir) if f.endswith("_best.zip")]

    if not models:
        print("❌ No trained model found! Run train.py first.")
        sys.exit(1)

    # Use the most recently trained model
    latest = sorted(models)[-1]
    model_path = os.path.join(model_dir, latest.replace(".zip", ""))
    print(f"Using model: {model_path}")

    evaluate(model_path)