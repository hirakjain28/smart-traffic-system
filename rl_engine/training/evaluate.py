# rl_engine/training/evaluate.py

"""
EVALUATION SCRIPT — Compare trained AI vs fixed-timer baseline

WHY EVALUATE SEPARATELY?
  Training tells us: "the agent improved its policy over time"
  Evaluation tells us: "is the agent actually better than a realistic baseline?"
  
  We compare two scenarios over the same 1-hour simulation:
  
  Scenario A: FIXED TIMER (Realistic 30s per green)
    North Green (30s) → Yellow (3s) → East Green (30s) → Yellow (3s) →
    South Green (30s) → Yellow (3s) → West Green (30s) → Yellow (3s) → repeat.
    Standard fixed-time rotation matching DEFAULT_GREEN_DURATION = 30s.

  Scenario B: TRAINED AI (DQN)
    AI observes queue lengths, waiting times, current phase and elapsed time
    every 10s → intelligently decides whether to KEEP or SWITCH.
    Prioritizes directions with growing queues and urgent wait times.

METRICS EVALUATED:
  1. Avg Wait Time / Vehicle (s/veh): True average delay experienced by each
     individual car from arrival until clearing the intersection.
  2. System Congestion / Step (s): Instantaneous sum of waiting time across all 4
     incoming roads combined at each 10s decision step.
  3. Max Lane Queue (vehicles): Longest single-lane queue observed.
  4. Max Total Queue (vehicles): Longest total intersection queue observed.
  5. Vehicles Serviced: Total throughput across the 1-hour period.
"""

import os
import sys

# Configure UTF-8 stdout on Windows to prevent UnicodeEncodeError with terminal symbols/emojis
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

import numpy as np
import traci
from rl_engine.environment.traffic_env import TrafficEnv
from rl_engine.agents.dqn_agent import load_dqn_agent
from rl_engine.environment.action_space import ACTION_KEEP, ACTION_SWITCH


def run_fixed_timer_baseline(num_episodes=3, fixed_green=30):
    """
    Runs the simulation with a standard fixed-timer traffic controller.
    Each green phase is held for `fixed_green` seconds (default: 30s) before switching.
    
    Returns average metrics across num_episodes.
    """
    print(f"\n📊 Running Fixed-Timer Baseline...")
    print(f"   (Standard fixed {fixed_green}s green per direction, 3s yellow)")

    env = TrafficEnv(use_gui=False, delta_time=10, max_steps=360)

    all_veh_waits      = []
    all_system_waits   = []
    all_lane_queues    = []
    all_total_queues   = []
    all_serviced       = []

    for ep in range(num_episodes):
        state, _ = env.reset()
        step_system_waits = []
        max_lane_q  = 0
        max_total_q = 0
        steps = 0

        while True:
            # Fixed timer logic: hold green for `fixed_green` seconds, then switch
            if env.time_in_phase >= fixed_green:
                action = ACTION_SWITCH
            else:
                action = ACTION_KEEP

            _, _, terminated, _, info = env.step(action)

            step_system_waits.append(info.get("total_wait", 0.0))

            traffic = info.get("traffic", {})
            if traffic:
                q = traffic.get("queue", {})
                if q:
                    max_lane_q  = max(max_lane_q, max(q.values()))
                    max_total_q = max(max_total_q, sum(q.values()))

            steps += 1
            if terminated:
                break

        veh_avg_wait = info.get("veh_avg_wait", 0.0)
        sys_avg_wait = np.mean(step_system_waits) if step_system_waits else 0.0
        serviced     = info.get("vehicles_served", 0)

        all_veh_waits.append(veh_avg_wait)
        all_system_waits.append(sys_avg_wait)
        all_lane_queues.append(max_lane_q)
        all_total_queues.append(max_total_q)
        all_serviced.append(serviced)

        print(f"   Episode {ep+1}: veh_avg_wait={veh_avg_wait:.1f}s/veh, "
              f"system_wait={sys_avg_wait:.1f}s, max_lane_q={max_lane_q}, serviced={serviced}")

    env.close()

    return {
        "veh_avg_wait":    np.mean(all_veh_waits),
        "system_wait":     np.mean(all_system_waits),
        "avg_wait":        np.mean(all_veh_waits),  # primary metric: realistic per-vehicle wait
        "max_lane_queue":  np.mean(all_lane_queues),
        "max_total_queue": np.mean(all_total_queues),
        "max_queue":       np.mean(all_lane_queues),
        "vehicles_served": np.mean(all_serviced),
        "label":           f"Fixed Timer ({fixed_green}s)",
    }


