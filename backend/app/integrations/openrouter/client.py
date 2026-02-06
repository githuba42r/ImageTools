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
    ) -> Dict[str, Any]:
        """
        Send a chat completion request
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model ID from OpenRouter catalog
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Dict containing response and usage information
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            # Extract response data
            choice = response.choices[0]
            message_content = choice.message.content
            
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
