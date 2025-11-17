import pytest
import aiosqlite
from modules.database import init_db, save_item, url_exists, get_url_hash


@pytest.mark.asyncio
async def test_url_hash_generation():
    """URL 해시 생성 테스트"""
    url1 = "https://example.com"
    url2 = "https://example.com"
    url3 = "https://example.com/different"
    
    hash1 = get_url_hash(url1)
    hash2 = get_url_hash(url2)
    hash3 = get_url_hash(url3)
    
    # 같은 URL은 같은 해시
    assert hash1 == hash2
    # 다른 URL은 다른 해시
    assert hash1 != hash3


@pytest.mark.asyncio
async def test_url_exists_check(tmp_path):
    """URL 존재 여부 확인 테스트"""
    db = tmp_path / "test.db"
    db_path = str(db)
    
    await init_db(db_path)
    
    url = "https://example.com/test"
    
    # 처음에는 존재하지 않음
    exists = await url_exists(db_path, url)
    assert exists is False
    
    # 저장 후에는 존재함
    item = {"url": url, "title": "Test", "content": "Content"}
    await save_item(db_path, item)
    
    exists = await url_exists(db_path, url)
    assert exists is True


@pytest.mark.asyncio
async def test_duplicate_insert_prevention(tmp_path):
    """중복 저장 방지 테스트"""
    db = tmp_path / "test.db"
    db_path = str(db)
    
    await init_db(db_path)
    
    url = "https://example.com/duplicate"
    item1 = {"url": url, "title": "Title 1", "content": "Content 1"}
    item2 = {"url": url, "title": "Title 2", "content": "Content 2"}
    
    # 첫 번째 저장
    await save_item(db_path, item1)
    
    # 두 번째 저장 (중복, INSERT OR IGNORE로 인해 무시됨)
    await save_item(db_path, item2)
    
    # DB에는 하나만 존재해야 함
    async with aiosqlite.connect(db_path) as conn:
        async with conn.execute("SELECT COUNT(*) FROM items WHERE url = ?", (url,)) as cur:
            count = await cur.fetchone()
            assert count[0] == 1
        
        # 첫 번째 저장된 데이터가 유지되어야 함
        async with conn.execute("SELECT title FROM items WHERE url = ?", (url,)) as cur:
            row = await cur.fetchone()
            assert row[0] == "Title 1"


@pytest.mark.asyncio
async def test_url_hash_index_exists(tmp_path):
    """URL 해시 인덱스 존재 확인"""
    db = tmp_path / "test.db"
    db_path = str(db)
    
    await init_db(db_path)
    
    async with aiosqlite.connect(db_path) as conn:
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_url_hash'"
        ) as cur:
            result = await cur.fetchone()
            assert result is not None
            assert result[0] == "idx_url_hash"
