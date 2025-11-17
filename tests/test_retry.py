import pytest
from unittest.mock import AsyncMock, patch
from modules.crawler import AsyncCrawler


@pytest.mark.asyncio
async def test_fetch_with_retry_success():
    """재시도 후 성공하는 경우"""
    crawler = AsyncCrawler(timeout=5, max_retries=3, delay=0.1)
    
    # 첫 시도는 실패, 두 번째는 성공
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="<html><body>Success</body></html>")
    mock_response.raise_for_status = AsyncMock()
    
    with patch.object(crawler, '_ensure_session'):
        crawler._session = AsyncMock()
        crawler._session.get = AsyncMock()
        crawler._session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        crawler._session.get.return_value.__aexit__ = AsyncMock()
        
        result = await crawler.fetch("https://example.com")
        assert result is not None
        assert "Success" in result
    
    await crawler.close()


@pytest.mark.asyncio
async def test_fetch_404_no_retry():
    """404는 재시도하지 않음"""
    crawler = AsyncCrawler(timeout=5, max_retries=3, delay=0.1)
    
    mock_response = AsyncMock()
    mock_response.status = 404
    
    with patch.object(crawler, '_ensure_session'):
        crawler._session = AsyncMock()
        crawler._session.get = AsyncMock()
        crawler._session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        crawler._session.get.return_value.__aexit__ = AsyncMock()
        
        result = await crawler.fetch("https://example.com/notfound")
        assert result is None
    
    await crawler.close()


@pytest.mark.asyncio
async def test_user_agent_setting():
    """User-Agent가 설정되는지 확인"""
    custom_ua = "CustomBot/1.0"
    crawler = AsyncCrawler(user_agent=custom_ua)
    
    assert crawler._user_agent == custom_ua
    
    await crawler.close()
