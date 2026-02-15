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
        
        # Check if compression_profiles table exists
        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='compression_profiles'"
        ))
        compression_profiles_exists = result.fetchone() is not None
        
        if not compression_profiles_exists:
            logger.info("Creating compression_profiles table...")
            await conn.execute(text("""
                CREATE TABLE compression_profiles (
                    id VARCHAR PRIMARY KEY,
                    session_id VARCHAR,
                    name VARCHAR NOT NULL,
                    max_width INTEGER NOT NULL,
                    max_height INTEGER NOT NULL,
                    quality INTEGER NOT NULL,
                    target_size_kb INTEGER NOT NULL,
                    format VARCHAR NOT NULL,
                    retain_aspect_ratio BOOLEAN DEFAULT 1,
                    is_default BOOLEAN DEFAULT 0,
                    system_default BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
            """))
            
            # Create index on session_id for fast lookups
            await conn.execute(text(
                "CREATE INDEX ix_compression_profiles_session_id ON compression_profiles(session_id)"
            ))
            
            migrations_applied.append("Created compression_profiles table with indexes")
            
            # Create system default profiles (one-time, global)
            logger.info("Creating system default profiles...")
            from app.services.profile_service import create_system_default_profiles
            from app.core.database import async_session
            
            async with async_session() as session:
                await create_system_default_profiles(session)
            
            migrations_applied.append("Created system default profiles")
        else:
            # Check if system_default column exists
            result = await conn.execute(text("PRAGMA table_info(compression_profiles)"))
            profile_columns = {row[1]: row for row in result.fetchall()}
            
            if 'retain_aspect_ratio' not in profile_columns:
                logger.info("Adding retain_aspect_ratio column to compression_profiles table...")
                await conn.execute(text("ALTER TABLE compression_profiles ADD COLUMN retain_aspect_ratio BOOLEAN DEFAULT 1"))
                migrations_applied.append("Added 'retain_aspect_ratio' column to compression_profiles")
            
            if 'system_default' not in profile_columns:
                logger.info("Adding system_default column to compression_profiles table...")
                await conn.execute(text("ALTER TABLE compression_profiles ADD COLUMN system_default BOOLEAN DEFAULT 0"))
                migrations_applied.append("Added 'system_default' column to compression_profiles")
                
                # Check if session_id is NOT NULL and needs to be made nullable
                # In SQLite, this requires recreating the table
                session_id_info = profile_columns.get('session_id')
                if session_id_info and session_id_info[3] == 1:  # notnull flag
                    logger.info("Making session_id nullable in compression_profiles (for system defaults)...")
                    
                    # Create new table with nullable session_id
                    await conn.execute(text("""
                        CREATE TABLE compression_profiles_new (
                            id VARCHAR PRIMARY KEY,
                            session_id VARCHAR,
                            name VARCHAR NOT NULL,
                            max_width INTEGER NOT NULL,
                            max_height INTEGER NOT NULL,
                            quality INTEGER NOT NULL,
                            target_size_kb INTEGER NOT NULL,
                            format VARCHAR NOT NULL,
                            retain_aspect_ratio BOOLEAN DEFAULT 1,
                            is_default BOOLEAN DEFAULT 0,
                            system_default BOOLEAN DEFAULT 0,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME,
                            FOREIGN KEY(session_id) REFERENCES sessions(id)
                        )
                    """))
                    
                    # Copy data from old table
                    await conn.execute(text("""
                        INSERT INTO compression_profiles_new 
                        SELECT id, session_id, name, max_width, max_height, quality, 
                               target_size_kb, format, 1, is_default, system_default, 
                               created_at, updated_at
                        FROM compression_profiles
                    """))
                    
                    # Drop old table
                    await conn.execute(text("DROP TABLE compression_profiles"))
                    
                    # Rename new table
                    await conn.execute(text("ALTER TABLE compression_profiles_new RENAME TO compression_profiles"))
                    
                    # Recreate index
                    await conn.execute(text(
                        "CREATE INDEX ix_compression_profiles_session_id ON compression_profiles(session_id)"
                    ))
                    
                    migrations_applied.append("Made session_id nullable in compression_profiles")
                
                # Delete all existing per-session default profiles (clean slate for system defaults)
                logger.info("Removing old per-session default profiles...")
                result = await conn.execute(text("DELETE FROM compression_profiles"))
                deleted_count = result.rowcount
                if deleted_count > 0:
                    migrations_applied.append(f"Deleted {deleted_count} old per-session profiles")
                
                # Create system default profiles (one-time, global)
                logger.info("Creating system default profiles...")
                from app.services.profile_service import create_system_default_profiles
                from app.core.database import async_session
                
                async with async_session() as session:
                    await create_system_default_profiles(session)
                
                migrations_applied.append("Created system default profiles")
        
        if migrations_applied:
            logger.info(f"Applied {len(migrations_applied)} migrations:")
            for migration in migrations_applied:
                logger.info(f"  - {migration}")
        else:
            logger.info("Database schema is up to date")
        
        # Check images table for exif_data column (for GPS preservation)
        result = await conn.execute(text("PRAGMA table_info(images)"))
        images_columns = {row[1]: row for row in result.fetchall()}
        
        if 'exif_data' not in images_columns:
            logger.info("Adding exif_data column to images table for GPS preservation...")
            await conn.execute(text("ALTER TABLE images ADD COLUMN exif_data TEXT"))
            migrations_applied.append("Added 'exif_data' column to images for GPS preservation")
        
        # Add GPS coordinate columns for mobile uploads (when Android strips EXIF GPS data)
        if 'gps_latitude' not in images_columns:
            logger.info("Adding GPS coordinate columns to images table...")
            await conn.execute(text("ALTER TABLE images ADD COLUMN gps_latitude REAL"))
            await conn.execute(text("ALTER TABLE images ADD COLUMN gps_longitude REAL"))
            await conn.execute(text("ALTER TABLE images ADD COLUMN gps_altitude REAL"))
            migrations_applied.append("Added GPS coordinate columns to images for mobile uploads")
