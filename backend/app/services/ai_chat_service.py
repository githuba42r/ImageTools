"""
AI Chat Service

This module provides the main AI chat functionality including conversation management,
message handling, and integration with OpenRouter API.
"""

import os
import json
import uuid
import re
import base64
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from PIL import Image as PILImage

from app.models.models import Conversation, Message, Image
from app.schemas.schemas import (
    ChatRequest, ChatResponse, AIOperation,
    ConversationResponse, MessageResponse
)
from app.integrations.openrouter.client import OpenRouterClient
from app.integrations.openrouter.models import DEFAULT_MODEL


# System prompt for AI image manipulation
SYSTEM_PROMPT = """You are an image manipulation assistant. When the user asks to modify the image, respond with:
1. A friendly explanation of what you'll do
2. A JSON block with operations to apply

Available operations:
- brightness: {"type": "brightness", "params": {"value": 0.5-2.0}}
- contrast: {"type": "contrast", "params": {"value": 0.5-2.0}}
- saturation: {"type": "saturation", "params": {"value": 0.0-2.0}}
- rotate: {"type": "rotate", "params": {"degrees": -360 to 360}}
- crop: {"type": "crop", "params": {"box": [x1, y1, x2, y2]}}
- resize: {"type": "resize", "params": {"width": int, "height": int}}
- blur: {"type": "blur", "params": {"radius": 1-10}}
- sharpen: {"type": "sharpen", "params": {"factor": 0.5-2.0}}
- sepia: {"type": "sepia", "params": {}}
- grayscale: {"type": "grayscale", "params": {}}

Format your response with explanation text, then add a JSON code block:
```json
{"operations": [...]}
```

Example:
"I'll make the image brighter and more vibrant!
```json
{"operations": [
  {"type": "brightness", "params": {"value": 1.3}},
  {"type": "saturation", "params": {"value": 1.4}}
]}
```
"

If the user asks something that doesn't require image modification, just respond conversationally without a JSON block.
Keep responses concise and friendly.
"""


