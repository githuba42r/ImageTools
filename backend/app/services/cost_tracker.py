"""
Cost Tracking Service

This module provides cost tracking functionality for AI chat conversations,
including per-message costs, conversation totals, and monthly limits.
"""

from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, extract, select

from app.models.models import Conversation, Message
from app.schemas.schemas import CostSummary


class CostTracker:
    """Service for tracking and managing AI chat costs"""
    
    # Default monthly cost limit (in USD)
    DEFAULT_MONTHLY_LIMIT = 5.00
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_conversation_cost(self, conversation_id: str) -> float:
        """
        Get total cost for a conversation
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Total cost in USD
        """
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        
        return float(conversation.total_cost) if conversation else 0.0
    
    async def get_monthly_cost(self, session_id: str) -> float:
        """
        Get total cost for current month for a session
        
        Args:
            session_id: Session ID
            
        Returns:
            Total monthly cost in USD
        """
        now = datetime.utcnow()
        current_month = now.month
        current_year = now.year
        
        # Query conversations for this session in current month
        result = await self.db.execute(
            select(func.sum(Conversation.total_cost))
            .where(
                Conversation.session_id == session_id,
                extract('month', Conversation.created_at) == current_month,
                extract('year', Conversation.created_at) == current_year
            )
        )
        total = result.scalar()
        
        return float(total) if total else 0.0
    
    async def get_cost_summary(
        self,
        session_id: str,
        conversation_id: Optional[str] = None,
        monthly_limit: Optional[float] = None
    ) -> CostSummary:
        """
        Get cost summary with conversation and monthly totals
        
        Args:
            session_id: Session ID
            conversation_id: Optional conversation ID
            monthly_limit: Optional custom monthly limit
            
        Returns:
            CostSummary object
        """
        conversation_cost = 0.0
        if conversation_id:
            conversation_cost = await self.get_conversation_cost(conversation_id)
        
        monthly_cost = await self.get_monthly_cost(session_id)
        limit = monthly_limit or self.DEFAULT_MONTHLY_LIMIT
        remaining = max(0.0, limit - monthly_cost)
        
        return CostSummary(
            conversation_cost=conversation_cost,
            monthly_cost=monthly_cost,
            monthly_limit=limit,
            remaining_budget=remaining
        )
    
    async def check_cost_limit(
        self,
        session_id: str,
        estimated_cost: float,
        monthly_limit: Optional[float] = None
    ) -> tuple[bool, float]:
        """
        Check if a request would exceed monthly cost limit
        
        Args:
            session_id: Session ID
            estimated_cost: Estimated cost for the request
            monthly_limit: Optional custom monthly limit
            
        Returns:
            Tuple of (allowed: bool, remaining_budget: float)
        """
        monthly_cost = await self.get_monthly_cost(session_id)
        limit = monthly_limit or self.DEFAULT_MONTHLY_LIMIT
        remaining = limit - monthly_cost
        
        allowed = estimated_cost <= remaining
        
        return allowed, remaining
    
    async def get_message_costs(
        self,
        conversation_id: str
    ) -> list[dict]:
        """
        Get cost breakdown for all messages in a conversation
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            List of dicts with message info and costs
        """
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        messages = result.scalars().all()
        
        result_list = []
        for msg in messages:
            if msg.role == "assistant" and msg.cost is not None:
                result_list.append({
                    "message_id": msg.id,
                    "created_at": msg.created_at,
                    "tokens_used": msg.tokens_used,
                    "cost": msg.cost,
                    "content_preview": msg.content[:100] if len(msg.content) > 100 else msg.content
                })
        
        return result_list
    
    async def get_session_total_cost(self, session_id: str) -> float:
        """
        Get total cost across all conversations for a session (all time)
        
        Args:
            session_id: Session ID
            
        Returns:
            Total cost in USD
        """
        result = await self.db.execute(
            select(func.sum(Conversation.total_cost))
            .where(Conversation.session_id == session_id)
        )
        total = result.scalar()
        
        return float(total) if total else 0.0
