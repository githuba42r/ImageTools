"""
Migration script to add long-term authorization fields to mobile_app_pairings table
"""
import asyncio
import sqlite3
from pathlib import Path


async def migrate():
    """Add long_term_secret, refresh_secret, and expiration fields"""
    db_path = Path(__file__).parent.parent.parent / "storage" / "imagetools.db"
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Starting migration for long-term authorization...")
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(mobile_app_pairings)")
        columns = [col[1] for col in cursor.fetchall()]
        
        migrations = []
        
        if 'long_term_secret' not in columns:
            migrations.append("ALTER TABLE mobile_app_pairings ADD COLUMN long_term_secret TEXT")
        
        if 'long_term_expires_at' not in columns:
            migrations.append("ALTER TABLE mobile_app_pairings ADD COLUMN long_term_expires_at TIMESTAMP")
        
        if 'refresh_secret' not in columns:
            migrations.append("ALTER TABLE mobile_app_pairings ADD COLUMN refresh_secret TEXT")
        
        if 'refresh_expires_at' not in columns:
            migrations.append("ALTER TABLE mobile_app_pairings ADD COLUMN refresh_expires_at TIMESTAMP")
        
        if not migrations:
            print("✓ All columns already exist, no migration needed")
            return
        
        # Execute migrations
        for migration_sql in migrations:
            print(f"Executing: {migration_sql}")
            cursor.execute(migration_sql)
        
        # Create indexes for new secret columns
        if 'long_term_secret' in [m.split()[5] for m in migrations if 'long_term_secret' in m]:
            print("Creating index on long_term_secret...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_mobile_app_pairings_long_term_secret 
                ON mobile_app_pairings(long_term_secret)
            """)
        
        if 'refresh_secret' in [m.split()[5] for m in migrations if 'refresh_secret' in m]:
            print("Creating index on refresh_secret...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_mobile_app_pairings_refresh_secret 
                ON mobile_app_pairings(refresh_secret)
            """)
        
        conn.commit()
        print("✓ Migration completed successfully")
        
        # Verify columns
        cursor.execute("PRAGMA table_info(mobile_app_pairings)")
        all_columns = [col[1] for col in cursor.fetchall()]
        print(f"✓ Final columns: {', '.join(all_columns)}")
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