class AIChatService:
    """Service for AI-powered image manipulation chat"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def send_message(
        self,
        request: ChatRequest,
        api_key: Optional[str] = None
    ) -> ChatResponse:
        """
        Send a message in an AI chat conversation
        
        Args:
            request: Chat request with message, image_id, model, etc.
            api_key: OpenRouter API key (overrides env var)
            
        Returns:
            ChatResponse with AI reply and any operations performed
        """
        # Use provided API key or fall back to env var
        effective_api_key = api_key or request.api_key or os.getenv("OPENROUTER_API_KEY")
        if not effective_api_key:
            raise ValueError("OpenRouter API key required")
        
        # Initialize OpenRouter client
        client = OpenRouterClient(api_key=effective_api_key)
        
        # Get or create conversation
        if request.conversation_id:
            conversation = self.db.query(Conversation).filter(
                Conversation.id == request.conversation_id
            ).first()
            if not conversation:
                raise ValueError(f"Conversation {request.conversation_id} not found")
        else:
            conversation = self._create_conversation(
                request.image_id,
                request.model or DEFAULT_MODEL
            )
        
        # Get image
        image = self.db.query(Image).filter(Image.id == request.image_id).first()
        if not image:
            raise ValueError(f"Image {request.image_id} not found")
        
        # Build message history with image context
        messages = self._build_message_history(conversation, image)
        
        # Add user message
        user_content = request.message
        messages.append({
            "role": "user",
            "content": user_content
        })
        
        # Call OpenRouter API
        response_data = client.chat_completion(
            messages=messages,
            model=conversation.model,
            temperature=0.7,
        )
        
        assistant_content = response_data["content"]
        tokens_used = response_data.get("tokens_used")
        cost = response_data.get("cost", 0.0)
        
        # Store user message
        user_message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            role="user",
            content=user_content,
            tokens_used=None,
            cost=None,
            created_at=datetime.utcnow()
        )
        self.db.add(user_message)
        
        # Store assistant message
        assistant_message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            role="assistant",
            content=assistant_content,
            tokens_used=tokens_used,
            cost=cost,
            created_at=datetime.utcnow()
        )
        self.db.add(assistant_message)
        
        # Update conversation cost
        conversation.total_cost += (cost or 0.0)
        conversation.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(conversation)
        
        # Parse operations from AI response
        operations = self._parse_operations(assistant_content)
        
        return ChatResponse(
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            response=assistant_content,
            operations=operations,
            image_updated=len(operations) > 0,
            new_image_url=f"/api/v1/images/{image.id}/current" if operations else None,
            tokens_used=tokens_used,
            cost=cost,
            total_conversation_cost=conversation.total_cost
        )
    
    def get_conversation(self, conversation_id: str) -> Optional[ConversationResponse]:
        """
        Get conversation with all messages
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            ConversationResponse or None if not found
        """
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            return None
        
        messages = self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).all()
        
        return ConversationResponse(
            id=conversation.id,
            session_id=conversation.session_id,
            image_id=conversation.image_id,
            model=conversation.model,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            total_cost=conversation.total_cost,
            messages=[MessageResponse.from_orm(msg) for msg in messages]
        )
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete conversation and all messages
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            True if deleted, False if not found
        """
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            return False
        
        # Delete messages first (due to foreign key)
        self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).delete()
        
        # Delete conversation
        self.db.delete(conversation)
        self.db.commit()
        
        return True
    
    def get_session_conversations(self, session_id: str) -> List[ConversationResponse]:
        """
        Get all conversations for a session
        
        Args:
            session_id: Session ID
            
        Returns:
            List of ConversationResponse objects
        """
        conversations = self.db.query(Conversation).filter(
            Conversation.session_id == session_id
        ).order_by(Conversation.updated_at.desc()).all()
        
        result = []
        for conv in conversations:
            messages = self.db.query(Message).filter(
                Message.conversation_id == conv.id
            ).order_by(Message.created_at).all()
            
            result.append(ConversationResponse(
                id=conv.id,
                session_id=conv.session_id,
                image_id=conv.image_id,
                model=conv.model,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                total_cost=conv.total_cost,
                messages=[MessageResponse.from_orm(msg) for msg in messages]
            ))
        
        return result
    
    def _create_conversation(self, image_id: str, model: str) -> Conversation:
        """Create a new conversation"""
        # Get image to find session_id
        image = self.db.query(Image).filter(Image.id == image_id).first()
        if not image:
            raise ValueError(f"Image {image_id} not found")
        
        conversation = Conversation(
            id=str(uuid.uuid4()),
            session_id=image.session_id,
            image_id=image_id,
            model=model,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            total_cost=0.0
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        
        return conversation
    
    def _build_message_history(
        self,
        conversation: Conversation,
        image: Image
    ) -> List[Dict[str, Any]]:
        """
        Build message history for API call
        
        Args:
            conversation: Conversation object
            image: Image object
            
        Returns:
            List of message dicts for OpenRouter API
        """
        messages = []
        
        # Add system prompt
        messages.append({
            "role": "system",
            "content": SYSTEM_PROMPT
        })
        
        # Get previous messages
        prev_messages = self.db.query(Message).filter(
            Message.conversation_id == conversation.id
        ).order_by(Message.created_at).all()
        
        # Add conversation history (without images for older messages to save tokens)
        for msg in prev_messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        return messages
    
    def _encode_image_base64(self, image_path: str) -> str:
        """Encode image as base64 for API"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def _parse_operations(self, ai_response: str) -> List[AIOperation]:
        """
        Parse operations from AI response
        
        Args:
            ai_response: AI text response
            
        Returns:
            List of AIOperation objects
        """
        operations = []
        
        # Look for JSON code block
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
        if not json_match:
            # Try without code block markers
            json_match = re.search(r'(\{[^{}]*"operations"[^{}]*\})', ai_response, re.DOTALL)
        
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                ops_list = data.get("operations", [])
                
                for op in ops_list:
                    operations.append(AIOperation(
                        type=op["type"],
                        params=op.get("params", {})
                    ))
            except json.JSONDecodeError:
                # AI didn't return valid JSON, no operations to apply
                pass
        
        return operations
