"""
AI Chat Endpoints

This module provides REST API endpoints for AI-powered image manipulation chat.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.services.ai_chat_service import AIChatService
from app.schemas.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationResponse
)

router = APIRouter(tags=["AI Chat"])


@router.post("/send", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Send a message in an AI chat conversation
    
    - **message**: User's message/request
    - **image_id**: ID of the image to manipulate
    - **conversation_id**: Optional - continue existing conversation
    - **model**: Optional - AI model to use (defaults to gemini-2.0-flash-exp:free)
    - **api_key**: Optional - OpenRouter API key (can also use OPENROUTER_API_KEY env var)
    
    Returns AI response with any image operations to apply
    """
    try:
        service = AIChatService(db)
        response = await service.send_message(request)
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat error: {str(e)}"
        )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a conversation with all messages
    
    - **conversation_id**: ID of the conversation
    
    Returns conversation details and message history
    """
    service = AIChatService(db)
    conversation = service.get_conversation(conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )
    
    return conversation


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a conversation and all its messages
    
    - **conversation_id**: ID of the conversation
    
    Returns success status
    """
    service = AIChatService(db)
    deleted = service.delete_conversation(conversation_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )
    
    return {"success": True, "message": "Conversation deleted"}


@router.get("/sessions/{session_id}/conversations", response_model=List[ConversationResponse])
def get_session_conversations(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all conversations for a session
    
    - **session_id**: ID of the session
    
    Returns list of conversations with messages
    """
    service = AIChatService(db)
    conversations = service.get_session_conversations(session_id)
    return conversations
