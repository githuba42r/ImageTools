# WebSocket Architecture for ImageTools

## Overview

This document outlines the proposed WebSocket architecture for real-time features in ImageTools, including:
- Real-time image upload notifications (from Android App, Browser Addon)
- Connection status monitoring
- Live progress updates for long-running operations

## Current Status

**Implemented:**
- HTTP REST API for all operations
- Periodic health check polling (30s interval with exponential backoff)
- Offline detection via failed API requests

**Planned:**
- WebSocket connections for real-time features
- Push notifications for external uploads
- Live progress tracking

## Architecture Design

### 1. Backend WebSocket Setup (FastAPI + WebSockets)

#### Dependencies
```bash
# Already included in FastAPI
websockets
```

#### WebSocket Endpoint Structure
```python
# backend/app/api/v1/endpoints/websocket.py

from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
import json

class ConnectionManager:
    """Manages WebSocket connections per session"""
    def __init__(self):
        # session_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
    
    async def send_to_session(self, session_id: str, message: dict):
        """Send message to all connections for a session"""
        if session_id in self.active_connections:
            dead_connections = set()
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_json(message)
                except:
                    dead_connections.add(connection)
            
            # Clean up dead connections
            for conn in dead_connections:
                self.disconnect(conn, session_id)

manager = ConnectionManager()

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    # Validate session exists
    session = await validate_session(session_id, db)
    if not session:
        await websocket.close(code=4004, reason="Invalid session")
        return
    
    await manager.connect(websocket, session_id)
    
    try:
        while True:
            # Keep connection alive with ping/pong
            data = await websocket.receive_text()
            
            if data == "ping":
                await websocket.send_text("pong")
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
```

#### Message Types

```python
# Event types sent from backend to frontend
class WSEventType:
    # Image events
    IMAGE_UPLOADED = "image.uploaded"
    IMAGE_UPDATED = "image.updated"
    IMAGE_DELETED = "image.deleted"
    
    # Operation progress
    OPERATION_STARTED = "operation.started"
    OPERATION_PROGRESS = "operation.progress"
    OPERATION_COMPLETED = "operation.completed"
    OPERATION_FAILED = "operation.failed"
    
    # System events
    SESSION_EXPIRING = "session.expiring"
    CONNECTION_STATUS = "connection.status"

# Example message formats
{
    "type": "image.uploaded",
    "timestamp": "2026-02-07T12:34:56Z",
    "data": {
        "image_id": "uuid-here",
        "filename": "photo.jpg",
        "source": "android_app",  # or "browser_addon", "web"
        "thumbnail_url": "/api/v1/images/uuid/thumbnail"
    }
}

{
    "type": "operation.progress",
    "timestamp": "2026-02-07T12:34:56Z",
    "data": {
        "operation_id": "op-uuid",
        "operation_type": "bulk_compress",
        "progress": 45,  # percentage
        "current": 9,
        "total": 20,
        "message": "Compressing image 9 of 20..."
    }
}
```

### 2. Frontend WebSocket Client

#### WebSocket Service
```javascript
// frontend/src/services/websocketService.js

class WebSocketService {
  constructor() {
    this.ws = null;
    this.sessionId = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000; // Start with 1 second
    this.messageHandlers = new Map();
    this.isConnecting = false;
    this.isConnected = false;
  }
  
  connect(sessionId) {
    if (this.isConnecting || this.isConnected) {
      return;
    }
    
    this.sessionId = sessionId;
    this.isConnecting = true;
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/${sessionId}`;
    
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onopen = () => {
      console.log('[WebSocket] Connected');
      this.isConnected = true;
      this.isConnecting = false;
      this.reconnectAttempts = 0;
      this.reconnectDelay = 1000;
      
      // Start heartbeat
      this.startHeartbeat();
    };
    
    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        console.error('[WebSocket] Failed to parse message:', error);
      }
    };
    
    this.ws.onerror = (error) => {
      console.error('[WebSocket] Error:', error);
    };
    
    this.ws.onclose = (event) => {
      console.log('[WebSocket] Disconnected:', event.code, event.reason);
      this.isConnected = false;
      this.isConnecting = false;
      this.stopHeartbeat();
      
      // Attempt reconnection
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.scheduleReconnect();
      }
    };
  }
  
  disconnect() {
    if (this.ws) {
      this.stopHeartbeat();
      this.ws.close();
      this.ws = null;
      this.isConnected = false;
    }
  }
  
  scheduleReconnect() {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    
    setTimeout(() => {
      this.connect(this.sessionId);
    }, delay);
  }
  
  startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send('ping');
      }
    }, 30000); // Every 30 seconds
  }
  
  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }
  
  handleMessage(message) {
    const handlers = this.messageHandlers.get(message.type);
    if (handlers) {
      handlers.forEach(handler => handler(message.data));
    }
    
    // Also call wildcard handlers
    const wildcardHandlers = this.messageHandlers.get('*');
    if (wildcardHandlers) {
      wildcardHandlers.forEach(handler => handler(message));
    }
  }
  
  on(eventType, handler) {
    if (!this.messageHandlers.has(eventType)) {
      this.messageHandlers.set(eventType, new Set());
    }
    this.messageHandlers.get(eventType).add(handler);
  }
  
  off(eventType, handler) {
    const handlers = this.messageHandlers.get(eventType);
    if (handlers) {
      handlers.delete(handler);
    }
  }
}

