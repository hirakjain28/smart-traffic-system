# rl_engine/training/train.py

"""
MAIN TRAINING SCRIPT

This is the file you run to train the DQN agent.
It orchestrates everything:
  1. Creates the environment
  2. Builds the DQN agent
  3. Attaches callbacks (logging, saving)
  4. Runs training for N timesteps
  5. Saves the final model

WHAT IS A TIMESTEP vs AN EPISODE?
  Timestep = one call to env.step() = 10 seconds of simulated traffic
  Episode  = full simulation run = 360 timesteps = 1 hour of traffic
  
  total_timesteps=50_000 means:
  50,000 steps ÷ 360 steps/episode ≈ 138 episodes of training
  138 episodes × 1 hour each = 138 simulated hours of traffic

HOW LONG DOES TRAINING TAKE?
  On a modern CPU: ~15-30 minutes for 50,000 steps
  On GPU: ~5-10 minutes
  
  We can monitor progress via the callback prints every 5 episodes.

TRAINING PHASES (based on epsilon):
  Steps 0-15,000:     Exploring  (ε: 1.0 → 0.1)  random decisions
  Steps 15,000-50,000: Exploiting (ε: 0.1 → 0.05) learned decisions
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from datetime import datetime
from rl_engine.environment.traffic_env import TrafficEnv
from rl_engine.agents.dqn_agent import build_dqn_agent
from rl_engine.training.callbacks import TrafficTrainingCallback


# ── TRAINING CONFIGURATION ────────────────────────────────────────────────────
TOTAL_TIMESTEPS = 50_000   # Total training steps
                            # Increase to 200,000 for better results later

LOG_DIR    = "data/logs"
MODEL_DIR  = "rl_engine/models"
# ─────────────────────────────────────────────────────────────────────────────


def train():
    """
    Main training function.
    Creates environment → builds agent → trains → saves model.
    """

    # ── GENERATE UNIQUE RUN NAME ──────────────────────────────────────────────
    # Each training run gets a unique name based on timestamp.
    # Lets you compare multiple runs side by side.
    run_name = f"dqn_traffic_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print("=" * 60)
    print(f"  🚦 SMART TRAFFIC — DQN TRAINING")
    print(f"  Run: {run_name}")
    print(f"  Total timesteps: {TOTAL_TIMESTEPS:,}")
    print("=" * 60)

    # ── STEP 1: CREATE ENVIRONMENT ────────────────────────────────────────────
    # use_gui=False → no SUMO window (much faster for training)
    # Set use_gui=True if you want to WATCH the AI train (very slow)
    print("\n🌍 Creating Traffic Environment...")
    env = TrafficEnv(
        use_gui=False,
        delta_time=10,
        max_steps=360
    )
    print("✅ Environment ready")

    # ── STEP 2: BUILD DQN AGENT ───────────────────────────────────────────────
    print("\n🧠 Building DQN Agent...")
    model = build_dqn_agent(env, tensorboard_log=LOG_DIR)

    # ── STEP 3: CREATE CALLBACK ───────────────────────────────────────────────
    print("\n📝 Setting up training callbacks...")
    callback = TrafficTrainingCallback(
        log_dir=LOG_DIR,
        model_dir=MODEL_DIR,
        run_name=run_name,
        print_freq=5,
    )

    # ── STEP 4: TRAIN ─────────────────────────────────────────────────────────
    print(f"\n🏋️  Starting training for {TOTAL_TIMESTEPS:,} timesteps...")
    print("  (Progress printed every 5 episodes)\n")
    print(f"  {'Episode':>7} | {'Reward':>8} | {'AvgWait':>8} | "
          f"{'Switches':>8} | {'ε':>6}")
    print("  " + "-" * 50)

    model.learn(
        total_timesteps=TOTAL_TIMESTEPS,
        callback=callback,
        progress_bar=True,     # shows a tqdm progress bar
    )

    # ── STEP 5: SAVE FINAL MODEL ──────────────────────────────────────────────
    final_model_path = os.path.join(MODEL_DIR, f"{run_name}_final")
    model.save(final_model_path)
    print(f"\n💾 Final model saved: {final_model_path}.zip")

    # ── DONE ──────────────────────────────────────────────────────────────────
    env.close()

    print(f"\n✅ Training complete!")
    print(f"   Best model:  {MODEL_DIR}/{run_name}_best.zip")
    print(f"   Final model: {final_model_path}.zip")
    print(f"   Logs:        {LOG_DIR}/{run_name}.csv")
    print(f"   Plot:        {LOG_DIR}/{run_name}_plot.png")

    return run_name


if __name__ == "__main__":
    train()