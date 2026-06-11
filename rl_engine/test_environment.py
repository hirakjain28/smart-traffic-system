# rl_engine/test_environment.py

"""
TEST ENVIRONMENT

This script manually tests our Gym environment WITHOUT any AI.
We take random actions to verify:
  1. The environment starts correctly (reset works)
  2. Steps run without errors (step works)
  3. State is a proper numpy array of 10 floats
  4. Rewards are calculated and look reasonable
  5. Constraints are working (printed in info)
  6. SUMO closes cleanly (close works)

After this test passes, we know our environment is solid.
THEN we attach the AI agent in Phase 3.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
from rl_engine.environment.traffic_env import TrafficEnv


def test_environment():
    print("=" * 60)
    print("  TESTING TRAFFIC ENVIRONMENT")
    print("=" * 60)

    # Create environment (use_gui=False for speed, set True to watch)
    env = TrafficEnv(use_gui=False, delta_time=10, max_steps=20)

    # ── TEST 1: reset() ───────────────────────────────────────────────────────
    print("\n📋 Test 1: reset()")
    state, info = env.reset()

    print(f"  State shape:  {state.shape}  (should be (10,))")
    print(f"  State dtype:  {state.dtype}  (should be float32)")
    print(f"  State min:    {state.min():.3f}  (should be >= 0.0)")
    print(f"  State max:    {state.max():.3f}  (should be <= 1.0)")
    print(f"  State values: {np.round(state, 3)}")

    assert state.shape == (10,),    "❌ Wrong shape!"
    assert state.dtype == np.float32, "❌ Wrong dtype!"
    assert state.min() >= 0.0,      "❌ State below 0!"
    assert state.max() <= 1.0,      "❌ State above 1!"
    print("  ✅ reset() passed!")

    # ── TEST 2: step() with manual actions ────────────────────────────────────
    print("\n📋 Test 2: step() — running 20 steps with random actions")
    print(f"  {'Step':>4} | {'Action':>6} | {'Reward':>8} | {'TotalWait':>10} | "
          f"{'Phase':>6} | {'Overridden':>10}")
    print("  " + "-" * 60)

    total_reward = 0.0

    for step in range(20):
        # Random action (0 or 1) — simulating untrained agent
        action = env.action_space.sample()

        # Take the step
        new_state, reward, terminated, truncated, info = env.step(action)

        total_reward += reward

        print(f"  {step+1:>4} | {action:>6} | {reward:>8.3f} | "
              f"{info['total_wait']:>10.1f}s | "
              f"{info['current_phase']:>6} | "
              f"{str(info['action_overridden']):>10}")

        # Validate state
        assert new_state.shape == (10,)
        assert new_state.min() >= 0.0
        assert new_state.max() <= 1.0

        if terminated:
            print(f"\n  Episode ended at step {step+1}")
            break

    print(f"\n  Total reward across 20 steps: {total_reward:.3f}")
    print("  ✅ step() passed!")

    # ── TEST 3: constraint working ─────────────────────────────────────────────
    print("\n📋 Test 3: Fairness constraint check")
    print(f"  Constraint info: {env.constraint.get_info()}")
    print("  ✅ Constraints loaded!")

    # ── TEST 4: close() ───────────────────────────────────────────────────────
    print("\n📋 Test 4: close()")
    env.close()
    print("  ✅ SUMO closed cleanly!")

    print("\n" + "=" * 60)
    print("  ALL TESTS PASSED ✅")
    print("=" * 60)


if __name__ == "__main__":
    test_environment()