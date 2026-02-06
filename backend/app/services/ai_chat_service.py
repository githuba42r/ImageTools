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
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from PIL import Image as PILImage

from app.models.models import Conversation, Message, Image
from app.schemas.schemas import (
    ChatRequest, ChatResponse, AIOperation, ModelRecommendation,
    ConversationResponse, MessageResponse
)
from app.integrations.openrouter.client import OpenRouterClient
from app.integrations.openrouter.models import DEFAULT_MODEL, IMAGE_EDITING_MODELS, is_image_editing_model


# Base system prompt for vision-only models
SYSTEM_PROMPT_VISION = """You are an image manipulation assistant. You can ONLY use the operations listed below. Do NOT suggest operations that are not in this list.

AVAILABLE OPERATIONS (use ONLY these):
1. brightness: Adjust image brightness (0.5 = darker, 1.0 = normal, 2.0 = brighter)
   Example: {"type": "brightness", "params": {"value": 1.3}}

2. contrast: Adjust image contrast (0.5 = low, 1.0 = normal, 2.0 = high)
   Example: {"type": "contrast", "params": {"value": 1.5}}

3. saturation: Adjust color saturation (0.0 = grayscale, 1.0 = normal, 2.0 = vibrant)
   Example: {"type": "saturation", "params": {"value": 1.4}}

4. rotate: Rotate image by degrees (-360 to 360)
   Example: {"type": "rotate", "params": {"degrees": 90}}

5. crop: Crop image to box coordinates [x1, y1, x2, y2]
   Example: {"type": "crop", "params": {"box": [100, 100, 500, 400]}}

6. resize: Resize image to width and height in pixels
   Example: {"type": "resize", "params": {"width": 800, "height": 600}}

7. blur: Blur image (radius: 1-10)
   Example: {"type": "blur", "params": {"radius": 5}}

8. sharpen: Sharpen image (factor: 0.5-2.0)
   Example: {"type": "sharpen", "params": {"factor": 1.5}}

9. sepia: Apply sepia tone effect (no parameters needed)
   Example: {"type": "sepia", "params": {}}

10. grayscale: Convert to grayscale (no parameters needed)
    Example: {"type": "grayscale", "params": {}}

IMPORTANT RULES:
- NEVER suggest operations not in this list (no "remove", "erase", "delete", "add", etc.)
- If user asks for something not possible with these operations, include [MODEL_RECOMMENDATION_NEEDED] in your response
- Always explain what you'll do BEFORE the JSON block
- Keep responses concise and friendly

Response format:
"I'll make the image brighter and more colorful!
```json
{"operations": [
  {"type": "brightness", "params": {"value": 1.3}},
  {"type": "saturation", "params": {"value": 1.4}}
]}
```"

If you receive an impossible request, respond with:
"[MODEL_RECOMMENDATION_NEEDED]
I can't perform that operation with the current model. The operations I support are: brightness, contrast, saturation, blur, sharpen, grayscale, sepia, rotate, resize, and crop.

For advanced image editing like removing objects, erasing backgrounds, or adding elements, you would need to switch to a model with image generation capabilities."
"""

# Enhanced system prompt for image generation/editing models
SYSTEM_PROMPT_IMAGE_EDITING = """You are an advanced AI image manipulation assistant with image generation and editing capabilities.

YOU HAVE TWO WAYS TO EDIT IMAGES:

1. ADVANCED IMAGE EDITING (YOUR PRIMARY CAPABILITY):
   You can directly manipulate images using your native image generation/editing capabilities:
   - Blur or remove specific objects (e.g., "blur the license plate", "remove the person")
   - Selectively edit parts of the image (faces, objects, backgrounds)
   - Erase or replace backgrounds
   - Add or modify elements in the image
   - Inpaint, outpaint, or regenerate portions of the image
   
   For these requests, simply process the image and return the edited version directly.
   Explain what you're doing, then return the edited image.

2. BASIC FILTER OPERATIONS (JSON):
   For simple adjustments, you can use these JSON operations:
   - brightness, contrast, saturation, rotate, crop, resize, blur, sharpen, sepia, grayscale
   
   Use JSON format only for these basic filters:
   ```json
   {"operations": [{"type": "brightness", "params": {"value": 1.3}}]}
   ```

IMPORTANT:
- For requests involving specific objects, regions, or advanced editing: USE YOUR IMAGE EDITING CAPABILITIES (return edited image)
- For simple filters like "make it brighter" or "rotate 90 degrees": USE JSON OPERATIONS
- Always explain what you're doing before editing
- Be concise and friendly
- If asked to blur a license plate, face, or specific object: PROCESS THE IMAGE DIRECTLY and return the edited version
"""


