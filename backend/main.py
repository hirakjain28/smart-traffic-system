# backend/main.py

"""
FASTAPI APPLICATION — Main entry point

This file:
  1. Creates the FastAPI app
  2. Initializes all services (simulation, RL, database)
  3. Registers all routes
  4. Sets up WebSocket endpoint
  5. Starts the simulation on app startup

LIFESPAN:
  FastAPI uses a "lifespan" context manager to run code
  on startup and shutdown.
  
  On startup:  create DB tables, load AI model, start simulation
  On shutdown: stop simulation cleanly
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.config import API_HOST, API_PORT
from backend.database.db import create_tables
from backend.services.rl_service import RLService
from backend.services.simulation_service import SimulationService
from backend.services.override_service import OverrideService
from backend.api.websocket.live_feed import manager
from backend.api.routes import traffic, signals, override, logs


# ── GLOBAL SERVICE INSTANCES ──────────────────────────────────────────────────
# These are created once and shared across all API routes
rl_service       = None
sim_service      = None
override_service = None
# ─────────────────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup (before yield) and shutdown (after yield).
    
    Startup:
      - Create database tables
      - Load AI model
      - Start simulation thread
    
    Shutdown:
      - Stop simulation cleanly
    """
    global rl_service, sim_service, override_service

    print("\n" + "=" * 50)
    print("  🚦 SMART TRAFFIC BACKEND STARTING")
    print("=" * 50)

    # ── STARTUP ───────────────────────────────────────────────────────────────
    # 1. Create database tables
    create_tables()

    # 2. Load AI model
    print("\n🧠 Loading RL model...")
    rl_service = RLService()

    # 3. Create simulation service
    print("\n🌍 Initializing simulation...")
    sim_service = SimulationService(rl_service)

    # 4. Hook WebSocket broadcast into simulation
    # When simulation updates → broadcast to all WS clients
    sim_service.state.broadcast_callback = manager.broadcast_sync

    # 5. Create override service
    override_service = OverrideService(sim_service)

    # 6. Start simulation in background thread
    sim_service.start()

    print("\n✅ Backend ready!")
    print(f"   API: http://{API_HOST}:{API_PORT}")
    print(f"   Docs: http://{API_HOST}:{API_PORT}/docs")
    print("=" * 50 + "\n")

    yield   # ← Application runs here

    # ── SHUTDOWN ──────────────────────────────────────────────────────────────
    print("\n🛑 Shutting down...")
    sim_service.stop()
    print("✅ Shutdown complete")


# ── CREATE FASTAPI APP ────────────────────────────────────────────────────────
app = FastAPI(
    title="Smart Traffic Management API",
    description="Real-time traffic signal control using reinforcement learning",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS MIDDLEWARE ───────────────────────────────────────────────────────────
# CORS = Cross-Origin Resource Sharing
# Allows the React dashboard (running on port 3000) to call this API (port 8000)
# Without this, the browser blocks the requests for security reasons
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",
                   "http://localhost:5173"],   # React dev server ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── REGISTER ROUTES ───────────────────────────────────────────────────────────
app.include_router(traffic.router)
app.include_router(signals.router)
app.include_router(override.router)
app.include_router(logs.router)


# ── WEBSOCKET ENDPOINT ────────────────────────────────────────────────────────
@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time traffic updates.
    
    The dashboard connects here once and receives live
    updates every time the simulation advances.
    
    Connection lifecycle:
      1. Dashboard connects → manager.connect() called
      2. Simulation updates → manager.broadcast() called
      3. Dashboard receives JSON data → updates UI
      4. Dashboard closes/refreshes → manager.disconnect() called
    """
    await manager.connect(websocket)
    try:
        # Send initial state immediately on connect
        if sim_service:
            snapshot = sim_service.state.get_snapshot()
            import json
            await websocket.send_text(json.dumps({
                "type": "initial_state",
                "data": snapshot,
            }))

        # Keep connection alive — wait for client messages
        # (client can send "ping" to check connection)
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type": "pong"}')

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ── ROOT ENDPOINT ─────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status":  "running",
        "service": "Smart Traffic Management API",
        "version": "1.0.0",
        "endpoints": {
            "traffic":  "/api/traffic/status",
            "signals":  "/api/signals/state",
            "override": "/api/override/phase",
            "logs":     "/api/logs/decisions",
            "websocket":"/ws/live",
            "docs":     "/docs",
        }
    }


# ── RUN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,    # Don't use reload — simulation state would reset
    )