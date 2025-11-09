import aiosqlite


async def init_db(db_path: str = "data.db"):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                title TEXT,
                content TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.commit()


async def save_item(db_path: str, item: dict):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT OR IGNORE INTO items (url, title, content) VALUES (?, ?, ?)",
            (item.get("url"), item.get("title"), item.get("content")),
        )
        await db.commit()
