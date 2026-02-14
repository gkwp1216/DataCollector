"""
Database migration script
Add new columns for keyword search functionality
"""

import asyncio
import aiosqlite
from pathlib import Path


async def migrate_database(db_path: str = "data.db"):
    """Add keyword search columns to existing database"""
    
    async with aiosqlite.connect(db_path) as db:
        # Check if columns already exist
        async with db.execute("PRAGMA table_info(items)") as cursor:
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
        
        print(f"Current columns: {column_names}")
        
        # Add keyword column if not exists
        if 'keyword' not in column_names:
            print("Adding 'keyword' column...")
            await db.execute("ALTER TABLE items ADD COLUMN keyword TEXT")
            print("✅ Added 'keyword' column")
        
        # Add keyword_matches column if not exists
        if 'keyword_matches' not in column_names:
            print("Adding 'keyword_matches' column...")
            await db.execute("ALTER TABLE items ADD COLUMN keyword_matches INTEGER DEFAULT 0")
            print("✅ Added 'keyword_matches' column")
        
        # Add images column if not exists
        if 'images' not in column_names:
            print("Adding 'images' column...")
            await db.execute("ALTER TABLE items ADD COLUMN images TEXT")
            print("✅ Added 'images' column")
        
        await db.commit()
        
        # Verify changes
        async with db.execute("PRAGMA table_info(items)") as cursor:
            columns = await cursor.fetchall()
            new_column_names = [col[1] for col in columns]
        
        print(f"\nUpdated columns: {new_column_names}")
        print("\n✅ Database migration completed successfully!")


async def main():
    """Run migration"""
    db_path = "data.db"
    
    if not Path(db_path).exists():
        print(f"Database '{db_path}' does not exist. No migration needed.")
        print("New database will be created with correct schema on first use.")
        return
    
    print(f"Migrating database: {db_path}")
    print("-" * 50)
    
    await migrate_database(db_path)


if __name__ == "__main__":
    asyncio.run(main())
