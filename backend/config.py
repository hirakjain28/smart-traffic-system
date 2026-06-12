# backend/config.py

"""
CONFIGURATION — Central settings for the backend

WHY A CONFIG FILE?
Instead of hardcoding paths and settings everywhere,
we put them all here. Change one thing here → affects the whole system.

We use python-dotenv to load settings from a .env file.
This means sensitive settings (like API keys) never get
committed to git — they stay in .env which is gitignored.
"""

import os
from pathlib import Path

# ── PROJECT ROOT ──────────────────────────────────────────────────────────────
# This finds the project root regardless of where you run the script from
ROOT_DIR = Path(__file__).parent.parent.absolute()

# ── SUMO SETTINGS ─────────────────────────────────────────────────────────────
SUMO_HOME     = os.environ.get("SUMO_HOME", "/usr/share/sumo")
NET_FILE      = str(ROOT_DIR / "simulation/nets/single_intersection/network.net.xml")
ROUTE_FILE    = str(ROOT_DIR / "simulation/nets/single_intersection/routes.rou.xml")
TRAFFIC_LIGHT_ID = "C"

# ── AI MODEL SETTINGS ─────────────────────────────────────────────────────────
# Path to the best trained model
# We scan the models directory and pick the most recent _best model
MODELS_DIR = str(ROOT_DIR / "rl_engine/models")

def get_latest_model_path():
    """
    Scans the models directory and returns the path to the
    most recently trained best model.
    
    Returns None if no model found.
    """
    models_path = Path(MODELS_DIR)
    best_models = sorted(models_path.glob("*_best.zip"))
    if not best_models:
        return None
    return str(best_models[-1]).replace(".zip", "")

# ── SIMULATION SETTINGS ───────────────────────────────────────────────────────
DELTA_TIME  = 10     # seconds between AI decisions
MAX_STEPS   = 360    # steps per episode (360 × 10s = 1 hour)
USE_GUI     = False  # set True to see SUMO window (slow)

# ── API SETTINGS ──────────────────────────────────────────────────────────────
API_HOST = "0.0.0.0"
API_PORT = 8000

# ── DATABASE SETTINGS ─────────────────────────────────────────────────────────
DB_PATH = str(ROOT_DIR / "data/traffic_db.sqlite")

# ── TIMING ────────────────────────────────────────────────────────────────────
# How often (seconds) the background simulation loop runs
SIMULATION_TICK_INTERVAL = 0.1   # 100ms between ticks (10 ticks per second)