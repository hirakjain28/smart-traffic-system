# rl_engine/environment/__init__.py

# This file makes the 'environment' folder a Python package.
# It allows you to write:
#   from rl_engine.environment.traffic_env import TrafficEnv
# instead of dealing with raw file paths.

# We expose the main environment class so it's easy to import
from .traffic_env import TrafficEnv