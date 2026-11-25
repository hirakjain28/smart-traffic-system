# rl_engine/training/evaluate_multi.py

"""
Compares fixed-timer baseline vs multi-agent AI on the 2x2 grid.
This is the only number that actually matters — not the reward value,
but how much better AI is than no AI.
"""

import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

import numpy as np
import traci
from rl_engine.environment.multi_intersection_env import (
    MultiIntersectionEnv, INTERSECTIONS
)
from rl_engine.agents.multi_agent_manager import MultiAgentManager
from rl_engine.environment.signal_program import install_clockwise_program

NET_FILE   = "simulation/nets/grid_2x2/network.net.xml"
ROUTE_FILE = "simulation/nets/grid_2x2/routes.rou.xml"

INCOMING = {
    "A": ["W12A", "N12A", "B2A",  "C2A"],
    "B": ["A2B",  "N22B", "E12B", "D2B"],
    "C": ["A2C",  "W22C", "D2C",  "S12C"],
    "D": ["C2D",  "B2D",  "E22D", "S22D"],
}


def run_fixed_timer(num_episodes=2):
    """Fixed timer: SUMO's default program, no AI."""
    print("\n📊 Running Fixed-Timer Baseline (2x2 grid)...")
    all_waits = []

    for ep in range(num_episodes):
        traci.start(["sumo", "--net-file", NET_FILE,
                     "--route-files", ROUTE_FILE,
                     "--no-step-log", "true",
                     "--waiting-time-memory", "1000",
                     "--time-to-teleport", "-1"])

        for _ in range(5):
            traci.simulationStep()

        total_wait_steps = []
        for step in range(360):
            for _ in range(10):
                traci.simulationStep()

            step_wait = sum(
                traci.edge.getWaitingTime(e)
                for tl in INTERSECTIONS
                for e in INCOMING[tl]
            )
            total_wait_steps.append(step_wait)

        traci.close()
        avg = np.mean(total_wait_steps)
        all_waits.append(avg)
        print(f"   Episode {ep+1}: avg_total_wait={avg:.1f}s")

    return np.mean(all_waits)


def run_ai_agents(model_dir, run_name, num_episodes=2):
    """Multi-agent AI controlling all 4 intersections."""
    print(f"\n🤖 Running Multi-Agent AI...")

    env     = MultiIntersectionEnv(use_gui=False)
    manager = MultiAgentManager.load_all(model_dir, run_name, env)

    all_waits = []

    for ep in range(num_episodes):
        obs  = env.reset()
        done = False
        episode_waits = []

        while not done:
            actions = manager.predict_all(obs, deterministic=True)
            obs, rewards, done, info = env.step(actions)

            step_wait = sum(
                sum(info[tl]["raw_state"]["wait"].values())
                for tl in INTERSECTIONS
            )
            episode_waits.append(step_wait)

        avg = np.mean(episode_waits)
        all_waits.append(avg)
        print(f"   Episode {ep+1}: avg_total_wait={avg:.1f}s")

    env.close()
    return np.mean(all_waits)


if __name__ == "__main__":
    # Find the best multi-agent model
    model_dir = "rl_engine/models"
    best_runs = sorted([
        f.replace("_A.zip", "")
        for f in os.listdir(model_dir)
        if "multi" in f and "_best_A.zip" in f
    ])

    if not best_runs:
        print("❌ No multi-agent model found. Run train_multi.py first.")
        sys.exit(1)

    run_name = best_runs[-1]
    print(f"Using model: {run_name}")

    fixed_wait = run_fixed_timer(num_episodes=2)
    ai_wait    = run_ai_agents(model_dir, run_name, num_episodes=2)

    improvement = (fixed_wait - ai_wait) / fixed_wait * 100

    print("\n" + "=" * 55)
    print(f"  {'Metric':<25} {'Fixed':>12} {'AI':>12}")
    print("  " + "-" * 51)
    print(f"  {'Avg Total Wait (4 junctions)':<25} "
          f"{fixed_wait:>11.1f}s {ai_wait:>11.1f}s")
    print(f"  {'Improvement':<25} {'':>12} {improvement:>+11.1f}%")
    print("=" * 55)

    if improvement > 0:
        print(f"\n  ✅ Multi-agent AI reduced system wait by {improvement:.1f}%!")
    else:
        print(f"\n  ⚠️  Model needs more training episodes.")
        print(f"     Try increasing TOTAL_EPISODES to 300 in train_multi.py")