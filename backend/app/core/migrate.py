"""
Database migration utilities.
Handles schema migrations for SQLite without Alembic.
"""
import logging
from sqlalchemy import text
from app.core.database import engine

logger = logging.getLogger(__name__)


async def migrate_database():
    """
    Run database migrations.
    Adds missing columns to existing tables.
    """
    async with engine.begin() as conn:
        # Check if tokens_used column exists in messages table
        result = await conn.execute(text("PRAGMA table_info(messages)"))
        columns = {row[1]: row for row in result.fetchall()}
        
        migrations_applied = []
        
        # Check if we have the old schema (tokens_input/tokens_output)
        has_old_tokens = 'tokens_input' in columns or 'tokens_output' in columns
        has_new_tokens = 'tokens_used' in columns
        
        if has_old_tokens and not has_new_tokens:
            # This is an older database - need to recreate the table
            logger.info("Migrating from old tokens schema to new schema...")
            
            # SQLite doesn't support DROP COLUMN, so we need to recreate the table
            # 1. Create new table with correct schema
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS messages_new (
                    id VARCHAR PRIMARY KEY,
                    conversation_id VARCHAR NOT NULL,
                    role VARCHAR NOT NULL,
                    content TEXT NOT NULL,
                    tokens_used INTEGER,
                    cost REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
                )
            """))
            
            # 2. Copy data from old table (combining tokens if needed)
            await conn.execute(text("""
                INSERT INTO messages_new (id, conversation_id, role, content, tokens_used, cost, created_at)
                SELECT 
                    id, 
                    conversation_id, 
                    role, 
                    content,
                    COALESCE(tokens_input, 0) + COALESCE(tokens_output, 0) as tokens_used,
                    cost,
                    created_at
                FROM messages
            """))
            
            # 3. Drop old table
            await conn.execute(text("DROP TABLE messages"))
            
            # 4. Rename new table
            await conn.execute(text("ALTER TABLE messages_new RENAME TO messages"))
            
            migrations_applied.append("Migrated messages table from old tokens schema")
        
        elif not has_new_tokens and not has_old_tokens:
            # Fresh database or missing columns - add them
            logger.info("Adding tokens_used column to messages table...")
            await conn.execute(text("ALTER TABLE messages ADD COLUMN tokens_used INTEGER"))
            migrations_applied.append("Added tokens_used to messages")
            
            if 'cost' not in columns:
                logger.info("Adding cost column to messages table...")
                await conn.execute(text("ALTER TABLE messages ADD COLUMN cost REAL"))
                migrations_applied.append("Added cost to messages")
        
        if migrations_applied:
            logger.info(f"Applied {len(migrations_applied)} migrations:")
            for migration in migrations_applied:
                logger.info(f"  - {migration}")
        else:
            logger.info("Database schema is up to date")
