"""
Database migration utilities.
Handles schema migrations for SQLite without Alembic.
"""
import logging
from sqlalchemy import text
from app.core.database import engine, AsyncSessionLocal

logger = logging.getLogger(__name__)

ANONYMOUS_USER_ID = "00000000-0000-0000-0000-000000000000"


async def migrate_database():
    """
    Run database migrations.
    Handles sessions→users rename and adds missing columns to existing tables.
    """
    async with engine.begin() as conn:
        migrations_applied = []

        # ------------------------------------------------------------------ #
        # BLOCK 1: sessions → users table migration                           #
        # ------------------------------------------------------------------ #

        # Check if users table already exists (skip migration if so)
        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        ))
        users_table_exists = result.fetchone() is not None

        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
        ))
        sessions_table_exists = result.fetchone() is not None

        if not users_table_exists and sessions_table_exists:
            logger.info("Migrating sessions table to users table...")

            # Create users table (same as sessions minus expires_at)
            await conn.execute(text("""
                CREATE TABLE users (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    username VARCHAR,
                    display_name VARCHAR,
                    created_at DATETIME,
                    last_activity DATETIME
                )
            """))
            await conn.execute(text("CREATE INDEX ix_users_username ON users(username)"))

            # Copy all session rows into users (drop expires_at)
            await conn.execute(text("""
                INSERT INTO users (id, username, display_name, created_at)
                SELECT id, username, display_name, created_at
                FROM sessions
            """))

            # Rename session_id → user_id in each child table
            child_tables = [
                ("images",               "session_id", "user_id", "users",
                 """CREATE TABLE images_new (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        user_id VARCHAR NOT NULL,
                        filename VARCHAR NOT NULL,
                        original_filename VARCHAR NOT NULL,
                        file_path VARCHAR NOT NULL,
                        thumbnail_path VARCHAR,
                        file_size INTEGER NOT NULL,
                        width INTEGER,
                        height INTEGER,
                        format VARCHAR,
                        uploaded_at DATETIME,
                        exif_data TEXT,
                        gps_latitude REAL,
                        gps_longitude REAL,
                        gps_altitude REAL,
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )""",
                 "INSERT INTO images_new SELECT id, session_id, filename, original_filename, file_path, thumbnail_path, file_size, width, height, format, uploaded_at, exif_data, gps_latitude, gps_longitude, gps_altitude FROM images",
                 ["CREATE INDEX ix_images_user_id ON images_new(user_id)"]),

                ("mobile_app_pairings",  "session_id", "user_id", "users",
                 """CREATE TABLE mobile_app_pairings_new (
                        id VARCHAR PRIMARY KEY,
                        user_id VARCHAR NOT NULL,
                        device_name VARCHAR,
                        device_model VARCHAR,
                        device_manufacturer VARCHAR,
                        device_owner VARCHAR,
                        os_version VARCHAR,
                        app_version VARCHAR,
                        shared_secret VARCHAR NOT NULL UNIQUE,
                        long_term_secret VARCHAR,
                        long_term_expires_at DATETIME,
                        refresh_secret VARCHAR,
                        refresh_expires_at DATETIME,
                        is_active BOOLEAN DEFAULT 1,
                        used BOOLEAN DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_used_at DATETIME,
                        expires_at DATETIME,
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )""",
                 """INSERT INTO mobile_app_pairings_new
                        SELECT id, session_id, device_name, device_model, device_manufacturer,
                               device_owner, os_version, app_version, shared_secret,
                               long_term_secret, long_term_expires_at, refresh_secret,
                               refresh_expires_at, is_active, used, created_at,
                               last_used_at, expires_at
                        FROM mobile_app_pairings""",
                 ["CREATE INDEX ix_mobile_app_pairings_shared_secret ON mobile_app_pairings_new(shared_secret)",
                  "CREATE INDEX ix_mobile_app_pairings_user_id ON mobile_app_pairings_new(user_id)"]),

                ("addon_authorizations", "session_id", "user_id", "users",
                 """CREATE TABLE addon_authorizations_new (
                        id VARCHAR PRIMARY KEY,
                        user_id VARCHAR NOT NULL,
                        addon_name VARCHAR NOT NULL,
                        browser_name VARCHAR,
                        authorization_code VARCHAR NOT NULL UNIQUE,
                        access_token VARCHAR,
                        refresh_token VARCHAR,
                        access_expires_at DATETIME,
                        refresh_expires_at DATETIME,
                        is_active BOOLEAN DEFAULT 1,
                        code_expires_at DATETIME,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_used_at DATETIME,
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )""",
                 """INSERT INTO addon_authorizations_new
                        SELECT id, session_id, addon_name, browser_name, authorization_code,
                               access_token, refresh_token, access_expires_at, refresh_expires_at,
                               is_active, code_expires_at, created_at, last_used_at
                        FROM addon_authorizations""",
                 ["CREATE INDEX ix_addon_authorizations_user_id ON addon_authorizations_new(user_id)",
                  "CREATE INDEX ix_addon_authorizations_authorization_code ON addon_authorizations_new(authorization_code)"]),

                ("conversations",        "session_id", "user_id", "users",
                 """CREATE TABLE conversations_new (
                        id VARCHAR PRIMARY KEY,
                        user_id VARCHAR NOT NULL,
                        title VARCHAR,
                        model VARCHAR,
                        system_prompt TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME,
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )""",
                 """INSERT INTO conversations_new
                        SELECT id, session_id, title, model, system_prompt, created_at, updated_at
                        FROM conversations""",
                 ["CREATE INDEX ix_conversations_user_id ON conversations_new(user_id)"]),

                ("user_settings",        "session_id", "user_id", "users",
                 """CREATE TABLE user_settings_new (
                        id VARCHAR PRIMARY KEY,
                        user_id VARCHAR NOT NULL UNIQUE,
                        openrouter_api_key TEXT,
                        preferred_model VARCHAR,
                        system_prompt TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME,
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )""",
                 """INSERT INTO user_settings_new
                        SELECT id, session_id, openrouter_api_key, preferred_model,
                               system_prompt, created_at, updated_at
                        FROM user_settings""",
                 ["CREATE UNIQUE INDEX ix_user_settings_user_id ON user_settings_new(user_id)"]),

                ("openrouter_keys",      "session_id", "user_id", "users",
                 """CREATE TABLE openrouter_keys_new (
                        id VARCHAR PRIMARY KEY,
                        user_id VARCHAR NOT NULL UNIQUE,
                        encrypted_api_key TEXT NOT NULL,
                        key_hash VARCHAR,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME,
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )""",
                 """INSERT INTO openrouter_keys_new
                        SELECT id, session_id, encrypted_api_key, key_hash, created_at, updated_at
                        FROM openrouter_keys""",
                 ["CREATE UNIQUE INDEX ix_openrouter_keys_user_id ON openrouter_keys_new(user_id)"]),
            ]

            for (table, old_col, new_col, ref_table, create_sql, insert_sql, index_sqls) in child_tables:
                # Check if table exists before trying to migrate
                result = await conn.execute(text(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
                ))
                if result.fetchone() is None:
                    continue  # table doesn't exist yet, skip

                # Also check if the old column exists
                result = await conn.execute(text(f"PRAGMA table_info({table})"))
                col_names = [row[1] for row in result.fetchall()]
                if old_col not in col_names:
                    continue  # already migrated or doesn't have the column

                logger.info(f"Renaming {old_col} → {new_col} in {table}...")
                await conn.execute(text(create_sql))
                await conn.execute(text(insert_sql))
                for idx_sql in index_sqls:
                    await conn.execute(text(idx_sql))
                await conn.execute(text(f"DROP TABLE {table}"))
                await conn.execute(text(f"ALTER TABLE {table}_new RENAME TO {table}"))
                migrations_applied.append(f"Renamed {old_col}→{new_col} in {table}")

            # Update any "anonymous" string placeholder → proper UUID in user_id columns
            for table in ["images", "mobile_app_pairings", "addon_authorizations",
                          "conversations", "user_settings", "openrouter_keys"]:
                result = await conn.execute(text(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
                ))
                if result.fetchone() is None:
                    continue
                result = await conn.execute(text(f"PRAGMA table_info({table})"))
                col_names = [row[1] for row in result.fetchall()]
                if "user_id" in col_names:
                    await conn.execute(text(
                        f"UPDATE {table} SET user_id = :uuid WHERE user_id = 'anonymous'"
                    ), {"uuid": ANONYMOUS_USER_ID})

            # Ensure anonymous user record exists with proper UUID
            await conn.execute(text("""
                INSERT OR IGNORE INTO users (id, username, display_name, created_at)
                VALUES (:uuid, NULL, NULL, CURRENT_TIMESTAMP)
            """), {"uuid": ANONYMOUS_USER_ID})

            # Drop old sessions table
            await conn.execute(text("DROP TABLE sessions"))
            migrations_applied.append("Migrated sessions → users table")

        elif not users_table_exists and not sessions_table_exists:
            # Fresh database — users table will be created by init_db(); nothing to do here
            logger.info("No sessions table found; users table will be created by init_db()")

        # ------------------------------------------------------------------ #
        # BLOCK 1b: users table — add missing last_activity column           #
        # ------------------------------------------------------------------ #

        # Re-check — the users table now exists if it was pre-existing or just
        # created from the sessions migration above.  Fresh DBs skip this block
        # because init_db() will create the table correctly from the model.
        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        ))
        if result.fetchone() is not None:
            result = await conn.execute(text("PRAGMA table_info(users)"))
            user_columns = {row[1] for row in result.fetchall()}
            if 'last_activity' not in user_columns:
                logger.info("Adding last_activity column to users table...")
                await conn.execute(text(
                    "ALTER TABLE users ADD COLUMN last_activity DATETIME"
                ))
                migrations_applied.append("Added last_activity column to users")

        # ------------------------------------------------------------------ #
        # BLOCK 2: messages tokens schema migration                           #
        # ------------------------------------------------------------------ #

        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='messages'"
        ))
        messages_exists = result.fetchone() is not None

        if messages_exists:
            result = await conn.execute(text("PRAGMA table_info(messages)"))
            columns = {row[1]: row for row in result.fetchall()}

            has_old_tokens = 'tokens_input' in columns or 'tokens_output' in columns
            has_new_tokens = 'tokens_used' in columns

            if has_old_tokens and not has_new_tokens:
                logger.info("Migrating from old tokens schema to new schema...")
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
                await conn.execute(text("DROP TABLE messages"))
                await conn.execute(text("ALTER TABLE messages_new RENAME TO messages"))
                migrations_applied.append("Migrated messages table from old tokens schema")

            elif not has_new_tokens and not has_old_tokens:
                logger.info("Adding tokens_used column to messages table...")
                await conn.execute(text("ALTER TABLE messages ADD COLUMN tokens_used INTEGER"))
                migrations_applied.append("Added tokens_used to messages")

                if 'cost' not in columns:
                    logger.info("Adding cost column to messages table...")
                    await conn.execute(text("ALTER TABLE messages ADD COLUMN cost REAL"))
                    migrations_applied.append("Added cost to messages")

        # ------------------------------------------------------------------ #
        # BLOCK 3: mobile_app_pairings table / columns                        #
        # ------------------------------------------------------------------ #

        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='mobile_app_pairings'"
        ))
        mobile_table_exists = result.fetchone() is not None

        if not mobile_table_exists:
            logger.info("Creating mobile_app_pairings table...")
            await conn.execute(text("""
                CREATE TABLE mobile_app_pairings (
                    id VARCHAR PRIMARY KEY,
                    user_id VARCHAR NOT NULL,
                    device_name VARCHAR,
                    shared_secret VARCHAR NOT NULL UNIQUE,
                    is_active BOOLEAN DEFAULT 1,
                    used BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_used_at DATETIME,
                    expires_at DATETIME,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """))
            await conn.execute(text(
                "CREATE INDEX ix_mobile_app_pairings_shared_secret ON mobile_app_pairings(shared_secret)"
            ))
            await conn.execute(text(
                "CREATE INDEX ix_mobile_app_pairings_user_id ON mobile_app_pairings(user_id)"
            ))
            migrations_applied.append("Created mobile_app_pairings table with indexes")
        else:
            result = await conn.execute(text("PRAGMA table_info(mobile_app_pairings)"))
            mobile_columns = {row[1]: row for row in result.fetchall()}

            if 'used' not in mobile_columns:
                logger.info("Adding 'used' column to mobile_app_pairings table...")
                await conn.execute(text("ALTER TABLE mobile_app_pairings ADD COLUMN used BOOLEAN DEFAULT 0"))
                migrations_applied.append("Added 'used' column to mobile_app_pairings")

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

        # ------------------------------------------------------------------ #
        # BLOCK 4: compression_profiles table / columns                       #
        # ------------------------------------------------------------------ #

        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='compression_profiles'"
        ))
        compression_profiles_exists = result.fetchone() is not None

        if not compression_profiles_exists:
            logger.info("Creating compression_profiles table...")
            await conn.execute(text("""
                CREATE TABLE compression_profiles (
                    id VARCHAR PRIMARY KEY,
                    user_id VARCHAR,
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
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """))
            await conn.execute(text(
                "CREATE INDEX ix_compression_profiles_user_id ON compression_profiles(user_id)"
            ))
            migrations_applied.append("Created compression_profiles table with indexes")

            logger.info("Creating system default profiles...")
            from app.services.profile_service import create_system_default_profiles
            async with AsyncSessionLocal() as session:
                await create_system_default_profiles(session)
            migrations_applied.append("Created system default profiles")
        else:
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

                # If session_id column is NOT NULL, recreate table with nullable user_id
                user_id_info = profile_columns.get('user_id') or profile_columns.get('session_id')
                col_name = 'user_id' if 'user_id' in profile_columns else 'session_id'
                if user_id_info and user_id_info[3] == 1:  # notnull flag
                    logger.info("Making user_id nullable in compression_profiles (for system defaults)...")
                    await conn.execute(text("""
                        CREATE TABLE compression_profiles_new (
                            id VARCHAR PRIMARY KEY,
                            user_id VARCHAR,
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
                            FOREIGN KEY(user_id) REFERENCES users(id)
                        )
                    """))
                    await conn.execute(text(f"""
                        INSERT INTO compression_profiles_new
                        SELECT id, {col_name}, name, max_width, max_height, quality,
                               target_size_kb, format, 1, is_default, system_default,
                               created_at, updated_at
                        FROM compression_profiles
                    """))
                    await conn.execute(text("DROP TABLE compression_profiles"))
                    await conn.execute(text("ALTER TABLE compression_profiles_new RENAME TO compression_profiles"))
                    await conn.execute(text(
                        "CREATE INDEX ix_compression_profiles_user_id ON compression_profiles(user_id)"
                    ))
                    migrations_applied.append("Made user_id nullable in compression_profiles")

                logger.info("Removing old per-user default profiles...")
                result = await conn.execute(text("DELETE FROM compression_profiles"))
                deleted_count = result.rowcount
                if deleted_count > 0:
                    migrations_applied.append(f"Deleted {deleted_count} old per-user profiles")

                logger.info("Creating system default profiles...")
                from app.services.profile_service import create_system_default_profiles
                async with AsyncSessionLocal() as session:
                    await create_system_default_profiles(session)
                migrations_applied.append("Created system default profiles")

        # ------------------------------------------------------------------ #
        # BLOCK 5: images table — exif/GPS columns                           #
        # ------------------------------------------------------------------ #

        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='images'"
        ))
        images_exists = result.fetchone() is not None

        if images_exists:
            result = await conn.execute(text("PRAGMA table_info(images)"))
            images_columns = {row[1]: row for row in result.fetchall()}

            if 'exif_data' not in images_columns:
                logger.info("Adding exif_data column to images table for GPS preservation...")
                await conn.execute(text("ALTER TABLE images ADD COLUMN exif_data TEXT"))
                migrations_applied.append("Added 'exif_data' column to images for GPS preservation")

            if 'gps_latitude' not in images_columns:
                logger.info("Adding GPS coordinate columns to images table...")
                await conn.execute(text("ALTER TABLE images ADD COLUMN gps_latitude REAL"))
                await conn.execute(text("ALTER TABLE images ADD COLUMN gps_longitude REAL"))
                await conn.execute(text("ALTER TABLE images ADD COLUMN gps_altitude REAL"))
                migrations_applied.append("Added GPS coordinate columns to images for mobile uploads")

        # ------------------------------------------------------------------ #
        # BLOCK 6: sessions table legacy Authelia columns (if still exists)  #
        # ------------------------------------------------------------------ #
        # (Only reached if sessions table still exists and users table already
        #  existed — meaning this migration ran before but sessions wasn't
        #  cleaned up. Skip silently.)

        if migrations_applied:
            logger.info(f"Applied {len(migrations_applied)} migrations:")
            for migration in migrations_applied:
                logger.info(f"  - {migration}")
        else:
            logger.info("Database schema is up to date")
