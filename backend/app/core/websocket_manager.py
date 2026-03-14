"""
WebSocket connection manager for broadcasting events to all connected clients
"""
from fastapi import WebSocket
from typing import Dict, Set
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasts messages"""
    
    def __init__(self):
        # Map of user_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Map of WebSocket -> user_id for reverse lookup
        self.websocket_users: Dict[WebSocket, str] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept and store a new WebSocket connection for a user"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        self.websocket_users[websocket] = user_id
        
        logger.info(f"WebSocket connected for user {user_id}. Total connections: {len(self.active_connections[user_id])}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        user_id = self.websocket_users.get(websocket)
        if user_id:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                
                # Clean up empty user sets
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            del self.websocket_users[websocket]
            logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def broadcast_to_session(self, user_id: str, message: dict):
        """Broadcast a message to all connections for a specific user"""
        logger.info(f"[WS BROADCAST] Attempting to broadcast to user '{user_id}'")
        logger.info(f"[WS BROADCAST] Message: {message}")
        logger.info(f"[WS BROADCAST] All active users: {list(self.active_connections.keys())}")
        
        if user_id not in self.active_connections:
            logger.warning(f"[WS BROADCAST] No active connections for user '{user_id}'")
            logger.warning(f"[WS BROADCAST] Available users: {list(self.active_connections.keys())}")
            return
        
        # Copy the set to avoid issues if connections are removed during iteration
        connections = self.active_connections[user_id].copy()
        logger.info(f"[WS BROADCAST] Broadcasting to {len(connections)} connection(s)")
        
        for websocket in connections:
            try:
                await websocket.send_json(message)
                logger.info(f"[WS BROADCAST] Successfully sent message to a connection")
            except Exception as e:
                logger.error(f"[WS BROADCAST] Error broadcasting to websocket: {e}")
                # Remove failed connection
                self.disconnect(websocket)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast a message to all connected clients"""
        for user_id in list(self.active_connections.keys()):
            await self.broadcast_to_session(user_id, message)


# Global connection manager instance
manager = ConnectionManager()