export const wsService = new WebSocketService();
```

#### Integration in App.vue
```javascript
import { wsService } from './services/websocketService';

onMounted(() => {
  // ... existing code ...
  
  // Connect to WebSocket when session is ready
  if (sessionId.value) {
    wsService.connect(sessionId.value);
    
    // Listen for image uploads
    wsService.on('image.uploaded', (data) => {
      console.log('New image uploaded from external source:', data);
      // Reload images or add to store
      imageStore.loadSessionImages();
      
      // Show notification
      showNotification(`New image uploaded: ${data.filename}`, 'success');
    });
    
    // Listen for operation progress
    wsService.on('operation.progress', (data) => {
      // Update UI with progress
      updateOperationProgress(data);
    });
  }
});

onBeforeUnmount(() => {
  // ... existing code ...
  wsService.disconnect();
});
```

### 3. External Source Integration

#### Android App Upload
```kotlin
// Android app example
class ImageUploadService {
    suspend fun uploadImage(sessionId: String, imageFile: File) {
        val formData = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("session_id", sessionId)
            .addFormDataPart("source", "android_app")
            .addFormDataPart("file", imageFile.name,
                RequestBody.create("image/*".toMediaType(), imageFile)
            )
            .build()
        
        val request = Request.Builder()
            .url("https://imagetools.example.com/api/v1/images")
            .post(formData)
            .build()
        
        val response = client.newCall(request).execute()
        // WebSocket will notify web app automatically
    }
}
```

#### Browser Addon Upload
```javascript
// Browser addon example (Chrome/Firefox)
async function uploadImage(sessionId, imageBlob) {
  const formData = new FormData();
  formData.append('session_id', sessionId);
  formData.append('source', 'browser_addon');
  formData.append('file', imageBlob, 'screenshot.png');
  
  const response = await fetch('https://imagetools.example.com/api/v1/images', {
    method: 'POST',
    body: formData
  });
  
  // WebSocket will notify web app automatically
}
```

### 4. Implementation Phases

#### Phase 1: Basic WebSocket Connection (Optional)
- [ ] Add WebSocket endpoint to backend
- [ ] Create WebSocketService in frontend
- [ ] Integrate with session lifecycle
- [ ] Test connection/reconnection

#### Phase 2: Image Upload Notifications (For External Sources)
- [ ] Modify image upload endpoint to broadcast via WebSocket
- [ ] Add "source" field to image upload API
- [ ] Implement notification UI in frontend
- [ ] Create Android app integration example
- [ ] Create browser addon integration example

#### Phase 3: Operation Progress (Future Enhancement)
- [ ] Add progress tracking for long operations
- [ ] Broadcast progress via WebSocket
- [ ] Update UI with live progress bars
- [ ] Handle operation cancellation

#### Phase 4: Advanced Features (Future)
- [ ] Session expiration warnings
- [ ] Multi-user collaboration notifications
- [ ] Real-time image editing collaboration

## Considerations

### When to Use WebSocket vs Polling

**Use WebSocket when:**
- Real-time updates are critical (< 5 second latency)
- High frequency of updates (multiple per minute)
- Bi-directional communication needed
- Multiple external sources pushing data

**Use Polling when:**
- Updates are infrequent (every 30+ seconds)
- Simple request/response pattern
- Lower complexity requirements
- Better browser compatibility needed

### Current Recommendation

For ImageTools, **continue with polling** for health checks, but **add WebSocket** for:
1. External upload notifications (Android app, browser addon)
2. Future real-time collaboration features

This hybrid approach provides:
- Simple, reliable health monitoring (polling)
- Real-time notifications for user-initiated events (WebSocket)
- Lower server resource usage
- Graceful degradation if WebSocket fails

## Migration Path

1. **Keep current implementation** (polling for health checks) ✅
2. **Add WebSocket support** when external sources are ready
3. **Make WebSocket optional** - app works fine without it
4. **Use feature detection** - fallback to polling if WebSocket unavailable

## Security Considerations

- Validate session ID on WebSocket connection
- Implement message authentication
- Rate limit WebSocket messages
- Close connections for expired sessions
- Use WSS (WebSocket Secure) in production

## Monitoring

- Track WebSocket connection count
- Monitor message throughput
- Alert on high reconnection rates
- Log connection errors for debugging
