"""
OpenRouter Models Helper

This module provides utilities for working with OpenRouter models,
including model discovery, filtering, and cost calculations.
"""

from typing import List, Dict, Any, Optional
from app.schemas.schemas import ModelInfo


# Recommended models for image manipulation tasks
# Vision models (text+image->text) for viewing/analysis:
RECOMMENDED_MODELS = [
    "qwen/qwen3-vl-8b-instruct",                        # Best value - cheapest vision model ($0.08/$0.50 per 1M tokens)
    "google/gemini-2.5-flash-lite-preview-09-2025",    # Google's low-cost option ($0.10/$0.40 per 1M tokens)
    "qwen/qwen3-vl-30b-a3b-instruct",                  # Better quality, still affordable ($0.15/$0.60 per 1M tokens)
    "allenai/molmo-2-8b",                              # Video support, low cost ($0.20/$0.20 per 1M tokens)
    "google/gemini-3-flash-preview",                   # High quality Google option ($0.50/$3.00 per 1M tokens)
    "anthropic/claude-3.5-sonnet",                     # Premium quality, higher cost
]

# Image editing models (text+image->text+image) for object removal, inpainting:
IMAGE_EDITING_MODELS = [
    "google/gemini-2.5-flash-image",                   # Low cost editing ($0.30/$2.50 per 1M tokens)
    "openai/gpt-5-image-mini",                         # Mid-range editing ($2.50/$2.00 per 1M tokens)
    "google/gemini-3-pro-image-preview",               # High quality editing ($2.00/$12.00 per 1M tokens)
    "google/gemini-4-pro-image-preview",               # Latest Gemini 4 with image editing
    "openai/gpt-5-image",                              # Premium editing ($10.00/$10.00 per 1M tokens)
]

# Default model - cheapest vision-capable model
DEFAULT_MODEL = "qwen/qwen3-vl-8b-instruct"


def parse_model_data(model_data: Dict[str, Any]) -> ModelInfo:
    """
    Parse model data from OpenRouter API into ModelInfo schema
    
    Args:
        model_data: Raw model data from OpenRouter API
        
    Returns:
        ModelInfo object
    """
    pricing_data = model_data.get("pricing", {})
    
    # Extract pricing information
    pricing = None
    if pricing_data:
        pricing = {
            "prompt": float(pricing_data.get("prompt", 0)),
            "completion": float(pricing_data.get("completion", 0)),
        }
    
    return ModelInfo(
        id=model_data.get("id", ""),
        name=model_data.get("name", ""),
        description=model_data.get("description"),
        context_length=model_data.get("context_length"),
        pricing=pricing,
    )


def filter_models_for_chat(models: List[Dict[str, Any]]) -> List[ModelInfo]:
    """
    Filter models suitable for chat/text generation
    
    Args:
        models: List of raw model data from OpenRouter
        
    Returns:
        List of ModelInfo objects suitable for chat
    """
    filtered = []
    
    for model_data in models:
        model_id = model_data.get("id", "")
        
        # Filter out non-chat models (image gen, embedding, etc.)
        if any(skip in model_id.lower() for skip in ["dall-e", "whisper", "embedding", "tts"]):
            continue
        
        # Filter out deprecated models
        if model_data.get("deprecated", False):
            continue
        
        filtered.append(parse_model_data(model_data))
    
    return filtered


def search_models(
    models: List[ModelInfo],
    query: str,
    limit: int = 20
) -> List[ModelInfo]:
    """
    Search models by query string
    
    Args:
        models: List of ModelInfo objects
        query: Search query
        limit: Maximum results to return
        
    Returns:
        Filtered list of models matching query
    """
    query_lower = query.lower()
    
    results = [
        model for model in models
        if query_lower in model.id.lower() or
           query_lower in (model.name or "").lower() or
           query_lower in (model.description or "").lower()
    ]
    
    return results[:limit]


def get_recommended_models(all_models: List[ModelInfo]) -> List[ModelInfo]:
    """
    Get recommended models for image manipulation
    
    Args:
        all_models: List of all available models
        
    Returns:
        List of recommended models
    """
    recommended = []
    
    for model_id in RECOMMENDED_MODELS:
        for model in all_models:
            if model.id == model_id:
                recommended.append(model)
                break
    
    return recommended


def is_image_editing_model(model_id: str) -> bool:
    """
    Check if a model supports image editing/generation capabilities
    
    Args:
        model_id: Model identifier (e.g., "google/gemini-4-pro-image-preview")
        
    Returns:
        True if model can generate/edit images, False otherwise
    """
    # Check if explicitly listed in IMAGE_EDITING_MODELS
    if model_id in IMAGE_EDITING_MODELS:
        return True
    
    # Auto-detect based on model name patterns
    model_lower = model_id.lower()
    
    # Image editing indicators in model names
    image_indicators = [
        "-image",           # e.g., "gemini-4-pro-image-preview"
        "/image-",          # e.g., "provider/image-model"
        "image-generation", # Explicit image generation models
        "imagen",           # Google's Imagen models
        "dall-e",          # OpenAI's DALL-E models (though these are usually separate)
    ]
    
    # Check if model name contains image editing indicators
    for indicator in image_indicators:
        if indicator in model_lower:
            return True
    
    return False


def calculate_conversation_cost(
    messages: List[Dict[str, Any]],
    model_pricing: Optional[Dict[str, float]] = None
) -> float:
    """
    Calculate total cost for a conversation
    
    Args:
        messages: List of message dicts with 'tokens_used' and 'cost'
        model_pricing: Optional pricing data (prompt/completion costs)
        
    Returns:
        Total cost in USD
    """
    total_cost = 0.0
    
    for message in messages:
        # If message has cost, use it
        if message.get("cost") is not None:
            total_cost += float(message["cost"])
        # Otherwise estimate from tokens and pricing
        elif message.get("tokens_used") and model_pricing:
            tokens = message["tokens_used"]
            # Rough estimate: 50% prompt, 50% completion
            cost = (tokens / 2) * (model_pricing.get("prompt", 0) / 1_000_000)
            cost += (tokens / 2) * (model_pricing.get("completion", 0) / 1_000_000)
            total_cost += cost
    
    return round(total_cost, 6)
