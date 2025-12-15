"""동적 페이지 핸들러 테스트"""
import pytest
from modules.dynamic_page_handler import DynamicPageHandler, fetch_dynamic_page


@pytest.mark.asyncio
async def test_dynamic_page_handler_basic():
    """기본 동적 페이지 수집 테스트"""
    async with DynamicPageHandler(headless=True) as handler:
        # Example.com은 정적 페이지지만 Playwright 동작 테스트용
        result = await handler.fetch_page(
            "https://example.com",
            wait_until="domcontentloaded"
        )
        
        assert result is not None
        assert result["html"] is not None
        assert "Example Domain" in result["html"]
        assert result["title"] == "Example Domain"
        assert result["url"] == "https://example.com/"
        print(f"✓ 페이지 제목: {result['title']}")


@pytest.mark.asyncio
async def test_fetch_dynamic_page_function():
    """편의 함수 테스트"""
    html = await fetch_dynamic_page(
        "https://example.com",
        headless=True,
        wait_until="domcontentloaded"
    )
    
    assert html is not None
    assert "Example Domain" in html
    print("✓ 편의 함수 정상 동작")


@pytest.mark.asyncio
async def test_dynamic_page_with_js():
    """JavaScript 실행 테스트"""
    async with DynamicPageHandler(headless=True) as handler:
        result = await handler.fetch_page(
            "https://example.com",
            wait_until="domcontentloaded",
            execute_js="document.title"
        )
        
        assert result is not None
        assert result["js_result"] == "Example Domain"
        print(f"✓ JavaScript 실행 결과: {result['js_result']}")


@pytest.mark.asyncio
async def test_multiple_pages():
    """여러 페이지 동시 수집 테스트"""
    urls = [
        "https://example.com",
        "https://httpbin.org/html"
    ]
    
    async with DynamicPageHandler(headless=True) as handler:
        results = await handler.fetch_pages(urls, max_concurrent=2)
        
        assert len(results) == 2
        assert all(r["html"] is not None for r in results)
        print(f"✓ {len(results)}개 페이지 동시 수집 성공")


@pytest.mark.asyncio
async def test_timeout_handling():
    """타임아웃 처리 테스트"""
    async with DynamicPageHandler(headless=True, timeout=1000) as handler:
        # 존재하지 않는 URL
        result = await handler.fetch_page(
            "https://httpbin.org/delay/10",  # 10초 지연
            wait_until="load"
        )
        
        # 타임아웃으로 실패해야 함
        assert result["html"] is None
        print("✓ 타임아웃 정상 처리")


@pytest.mark.asyncio
async def test_404_handling():
    """404 에러 처리 테스트"""
    async with DynamicPageHandler(headless=True) as handler:
        result = await handler.fetch_page(
            "https://httpbin.org/status/404",
            wait_until="domcontentloaded"
        )
        
        # 404는 html이 None이어야 함
        assert result["html"] is None
        print("✓ 404 에러 정상 처리")


if __name__ == "__main__":
    import asyncio
    
    print("동적 페이지 핸들러 테스트 실행 중...")
    
    print("\n1. 기본 동적 페이지 수집")
    asyncio.run(test_dynamic_page_handler_basic())
    
    print("\n2. 편의 함수 테스트")
    asyncio.run(test_fetch_dynamic_page_function())
    
    print("\n3. JavaScript 실행")
    asyncio.run(test_dynamic_page_with_js())
    
    print("\n4. 여러 페이지 동시 수집")
    asyncio.run(test_multiple_pages())
    
    print("\n5. 타임아웃 처리")
    asyncio.run(test_timeout_handling())
    
    print("\n6. 404 에러 처리")
    asyncio.run(test_404_handling())
    
    print("\n모든 테스트 통과!")
