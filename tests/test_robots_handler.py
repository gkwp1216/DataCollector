"""robots.txt 핸들러 테스트"""
import pytest
from modules.robots_handler import RobotsHandler, check_robots_allowed


@pytest.mark.asyncio
async def test_robots_handler_basic():
    """기본 robots.txt 확인 테스트"""
    handler = RobotsHandler(user_agent="TestBot")
    
    try:
        # httpbin.org는 robots.txt가 없어서 모든 것 허용
        allowed = await handler.can_fetch("https://httpbin.org/html")
        assert allowed is True
        print("✓ robots.txt 없는 사이트: 허용")
        
        # Google은 robots.txt가 있음
        google_allowed = await handler.can_fetch("https://www.google.com/search")
        print(f"✓ Google 검색: {'허용' if google_allowed else '차단'}")
        
    finally:
        await handler.close()


@pytest.mark.asyncio
async def test_robots_cache():
    """robots.txt 캐싱 테스트"""
    handler = RobotsHandler(user_agent="TestBot", cache_duration=3600)
    
    try:
        url = "https://httpbin.org/html"
        
        # 첫 번째 요청 (캐시 없음)
        allowed1 = await handler.can_fetch(url)
        
        # 두 번째 요청 (캐시 사용)
        allowed2 = await handler.can_fetch(url)
        
        assert allowed1 == allowed2
        
        # 캐시 정보 확인
        cache_info = handler.get_cache_info()
        assert "https://httpbin.org" in cache_info
        assert cache_info["https://httpbin.org"]["valid"] is True
        
        print(f"✓ 캐시 정보: {len(cache_info)}개 도메인")
        print(f"✓ 캐시 유효성: {cache_info['https://httpbin.org']['valid']}")
        
    finally:
        await handler.close()


@pytest.mark.asyncio
async def test_crawl_delay():
    """Crawl-delay 확인 테스트"""
    handler = RobotsHandler(user_agent="TestBot")
    
    try:
        # httpbin.org는 robots.txt가 없어서 None 반환
        delay = await handler.get_crawl_delay("https://httpbin.org/html")
        assert delay is None
        print("✓ Crawl-delay: None (robots.txt 없음)")
        
    finally:
        await handler.close()


@pytest.mark.asyncio
async def test_respect_robots_false():
    """robots.txt 무시 테스트"""
    handler = RobotsHandler(user_agent="TestBot", respect_robots=False)
    
    try:
        # respect_robots=False이면 항상 허용
        allowed = await handler.can_fetch("https://www.google.com/admin")
        assert allowed is True
        print("✓ respect_robots=False: 항상 허용")
        
    finally:
        await handler.close()


@pytest.mark.asyncio
async def test_different_user_agents():
    """User-Agent별 규칙 테스트"""
    handler = RobotsHandler()
    
    try:
        url = "https://httpbin.org/html"
        
        # 다른 User-Agent로 확인
        allowed1 = await handler.can_fetch(url, user_agent="Googlebot")
        allowed2 = await handler.can_fetch(url, user_agent="*")
        
        # httpbin은 robots.txt가 없어서 모두 허용
        assert allowed1 is True
        assert allowed2 is True
        
        print("✓ User-Agent별 확인 정상")
        
    finally:
        await handler.close()


@pytest.mark.asyncio
async def test_cache_clear():
    """캐시 삭제 테스트"""
    handler = RobotsHandler(user_agent="TestBot")
    
    try:
        # 캐시 생성
        await handler.can_fetch("https://httpbin.org/html")
        await handler.can_fetch("https://example.com")
        
        cache_info_before = handler.get_cache_info()
        assert len(cache_info_before) == 2
        
        # 특정 도메인 캐시 삭제
        handler.clear_cache("https://httpbin.org")
        cache_info_after = handler.get_cache_info()
        assert len(cache_info_after) == 1
        
        # 전체 캐시 삭제
        handler.clear_cache()
        cache_info_final = handler.get_cache_info()
        assert len(cache_info_final) == 0
        
        print("✓ 캐시 삭제 정상")
        
    finally:
        await handler.close()


@pytest.mark.asyncio
async def test_check_robots_allowed_function():
    """편의 함수 테스트"""
    allowed = await check_robots_allowed(
        "https://httpbin.org/html",
        user_agent="TestBot"
    )
    
    assert allowed is True
    print("✓ 편의 함수 정상 동작")


@pytest.mark.asyncio
async def test_invalid_url():
    """잘못된 URL 처리 테스트"""
    handler = RobotsHandler(user_agent="TestBot")
    
    try:
        # 존재하지 않는 도메인 (robots.txt 가져오기 실패)
        allowed = await handler.can_fetch("https://this-domain-does-not-exist-12345.com/page")
        
        # 오류 발생 시 허용 (안전한 기본값)
        assert allowed is True
        print("✓ 잘못된 URL: 허용 (안전한 기본값)")
        
    finally:
        await handler.close()


if __name__ == "__main__":
    import asyncio
    
    print("robots.txt 핸들러 테스트 실행 중...")
    
    print("\n1. 기본 robots.txt 확인")
    asyncio.run(test_robots_handler_basic())
    
    print("\n2. robots.txt 캐싱")
    asyncio.run(test_robots_cache())
    
    print("\n3. Crawl-delay 확인")
    asyncio.run(test_crawl_delay())
    
    print("\n4. robots.txt 무시 (respect_robots=False)")
    asyncio.run(test_respect_robots_false())
    
    print("\n5. User-Agent별 규칙")
    asyncio.run(test_different_user_agents())
    
    print("\n6. 캐시 삭제")
    asyncio.run(test_cache_clear())
    
    print("\n7. 편의 함수")
    asyncio.run(test_check_robots_allowed_function())
    
    print("\n8. 잘못된 URL 처리")
    asyncio.run(test_invalid_url())
    
    print("\n모든 테스트 통과!")
