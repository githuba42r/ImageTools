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
        # Check sessions table for new Authelia user fields
        result = await conn.execute(text("PRAGMA table_info(sessions)"))
        session_columns = {row[1]: row for row in result.fetchall()}
        
        migrations_applied = []
        
        # Add username column for Authelia Remote-User header
        if 'username' not in session_columns:
            logger.info("Adding username column to sessions table...")
            await conn.execute(text("ALTER TABLE sessions ADD COLUMN username VARCHAR"))
            await conn.execute(text("CREATE INDEX ix_sessions_username ON sessions(username)"))
            migrations_applied.append("Added 'username' column to sessions with index")
        
        # Add display_name column for Authelia Remote-Name header
        if 'display_name' not in session_columns:
            logger.info("Adding display_name column to sessions table...")
            await conn.execute(text("ALTER TABLE sessions ADD COLUMN display_name VARCHAR"))
            migrations_applied.append("Added 'display_name' column to sessions")
        
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
        
        # Check if mobile_app_pairings table exists
        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='mobile_app_pairings'"
        ))
        mobile_table_exists = result.fetchone() is not None
        
        if not mobile_table_exists:
            logger.info("Creating mobile_app_pairings table...")
            await conn.execute(text("""
                CREATE TABLE mobile_app_pairings (
                    id VARCHAR PRIMARY KEY,
                    session_id VARCHAR NOT NULL,
                    device_name VARCHAR,
                    shared_secret VARCHAR NOT NULL UNIQUE,
                    is_active BOOLEAN DEFAULT 1,
                    used BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_used_at DATETIME,
                    expires_at DATETIME,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
            """))
            
            # Create index on shared_secret for fast lookups
            await conn.execute(text(
                "CREATE INDEX ix_mobile_app_pairings_shared_secret ON mobile_app_pairings(shared_secret)"
            ))
            
            # Create index on session_id for listing pairings
            await conn.execute(text(
                "CREATE INDEX ix_mobile_app_pairings_session_id ON mobile_app_pairings(session_id)"
            ))
            
            migrations_applied.append("Created mobile_app_pairings table with indexes")
        else:
            # Check if 'used' column exists in mobile_app_pairings
            result = await conn.execute(text("PRAGMA table_info(mobile_app_pairings)"))
            mobile_columns = {row[1]: row for row in result.fetchall()}
            
            if 'used' not in mobile_columns:
                logger.info("Adding 'used' column to mobile_app_pairings table...")
                await conn.execute(text("ALTER TABLE mobile_app_pairings ADD COLUMN used BOOLEAN DEFAULT 0"))
                migrations_applied.append("Added 'used' column to mobile_app_pairings")
            
            # Add device metadata columns
            if 'device_model' not in mobile_columns:
                logger.info("Adding device metadata columns to mobile_app_pairings table...")
                await conn.execute(text("ALTER TABLE mobile_app_pairings ADD COLUMN device_model VARCHAR"))
                await conn.execute(text("ALTER TABLE mobile_app_pairings ADD COLUMN device_manufacturer VARCHAR"))
                await conn.execute(text("ALTER TABLE mobile_app_pairings ADD COLUMN device_owner VARCHAR"))
                await conn.execute(text("ALTER TABLE mobile_app_pairings ADD COLUMN os_version VARCHAR"))
                await conn.execute(text("ALTER TABLE mobile_app_pairings ADD COLUMN app_version VARCHAR"))
                migrations_applied.append("Added device metadata columns to mobile_app_pairings")
            elif 'device_owner' not in mobile_columns:
                logger.info("Adding device_owner column to mobile_app_pairings table...")
                await conn.execute(text("ALTER TABLE mobile_app_pairings ADD COLUMN device_owner VARCHAR"))
                migrations_applied.append("Added device_owner column to mobile_app_pairings")
        
        if migrations_applied:
            logger.info(f"Applied {len(migrations_applied)} migrations:")
            for migration in migrations_applied:
                logger.info(f"  - {migration}")
        else:
            logger.info("Database schema is up to date")
