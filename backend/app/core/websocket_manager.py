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
        # Map of session_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Map of WebSocket -> session_id for reverse lookup
        self.websocket_sessions: Dict[WebSocket, str] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and store a new WebSocket connection for a session"""
        await websocket.accept()
        
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        
        self.active_connections[session_id].add(websocket)
        self.websocket_sessions[websocket] = session_id
        
        logger.info(f"WebSocket connected for session {session_id}. Total connections: {len(self.active_connections[session_id])}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        session_id = self.websocket_sessions.get(websocket)
        if session_id:
            if session_id in self.active_connections:
                self.active_connections[session_id].discard(websocket)
                
                # Clean up empty session sets
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]
            
            del self.websocket_sessions[websocket]
            logger.info(f"WebSocket disconnected for session {session_id}")
    
    async def broadcast_to_session(self, session_id: str, message: dict):
        """Broadcast a message to all connections for a specific session"""
        logger.info(f"[WS BROADCAST] Attempting to broadcast to session '{session_id}'")
        logger.info(f"[WS BROADCAST] Message: {message}")
        logger.info(f"[WS BROADCAST] All active sessions: {list(self.active_connections.keys())}")
        
        if session_id not in self.active_connections:
            logger.warning(f"[WS BROADCAST] No active connections for session '{session_id}'")
            logger.warning(f"[WS BROADCAST] Available sessions: {list(self.active_connections.keys())}")
            return
        
        # Copy the set to avoid issues if connections are removed during iteration
        connections = self.active_connections[session_id].copy()
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
        for session_id in list(self.active_connections.keys()):
            await self.broadcast_to_session(session_id, message)


# Global connection manager instance
manager = ConnectionManager()
