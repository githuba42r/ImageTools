"""
OpenRouter API Client

This module provides a client for interacting with the OpenRouter.ai API
using the OpenAI SDK for compatibility.
"""

import os
import json
from typing import Optional, Dict, Any, List
from openai import OpenAI
import httpx
from app.core.config import settings


class OpenRouterClient:
    """Client for OpenRouter.ai API using OpenAI SDK"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenRouter client
        
        Args:
            api_key: OpenRouter API key. If None, uses OPENROUTER_API_KEY env var
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key not provided and OPENROUTER_API_KEY not set")
        
        # Initialize OpenAI client with OpenRouter base URL
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )
        
        # HTTP client for non-chat endpoints
        self.http_client = httpx.Client(
            base_url="https://openrouter.ai/api/v1",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": getattr(settings, "APP_URL", "http://localhost:5173"),
                "X-Title": "ImageTools AI Chat",
            }
        )
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "google/gemini-2.0-flash-exp:free",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        modalities: Optional[List[str]] = None,
        image_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Send a chat completion request
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model ID from OpenRouter catalog
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            modalities: Output modalities (e.g., ["image", "text"] for image generation)
            image_config: Image generation config (aspect_ratio, image_size, etc.)
            
        Returns:
            Dict containing response and usage information
        """
        try:
            # Build request parameters
            params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }
            
            if max_tokens is not None:
                params["max_tokens"] = max_tokens
            
            if modalities is not None:
                params["modalities"] = modalities
                
            if image_config is not None:
                params["image_config"] = image_config
            
            response = self.client.chat.completions.create(**params)
            
            # Extract response data
            choice = response.choices[0]
            message_content = choice.message.content
            
            # Debug logging for image generation
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"🖼️  OpenRouter Response Debug:")
            logger.info(f"  - Model: {model}")
            logger.info(f"  - Modalities requested: {modalities}")
            logger.info(f"  - Message type: {type(choice.message)}")
            logger.info(f"  - Message content type: {type(message_content)}")
            
            # Check if message has custom attributes (OpenRouter extensions)
            if hasattr(choice.message, '__dict__'):
                logger.info(f"  - Message __dict__ keys: {choice.message.__dict__.keys()}")
            if hasattr(choice.message, '_images'):
                logger.info(f"  - Found _images private attribute")
            
            # Extract generated images if present
            generated_images = []
            
            # Try multiple formats for image extraction
            # Format 1: OpenAI-style content array with image_url
            if isinstance(message_content, list):
                logger.info(f"  - Content is list with {len(message_content)} items")
                for item in message_content:
                    logger.info(f"    - Item type: {type(item)}, keys: {item.keys() if isinstance(item, dict) else 'N/A'}")
                    if isinstance(item, dict):
                        if item.get('type') == 'image_url' and 'image_url' in item:
                            url = item['image_url'].get('url') if isinstance(item['image_url'], dict) else item['image_url']
                            generated_images.append(url)
                            logger.info(f"    - Found image URL (format 1): {url[:100]}...")
                        elif 'image' in item:
                            generated_images.append(item['image'])
                            logger.info(f"    - Found image (format 1b): {item['image'][:100]}...")
                # If content is a list, extract text for message_content
                text_parts = [item.get('text', '') for item in message_content if isinstance(item, dict) and item.get('type') == 'text']
                if text_parts:
                    message_content = '\n'.join(text_parts)
            
            # Format 2: Direct images attribute on message
            if hasattr(choice.message, 'images') and choice.message.images:
                logger.info(f"  - Found images attribute: {len(choice.message.images)} images")
                for idx, img in enumerate(choice.message.images):
                    logger.info(f"    - Image {idx} type: {type(img)}")
                    logger.info(f"    - Image {idx} attributes: {dir(img)}")
                    
                    # Try different extraction methods
                    extracted = False
                    
                    # Method 1: img.image_url.url
                    if hasattr(img, 'image_url') and hasattr(img.image_url, 'url'):
                        generated_images.append(img.image_url.url)
                        logger.info(f"    - Extracted image URL (method 1): {img.image_url.url[:100]}...")
                        extracted = True
                    # Method 2: img.url
                    elif hasattr(img, 'url'):
                        generated_images.append(img.url)
                        logger.info(f"    - Extracted image URL (method 2): {img.url[:100]}...")
                        extracted = True
                    # Method 3: img as dict
                    elif isinstance(img, dict):
                        if 'url' in img:
                            generated_images.append(img['url'])
                            logger.info(f"    - Extracted image URL (method 3): {img['url'][:100]}...")
                            extracted = True
                        elif 'image_url' in img:
                            url = img['image_url'].get('url') if isinstance(img['image_url'], dict) else img['image_url']
                            generated_images.append(url)
                            logger.info(f"    - Extracted image URL (method 4): {url[:100]}...")
                            extracted = True
                    # Method 5: Direct string
                    elif isinstance(img, str):
                        generated_images.append(img)
                        logger.info(f"    - Extracted image URL (method 5 - direct string): {img[:100]}...")
                        extracted = True
                    
                    if not extracted:
                        logger.warning(f"    ⚠️ Failed to extract image {idx}, trying repr: {repr(img)[:200]}")
                        # Last resort: try to convert to dict
                        if hasattr(img, 'model_dump'):
                            img_dict = img.model_dump()
                            logger.info(f"    - Image dict keys: {img_dict.keys()}")
                            if 'url' in img_dict:
                                generated_images.append(img_dict['url'])
                                logger.info(f"    - Extracted via model_dump: {img_dict['url'][:100]}...")
                            elif 'image_url' in img_dict:
                                url = img_dict['image_url'].get('url') if isinstance(img_dict['image_url'], dict) else img_dict['image_url']
                                generated_images.append(url)
                                logger.info(f"    - Extracted via model_dump (nested): {url[:100]}...")

            
            # Format 3: Raw response dict format
            if hasattr(response, 'model_dump') or hasattr(response, 'dict'):
                raw_dict = response.model_dump() if hasattr(response, 'model_dump') else response.dict()
                logger.info(f"  - Checking raw response dict")
                logger.info(f"  - Raw response keys: {raw_dict.keys()}")
                
                if 'choices' in raw_dict and len(raw_dict['choices']) > 0:
                    choice_dict = raw_dict['choices'][0]
                    logger.info(f"  - Choice keys: {choice_dict.keys()}")
                    
                    if 'message' in choice_dict:
                        msg_dict = choice_dict['message']
                        logger.info(f"  - Message keys: {msg_dict.keys()}")
                        
                        # Check for images in message
                        if 'images' in msg_dict and msg_dict['images']:
                            logger.info(f"  - Found images in message dict: {len(msg_dict['images'])} images")
                            for idx, img_data in enumerate(msg_dict['images']):
                                logger.info(f"    - Image {idx} type: {type(img_data)}, data: {str(img_data)[:200]}")
                                if isinstance(img_data, str):
                                    if img_data not in generated_images:
                                        generated_images.append(img_data)
                                        logger.info(f"    ✓ Extracted image {idx} (string)")
                                elif isinstance(img_data, dict):
                                    url = img_data.get('url') or img_data.get('image_url', {}).get('url') if isinstance(img_data.get('image_url'), dict) else img_data.get('image_url')
                                    if url and url not in generated_images:
                                        generated_images.append(url)
                                        logger.info(f"    ✓ Extracted image {idx} (dict): {url[:100]}...")
                        
                        if 'content' in msg_dict:
                            content = msg_dict['content']
                            if isinstance(content, list):
                                logger.info(f"  - Message content is array with {len(content)} items")
                                for item in content:
                                    if isinstance(item, dict) and item.get('type') == 'image_url':
                                        url = item.get('image_url', {}).get('url') if isinstance(item.get('image_url'), dict) else item.get('image_url')
                                        if url and url not in generated_images:
                                            generated_images.append(url)
                                            logger.info(f"    ✓ Extracted from content array (format 3): {url[:100]}...")
            
            logger.info(f"  - Total images extracted: {len(generated_images)}")
            
            # Extract usage and cost information
            usage = response.usage
            tokens_used = usage.total_tokens if usage else None
            
            # Calculate cost (OpenRouter provides this in response headers in production)
            # For now, we'll estimate based on model pricing
            cost = self._estimate_cost(model, tokens_used) if tokens_used else None
            
            return {
                "content": message_content,
                "tokens_used": tokens_used,
                "cost": cost,
                "finish_reason": choice.finish_reason,
                "model": response.model,
                "images": generated_images,  # List of base64 data URLs
            }
            
        except Exception as e:
            raise Exception(f"OpenRouter API error: {str(e)}")
    
    def get_models(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get available models from OpenRouter
        
        Args:
            search: Optional search query to filter models
            
        Returns:
            List of model information dicts
        """
        try:
            response = self.http_client.get("/models")
            response.raise_for_status()
            
            data = response.json()
            models = data.get("data", [])
            
            # Filter by search query if provided
            if search:
                search_lower = search.lower()
                models = [
                    m for m in models
                    if search_lower in m.get("id", "").lower() or
                       search_lower in m.get("name", "").lower()
                ]
            
            return models
            
        except Exception as e:
            raise Exception(f"Failed to fetch models: {str(e)}")
    
    def _estimate_cost(self, model: str, tokens: int) -> float:
        """
        Estimate cost based on model and token count
        
        This is a rough estimate. In production, OpenRouter provides
        actual cost in response headers.
        
        Args:
            model: Model ID
            tokens: Total tokens used
            
        Returns:
            Estimated cost in USD
        """
        # Cost per 1M tokens (rough estimates)
        pricing = {
            "google/gemini-2.0-flash-exp:free": 0.0,  # Free tier
            "google/gemini-3-flash-preview": 0.00125,  # $1.25 per 1M tokens avg
            "anthropic/claude-3.5-sonnet": 3.0,  # $3 per 1M tokens avg
            "openai/gpt-4-turbo": 10.0,  # $10 per 1M tokens avg
        }
        
        # Default to $1 per 1M tokens if model not found
        cost_per_million = pricing.get(model, 1.0)
        
        return (tokens / 1_000_000) * cost_per_million
    
    def __del__(self):
        """Close HTTP client on cleanup"""
        if hasattr(self, 'http_client'):
            self.http_client.close()
