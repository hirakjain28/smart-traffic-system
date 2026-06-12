# backend/api/websocket/live_feed.py

"""
WEBSOCKET LIVE FEED — Real-time push to dashboard

WHAT IS A WEBSOCKET?
Normal HTTP: client asks → server responds → connection closes
WebSocket:   connection stays OPEN → server can push anytime

This is perfect for live traffic data:
  Every 10 seconds SUMO advances → we push updated data
  Dashboard updates automatically without polling

CONNECTION MANAGER:
  Keeps track of all connected dashboard clients.
  When simulation updates → broadcasts to ALL connected clients.
  Handles clients connecting/disconnecting gracefully.
"""

import json
import asyncio
from typing import List
from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """
    Manages all active WebSocket connections.
    
    Multiple browser tabs can be open simultaneously.
    All of them receive the same live updates.
    """

    def __init__(self):
        # List of all currently connected WebSocket clients
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accepts a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"📡 WebSocket client connected. "
              f"Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Removes a disconnected client."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"📡 WebSocket client disconnected. "
              f"Total: {len(self.active_connections)}")

    async def broadcast(self, data: dict):
        """
        Sends data to ALL connected clients.
        
        If a client has disconnected without proper cleanup,
        we catch the error and remove them from the list.
        """
        if not self.active_connections:
            return

        message     = json.dumps(data)
        dead_clients = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                # Client disconnected unexpectedly
                dead_clients.append(connection)

        # Clean up dead connections
        for dead in dead_clients:
            self.disconnect(dead)

    def broadcast_sync(self, data: dict):
        """
        Synchronous wrapper for broadcast.
        
        The simulation runs in a regular thread (not async).
        This lets it call the async broadcast from a sync context.
        """
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self.broadcast(data))
        except Exception:
            pass
        finally:
            loop.close()


# Global manager instance — shared across the entire application
manager = ConnectionManager()