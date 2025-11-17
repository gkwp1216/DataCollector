import aiosqlite
import hashlib
from typing import Optional


async def init_db(db_path: str = "data.db"):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                url_hash TEXT,
                title TEXT,
                content TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # URL 해시 인덱스 생성 (빠른 중복 검사)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_url_hash ON items(url_hash)"
        )
        await db.commit()


def get_url_hash(url: str) -> str:
    """URL의 MD5 해시 생성"""
    return hashlib.md5(url.encode('utf-8')).hexdigest()


async def url_exists(db_path: str, url: str) -> bool:
    """URL이 이미 DB에 존재하는지 확인"""
    url_hash = get_url_hash(url)
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT 1 FROM items WHERE url_hash = ? LIMIT 1",
            (url_hash,)
        ) as cursor:
            result = await cursor.fetchone()
            return result is not None


async def save_item(db_path: str, item: dict):
    url = item.get("url")
    url_hash = get_url_hash(url) if url else None
    
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT OR IGNORE INTO items (url, url_hash, title, content) VALUES (?, ?, ?, ?)",
            (url, url_hash, item.get("title"), item.get("content")),
        )
        await db.commit()