def run_ai_agent(model_path, num_episodes=3):
    """
    Runs the simulation with the trained DQN agent in control.
    
    Parameters:
        model_path   - path to the .zip model file
        num_episodes - how many episodes to average over
    
    Returns average metrics across num_episodes.
    """
    print(f"\n🤖 Running Trained AI Agent...")
    print(f"   Model: {model_path}")

    env = TrafficEnv(use_gui=False, delta_time=10, max_steps=360)
    model = load_dqn_agent(model_path, env)

    all_veh_waits      = []
    all_system_waits   = []
    all_lane_queues    = []
    all_total_queues   = []
    all_serviced       = []
    all_switches       = []

    for ep in range(num_episodes):
        state, _ = env.reset()
        step_system_waits = []
        max_lane_q   = 0
        max_total_q  = 0
        num_switches = 0
        steps = 0

        while True:
            # AI predicts the best action deterministically
            action, _ = model.predict(state, deterministic=True)
            action = int(action)

            state, _, terminated, _, info = env.step(action)

            step_system_waits.append(info.get("total_wait", 0.0))

            traffic = info.get("traffic", {})
            if traffic:
                q = traffic.get("queue", {})
                if q:
                    max_lane_q  = max(max_lane_q, max(q.values()))
                    max_total_q = max(max_total_q, sum(q.values()))

            if "SWITCH" in info.get("action_taken", ""):
                num_switches += 1

            steps += 1
            if terminated:
                break

        veh_avg_wait = info.get("veh_avg_wait", 0.0)
        sys_avg_wait = np.mean(step_system_waits) if step_system_waits else 0.0
        serviced     = info.get("vehicles_served", 0)

        all_veh_waits.append(veh_avg_wait)
        all_system_waits.append(sys_avg_wait)
        all_lane_queues.append(max_lane_q)
        all_total_queues.append(max_total_q)
        all_serviced.append(serviced)
        all_switches.append(num_switches)

        print(f"   Episode {ep+1}: veh_avg_wait={veh_avg_wait:.1f}s/veh, "
              f"system_wait={sys_avg_wait:.1f}s, max_lane_q={max_lane_q}, "
              f"serviced={serviced}, switches={num_switches}")

    env.close()

    return {
        "veh_avg_wait":    np.mean(all_veh_waits),
        "system_wait":     np.mean(all_system_waits),
        "avg_wait":        np.mean(all_veh_waits),  # primary metric: realistic per-vehicle wait
        "max_lane_queue":  np.mean(all_lane_queues),
        "max_total_queue": np.mean(all_total_queues),
        "max_queue":       np.mean(all_lane_queues),
        "vehicles_served": np.mean(all_serviced),
        "avg_switches":    np.mean(all_switches),
        "label":           "Trained DQN",
    }


def evaluate(model_path, num_episodes=3):
    """
    Runs full comparison: Fixed Timer vs Trained AI.
    Prints a clear comparison table.
    """
    print("=" * 72)
    print("  🏆 EVALUATION: Fixed Timer vs Trained AI")
    print("=" * 72)

    # Run both baselines
    fixed = run_fixed_timer_baseline(num_episodes=num_episodes, fixed_green=30)
    ai    = run_ai_agent(model_path, num_episodes=num_episodes)

    # Calculate improvements
    veh_wait_imp = ((fixed["veh_avg_wait"] - ai["veh_avg_wait"]) / 
                    fixed["veh_avg_wait"] * 100) if fixed["veh_avg_wait"] > 0 else 0.0

    sys_wait_imp = ((fixed["system_wait"] - ai["system_wait"]) / 
                    fixed["system_wait"] * 100) if fixed["system_wait"] > 0 else 0.0

    lane_q_imp   = ((fixed["max_lane_queue"] - ai["max_lane_queue"]) / 
                    fixed["max_lane_queue"] * 100) if fixed["max_lane_queue"] > 0 else 0.0

    total_q_imp  = ((fixed["max_total_queue"] - ai["max_total_queue"]) / 
                    fixed["max_total_queue"] * 100) if fixed["max_total_queue"] > 0 else 0.0

    # ── PRINT COMPARISON TABLE ────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print(f"  {'Metric':<32} {'Fixed Timer':>12} {'Trained AI':>12} {'Improvement':>12}")
    print("  " + "-" * 69)

    print(f"  {'Avg Wait Time / Vehicle':<32} "
          f"{fixed['veh_avg_wait']:>11.1f}s "
          f"{ai['veh_avg_wait']:>11.1f}s "
          f"{veh_wait_imp:>+11.1f}%")

    print(f"  {'System Total Wait / Step':<32} "
          f"{fixed['system_wait']:>11.1f}s "
          f"{ai['system_wait']:>11.1f}s "
          f"{sys_wait_imp:>+11.1f}%")

    print(f"  {'Max Lane Queue':<32} "
          f"{fixed['max_lane_queue']:>11.1f} "
          f"{ai['max_lane_queue']:>11.1f} "
          f"{lane_q_imp:>+11.1f}%")

    print(f"  {'Max Total Queue':<32} "
          f"{fixed['max_total_queue']:>11.1f} "
          f"{ai['max_total_queue']:>11.1f} "
          f"{total_q_imp:>+11.1f}%")

    print(f"  {'Vehicles Serviced':<32} "
          f"{fixed['vehicles_served']:>11.0f} "
          f"{ai['vehicles_served']:>11.0f} "
          f"{'+0.0%':>12}")

    print("=" * 72)

    print("\n  ℹ️  METRIC CLARIFICATION:")
    print("     • Avg Wait Time / Vehicle : Average delay experienced per individual vehicle (realistic: 20-45s).")
    print("     • System Total Wait / Step: Instantaneous sum of waiting time across all 4 roads combined.")
    print("       (Previously mislabeled as 'Avg Wait Time', which showed multi-minute aggregate values).")

    if veh_wait_imp > 0:
        print(f"\n  ✅ AI reduced average vehicle wait time by {veh_wait_imp:.1f}% "
              f"(from {fixed['veh_avg_wait']:.1f}s down to {ai['veh_avg_wait']:.1f}s per vehicle)!")
        print(f"  ✅ AI reduced overall system wait time by {sys_wait_imp:.1f}%!")
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