def get_system_prompt(model_id: str) -> str:
    """
    Get appropriate system prompt based on model capabilities
    
    Args:
        model_id: Model identifier
        
    Returns:
        System prompt string
    """
    if is_image_editing_model(model_id):
        return SYSTEM_PROMPT_IMAGE_EDITING
    else:
        return SYSTEM_PROMPT_VISION


class AIChatService:
    """Service for AI-powered image manipulation chat"""
    
    def __init__(self, db: AsyncSession):
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
            result = await self.db.execute(
                select(Conversation).where(Conversation.id == request.conversation_id)
            )
            conversation = result.scalar_one_or_none()
            if not conversation:
                raise ValueError(f"Conversation {request.conversation_id} not found")
            
            # Debug logging for model switching
            logger.info(f"🔍 Model Switching Debug:")
            logger.info(f"  - Request model: {request.model}")
            logger.info(f"  - Conversation model (before): {conversation.model}")
            logger.info(f"  - Models match: {request.model == conversation.model}")
            
            # Update conversation model if a new model is specified in the request
            if request.model and request.model != conversation.model:
                logger.info(f"  - Updating conversation model to: {request.model}")
                conversation.model = request.model
                conversation.updated_at = datetime.utcnow()
                await self.db.commit()
                await self.db.refresh(conversation)
                logger.info(f"  - Conversation model (after update): {conversation.model}")
            else:
                logger.info(f"  - No model update needed")
        else:
            conversation = await self._create_conversation(
                request.image_id,
                request.model or DEFAULT_MODEL
            )
        
        # Get image
        result = await self.db.execute(
            select(Image).where(Image.id == request.image_id)
        )
        image = result.scalar_one_or_none()
        if not image:
            raise ValueError(f"Image {request.image_id} not found")
        
        # Build message history with image context
        messages = await self._build_message_history(conversation, image)
        
        # Add user message with image for image-editing models
        user_content = request.message
        
        # Check if this is an image-editing model using smart detection
        is_image_editing = is_image_editing_model(conversation.model)
        
        if is_image_editing:
            # For image editing models, include the current image
            image_base64 = self._encode_image_base64(image.current_path)
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_content
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            })
        else:
            # For vision-only models, just send text
            messages.append({
                "role": "user",
                "content": user_content
            })
        
        # Use the current conversation model (which may have been just updated)
        current_model = conversation.model
        
        logger.info(f"  - Model being used for OpenRouter API call: {current_model}")
        logger.info(f"  - Is image editing model: {is_image_editing}")
        logger.info(f"  - Image included in request: {is_image_editing}")
        
        # Call OpenRouter API
        if is_image_editing:
            # Image editing models can output images
            response_data = client.chat_completion(
                messages=messages,
                model=current_model,
                temperature=0.7,
                modalities=["image", "text"],
            )
        else:
            # Regular vision models only output text
            response_data = client.chat_completion(
                messages=messages,
                model=current_model,
                temperature=0.7,
            )
        
        assistant_content = response_data["content"]
        tokens_used = response_data.get("tokens_used")
        cost = response_data.get("cost", 0.0)
        generated_images = response_data.get("images", [])
        
        # Log image generation status
        logger.info(f"📊 AI Chat Response Summary:")
        logger.info(f"  - Model used: {current_model}")
        logger.info(f"  - Is image editing model: {is_image_editing}")
        logger.info(f"  - Response length: {len(assistant_content) if assistant_content else 0} chars")
        logger.info(f"  - Generated images count: {len(generated_images)}")
        if generated_images:
            for idx, img_url in enumerate(generated_images):
                logger.info(f"    - Image {idx+1}: {img_url[:100]}...")
        
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
        conversation.total_cost = float(conversation.total_cost) + (cost or 0.0)
        conversation.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(conversation)
        
        # Handle generated/edited images
        image_updated = False
        if generated_images:
            # Save the first generated image to replace the current image
            image_updated = await self._save_generated_image(image, generated_images[0])
        
        # Parse operations from AI response
        operations = self._parse_operations(assistant_content)
        
        # Check if model recommendations are needed
        model_recommendations = []
        if self._detect_model_recommendation_needed(assistant_content):
            model_recommendations = await self._generate_model_recommendations()
            # Clean up the response text by removing the marker
            assistant_content = assistant_content.replace("[MODEL_RECOMMENDATION_NEEDED]", "").strip()
        
        return ChatResponse(
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            response=assistant_content,
            operations=operations,
            model_recommendations=model_recommendations,
            image_updated=image_updated or len(operations) > 0,
            new_image_url=f"/api/v1/images/{image.id}/current?t={int(datetime.utcnow().timestamp() * 1000)}" if (image_updated or operations) else None,
            tokens_used=tokens_used,
            cost=cost,
            total_conversation_cost=conversation.total_cost
        )
    
    async def get_conversation(self, conversation_id: str) -> Optional[ConversationResponse]:
        """
        Get conversation with all messages
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            ConversationResponse or None if not found
        """
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return None
        
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        messages = result.scalars().all()
        
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
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete conversation and all messages
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            True if deleted, False if not found
        """
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return False
        
        # Delete messages first (due to foreign key)
        await self.db.execute(
            delete(Message).where(Message.conversation_id == conversation_id)
        )
        
        # Delete conversation
        await self.db.delete(conversation)
        await self.db.commit()
        
        return True
    
    async def get_session_conversations(self, session_id: str) -> List[ConversationResponse]:
        """
        Get all conversations for a session
        
        Args:
            session_id: Session ID
            
        Returns:
            List of ConversationResponse objects
        """
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.session_id == session_id)
            .order_by(Conversation.updated_at.desc())
        )
        conversations = result.scalars().all()
        
        response_list = []
        for conv in conversations:
            result = await self.db.execute(
                select(Message)
                .where(Message.conversation_id == conv.id)
                .order_by(Message.created_at)
            )
            messages = result.scalars().all()
            
            response_list.append(ConversationResponse(
                id=conv.id,
                session_id=conv.session_id,
                image_id=conv.image_id,
                model=conv.model,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                total_cost=conv.total_cost,
                messages=[MessageResponse.from_orm(msg) for msg in messages]
            ))
        
        return response_list
    
    async def _create_conversation(self, image_id: str, model: str) -> Conversation:
        """Create a new conversation"""
        # Get image to find session_id
        result = await self.db.execute(
            select(Image).where(Image.id == image_id)
        )
        image = result.scalar_one_or_none()
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
        await self.db.commit()
        await self.db.refresh(conversation)
        
        return conversation
    
    async def _build_message_history(
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
        
        # Add system prompt based on model capabilities
        system_prompt = get_system_prompt(conversation.model)
        messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        # Get previous messages
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at)
        )
        prev_messages = result.scalars().all()
        
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
            List of AIOperation objects (only valid operations)
        """
        # Valid operation types
        VALID_OPERATIONS = {
            'brightness', 'contrast', 'saturation', 'rotate', 
            'crop', 'resize', 'blur', 'sharpen', 'sepia', 'grayscale'
        }
        
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
                    op_type = op.get("type", "")
                    
                    # Only include valid operations
                    if op_type in VALID_OPERATIONS:
                        operations.append(AIOperation(
                            type=op_type,
                            params=op.get("params", {})
                        ))
                    else:
                        # Log invalid operation for debugging
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"AI suggested invalid operation: {op_type}. Skipping.")
                        
            except json.JSONDecodeError:
                # AI didn't return valid JSON, no operations to apply
                pass
        
        return operations
    
    def _detect_model_recommendation_needed(self, ai_response: str) -> bool:
        """
        Check if AI response indicates model recommendation is needed
        
        Args:
            ai_response: AI text response
            
        Returns:
            True if model recommendation marker is present or AI mentions limitations
        """
        # Check for explicit marker
        if "[MODEL_RECOMMENDATION_NEEDED]" in ai_response:
            return True
        
        # Fallback: Detect if AI is explaining it can't do something
        response_lower = ai_response.lower()
        limitation_phrases = [
            "can't perform",
            "cannot perform",
            "can't remove",
            "cannot remove",
            "can't erase",
            "cannot erase",
            "can't add",
            "cannot add",
            "don't support",
            "do not support",
            "not possible with these operations",
            "would need to switch",
            "need a model with",
            "image generation capabilities",
            "advanced image editing"
        ]
        
        # If AI mentions limitations and doesn't have operations, recommend models
        has_limitation = any(phrase in response_lower for phrase in limitation_phrases)
        has_no_operations = "```json" not in ai_response or '"operations": []' in ai_response
        
        return has_limitation and has_no_operations
    
    async def _generate_model_recommendations(self) -> List[ModelRecommendation]:
        """
        Generate structured model recommendations for image editing
        
        Returns:
            List of ModelRecommendation objects for image editing capable models
        """
        # Fetch model data from OpenRouter API to get current pricing
        # For now, return hardcoded recommendations with pricing info
        recommendations = [
            ModelRecommendation(
                model_id="google/gemini-2.5-flash-image",
                model_name="Gemini 2.5 Flash Image",
                reason="Best for low-cost image editing",
                capabilities=[
                    "Remove objects from images",
                    "Erase backgrounds",
                    "Add or modify elements",
                    "Image generation and editing"
                ],
                cost_prompt=0.30,
                cost_completion=2.50,
                context_length=1048576
            ),
            ModelRecommendation(
                model_id="openai/gpt-5-image-mini",
                model_name="GPT-5 Image Mini",
                reason="Balanced quality and cost for image editing",
                capabilities=[
                    "Advanced object removal",
                    "Background replacement",
                    "Complex image modifications",
                    "High-quality image generation"
                ],
                cost_prompt=2.50,
                cost_completion=2.00,
                context_length=128000
            ),
            ModelRecommendation(
                model_id="google/gemini-3-pro-image-preview",
                model_name="Gemini 3 Pro Image",
                reason="Highest quality image editing",
                capabilities=[
                    "Professional-grade object removal",
                    "Complex scene manipulation",
                    "Multi-object editing",
                    "Premium image generation"
                ],
                cost_prompt=2.00,
                cost_completion=12.00,
                context_length=2097152
            )
        ]
        
        return recommendations
    
    async def _save_generated_image(self, image: Image, base64_image_url: str) -> bool:
        """
        Save a generated image from base64 data URL to storage
        
        Args:
            image: Image record to update
            base64_image_url: Base64 data URL (e.g., "data:image/png;base64,...")
            
        Returns:
            True if image was saved successfully
        """
        try:
            import os
            from pathlib import Path
            from app.core.config import settings
            from app.services.image_service import ImageService
            
            logger.info(f"💾 Saving generated image:")
            logger.info(f"  - Image ID: {image.id}")
            logger.info(f"  - Data URL prefix: {base64_image_url[:100]}...")
            
            # Parse base64 data URL
            if not base64_image_url.startswith("data:"):
                logger.error(f"❌ Invalid image data URL format: {base64_image_url[:50]}")
                return False
            
            # Extract mime type and base64 data
            header, base64_data = base64_image_url.split(",", 1)
            logger.info(f"  - Header: {header}")
            logger.info(f"  - Base64 data length: {len(base64_data)} chars")
            
            # Decode base64 image
            image_bytes = base64.b64decode(base64_data)
            logger.info(f"  - Decoded image size: {len(image_bytes)} bytes")
            
            # Determine file extension from mime type
            if "png" in header.lower():
                ext = ".png"
            elif "jpeg" in header.lower() or "jpg" in header.lower():
                ext = ".jpg"
            elif "webp" in header.lower():
                ext = ".webp"
            else:
                ext = ".png"  # Default to PNG
            
            # Generate output path
            output_path = os.path.join(
                settings.STORAGE_PATH,
                f"{image.id}_ai_edited_{uuid.uuid4()}{ext}"
            )
            logger.info(f"  - Output path: {output_path}")
            
            # Save image file
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            logger.info(f"  ✓ File written to disk")
            
            # Open image to get dimensions
            with PILImage.open(output_path) as img:
                new_width, new_height = img.size
                img_format = img.format or "PNG"
            logger.info(f"  - Dimensions: {new_width}x{new_height}, Format: {img_format}")
            
            # Get file size
            new_size = os.path.getsize(output_path)
            
            # Create history entry
            from app.models.models import History
            history_entry = History(
                id=str(uuid.uuid4()),
                image_id=image.id,
                operation_type="ai_edit",
                operation_params=json.dumps({"type": "ai_image_generation"}),
                input_path=image.current_path,
                output_path=output_path,
                file_size=new_size,
                sequence=await self._get_next_sequence(image.id)
            )
            self.db.add(history_entry)
            
            # Update image record
            image.current_path = output_path
            image.current_size = new_size
            image.width = new_width
            image.height = new_height
            image.format = img_format
            
            await self.db.commit()
            await self.db.refresh(image)
            logger.info(f"  ✓ Database updated")
            
            # Recreate thumbnail
            if image.thumbnail_path and os.path.exists(image.thumbnail_path):
                os.remove(image.thumbnail_path)
            thumbnail_path = os.path.join(settings.STORAGE_PATH, f"{image.id}_thumb{ext}")
            ImageService._create_thumbnail(output_path, thumbnail_path)
            image.thumbnail_path = thumbnail_path
            await self.db.commit()
            
            logger.info(f"✅ Successfully saved AI-generated image: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save generated image: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def _get_next_sequence(self, image_id: str) -> int:
        """Get next sequence number for history."""
        from app.models.models import History
        result = await self.db.execute(
            select(History)
            .where(History.image_id == image_id)
            .order_by(History.sequence.desc())
        )
        last_entry = result.scalars().first()
        return (last_entry.sequence + 1) if last_entry else 1
