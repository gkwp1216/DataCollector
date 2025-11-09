import pytest
import aiosqlite
from modules.database import init_db, save_item


@pytest.mark.asyncio
async def test_init_and_save(tmp_path):
    db = tmp_path / "test.db"
    db_path = str(db)

    # DB 초기화
    await init_db(db_path)

    item = {"url": "https://example.test", "title": "제목", "content": "내용"}
    await save_item(db_path, item)

    # 저장 확인
    async with aiosqlite.connect(db_path) as conn:
        async with conn.execute("SELECT url, title, content FROM items WHERE url = ?", (item["url"],)) as cur:
            row = await cur.fetchone()

    assert row is not None
    assert row[0] == item["url"]
    assert row[1] == item["title"]
