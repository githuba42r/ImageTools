"""Background task scheduler for cleanup and maintenance tasks."""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


async def cleanup_expired_sessions_task():
    """Scheduled task to cleanup expired sessions and their associated data."""
    logger.info("Running scheduled cleanup of expired sessions...")
    
    try:
        async with AsyncSessionLocal() as db:
            deleted_count = await SessionService.cleanup_expired_sessions(db)
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired session(s)")
            else:
                logger.debug("No expired sessions to clean up")
                
    except Exception as e:
        logger.error(f"Error during scheduled cleanup: {e}", exc_info=True)


def start_scheduler():
    """Initialize and start the background scheduler."""
    global scheduler
    
    if not settings.CLEANUP_ENABLED:
        logger.info("Cleanup scheduler is disabled via configuration")
        return
    
    if scheduler is not None:
        logger.warning("Scheduler already running")
        return
    
    try:
        scheduler = AsyncIOScheduler()
        
        # Parse cron expression from settings
        # Default: "0 2 * * *" = Daily at 2 AM
        cron_parts = settings.CLEANUP_SCHEDULE_CRON.split()
        
        if len(cron_parts) != 5:
            logger.error(f"Invalid cron expression: {settings.CLEANUP_SCHEDULE_CRON}")
            return
        
        minute, hour, day, month, day_of_week = cron_parts
        
        # Add cleanup job
        scheduler.add_job(
            cleanup_expired_sessions_task,
            trigger=CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week
            ),
            id='cleanup_expired_sessions',
            name='Cleanup Expired Sessions',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info(f"Scheduler started - Cleanup will run on schedule: {settings.CLEANUP_SCHEDULE_CRON}")
        
        # Also run cleanup on startup (but don't block)
        logger.info("Running initial cleanup on startup...")
        scheduler.add_job(
            cleanup_expired_sessions_task,
            id='cleanup_startup',
            name='Initial Cleanup on Startup',
            replace_existing=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)


def stop_scheduler():
    """Shutdown the scheduler gracefully."""
    global scheduler
    
    if scheduler is None:
        return
    
    try:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler shut down successfully")
        scheduler = None
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {e}", exc_info=True)
