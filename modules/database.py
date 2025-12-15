import aiosqlite
import hashlib
from typing import Optional, List, Dict
from datetime import datetime, timedelta


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
                keyword TEXT,
                keyword_matches INTEGER DEFAULT 0,
                images TEXT,
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
    
    # 이미지 리스트를 JSON 문자열로 변환
    images = item.get("images", [])
    images_str = ','.join(images) if images else None
    
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT OR IGNORE INTO items 
               (url, url_hash, title, content, keyword, keyword_matches, images) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                url, 
                url_hash, 
                item.get("title"), 
                item.get("content"),
                item.get("keyword"),
                item.get("keyword_matches", 0),
                images_str
            ),
        )
        await db.commit()


async def get_all_items(db_path: str, limit: int = 50, offset: int = 0, search: str = "") -> List[Dict]:
    """Get all items with pagination and search"""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        
        if search:
            query = """
                SELECT id, url, title, content, keyword, keyword_matches, images, fetched_at 
                FROM items 
                WHERE title LIKE ? OR url LIKE ? OR keyword LIKE ?
                ORDER BY fetched_at DESC 
                LIMIT ? OFFSET ?
            """
            search_param = f"%{search}%"
            async with db.execute(query, (search_param, search_param, search_param, limit, offset)) as cursor:
                rows = await cursor.fetchall()
        else:
            query = """
                SELECT id, url, title, content, keyword, keyword_matches, images, fetched_at 
                FROM items 
                ORDER BY fetched_at DESC 
                LIMIT ? OFFSET ?
            """
            async with db.execute(query, (limit, offset)) as cursor:
                rows = await cursor.fetchall()
        
        return [dict(row) for row in rows]


async def get_stats(db_path: str) -> Dict:
    """Get database statistics"""
    async with aiosqlite.connect(db_path) as db:
        # Total items
        async with db.execute("SELECT COUNT(*) FROM items") as cursor:
            total_items = (await cursor.fetchone())[0]
        
        # Today's items
        today = datetime.now().date()
        async with db.execute(
            "SELECT COUNT(*) FROM items WHERE DATE(fetched_at) = ?", 
            (today.isoformat(),)
        ) as cursor:
            today_items = (await cursor.fetchone())[0]
        
        # Unique domains
        async with db.execute(
            """
            SELECT COUNT(DISTINCT SUBSTR(url, 
                INSTR(url, '://') + 3, 
                CASE 
                    WHEN INSTR(SUBSTR(url, INSTR(url, '://') + 3), '/') > 0 
                    THEN INSTR(SUBSTR(url, INSTR(url, '://') + 3), '/') - 1
                    ELSE LENGTH(url)
                END
            )) FROM items
            """
        ) as cursor:
            unique_domains = (await cursor.fetchone())[0]
        
        return {
            'total_items': total_items,
            'today_items': today_items,
            'unique_domains': unique_domains
        }
