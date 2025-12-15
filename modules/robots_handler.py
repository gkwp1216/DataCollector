"""
robots.txt 핸들러 모듈
- robots.txt 파싱 및 캐싱
- 크롤링 허용 여부 확인
- Crawl-delay 준수
- User-agent별 규칙 처리
"""

import logging
from typing import Optional, Dict
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import aiohttp
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RobotsHandler:
    """robots.txt 처리 핸들러"""
    
    def __init__(
        self,
        user_agent: str = "*",
        cache_duration: int = 3600,  # 1시간
        respect_robots: bool = True
    ):
        """
        Args:
            user_agent: User-Agent 문자열
            cache_duration: 캐시 유효 시간 (초)
            respect_robots: robots.txt 준수 여부
        """
        self.user_agent = user_agent
        self.cache_duration = cache_duration
        self.respect_robots = respect_robots
        
        # 캐시: {domain: {"parser": RobotFileParser, "timestamp": datetime}}
        self._cache: Dict[str, Dict] = {}
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _ensure_session(self):
        """HTTP 세션 초기화"""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
    
    async def close(self):
        """세션 종료"""
        if self._session is not None:
            await self._session.close()
            self._session = None
    
    def _get_robots_url(self, url: str) -> str:
        """URL에서 robots.txt URL 생성"""
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        return robots_url
    
    def _get_domain(self, url: str) -> str:
        """URL에서 도메인 추출"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def _is_cache_valid(self, domain: str) -> bool:
        """캐시가 유효한지 확인"""
        if domain not in self._cache:
            return False
        
        cache_entry = self._cache[domain]
        timestamp = cache_entry.get("timestamp")
        
        if timestamp is None:
            return False
        
        age = (datetime.now() - timestamp).total_seconds()
        return age < self.cache_duration
    
    async def _fetch_robots_txt(self, robots_url: str) -> Optional[str]:
        """robots.txt 파일 다운로드"""
        await self._ensure_session()
        
        try:
            async with self._session.get(robots_url) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    logger.debug("robots.txt 다운로드 성공: %s", robots_url)
                    return content
                elif resp.status == 404:
                    logger.debug("robots.txt 없음: %s", robots_url)
                    return None
                else:
                    logger.warning("robots.txt 다운로드 실패 (%d): %s", resp.status, robots_url)
                    return None
        except Exception as e:
            logger.error("robots.txt 다운로드 오류: %s - %s", robots_url, str(e))
            return None
    
    async def _get_parser(self, url: str) -> Optional[RobotFileParser]:
        """RobotFileParser 가져오기 (캐시 활용)"""
        domain = self._get_domain(url)
        
        # 캐시 확인
        if self._is_cache_valid(domain):
            logger.debug("캐시된 robots.txt 사용: %s", domain)
            return self._cache[domain]["parser"]
        
        # robots.txt 다운로드
        robots_url = self._get_robots_url(url)
        robots_content = await self._fetch_robots_txt(robots_url)
        
        # 파서 생성
        parser = RobotFileParser()
        parser.set_url(robots_url)
        
        if robots_content:
            parser.parse(robots_content.splitlines())
        else:
            # robots.txt가 없으면 모든 것 허용
            parser.parse([])
        
        # 캐시 저장
        self._cache[domain] = {
            "parser": parser,
            "timestamp": datetime.now()
        }
        
        logger.info("robots.txt 파싱 완료 및 캐시 저장: %s", domain)
        return parser
    
    async def can_fetch(self, url: str, user_agent: Optional[str] = None) -> bool:
        """
        URL 크롤링 허용 여부 확인
        
        Args:
            url: 확인할 URL
            user_agent: User-Agent (None이면 기본값 사용)
        
        Returns:
            True: 크롤링 허용, False: 크롤링 금지
        """
        if not self.respect_robots:
            return True
        
        try:
            parser = await self._get_parser(url)
            
            if parser is None:
                # robots.txt를 가져올 수 없으면 허용
                return True
            
            ua = user_agent or self.user_agent
            allowed = parser.can_fetch(ua, url)
            
            if not allowed:
                logger.info("robots.txt에 의해 차단됨: %s (User-Agent: %s)", url, ua)
            
            return allowed
            
        except Exception as e:
            logger.error("robots.txt 확인 오류: %s - %s", url, str(e))
            # 오류 발생 시 크롤링 허용 (안전한 기본값)
            return True
    
    async def get_crawl_delay(self, url: str, user_agent: Optional[str] = None) -> Optional[float]:
        """
        Crawl-delay 값 가져오기
        
        Args:
            url: URL
            user_agent: User-Agent
        
        Returns:
            Crawl-delay 값 (초) 또는 None
        """
        if not self.respect_robots:
            return None
        
        try:
            parser = await self._get_parser(url)
            
            if parser is None:
                return None
            
            ua = user_agent or self.user_agent
            delay = parser.crawl_delay(ua)
            
            if delay:
                logger.debug("Crawl-delay: %s초 (%s)", delay, url)
            
            return delay
            
        except Exception as e:
            logger.error("Crawl-delay 확인 오류: %s - %s", url, str(e))
            return None
    
    async def get_request_rate(self, url: str, user_agent: Optional[str] = None) -> Optional[tuple]:
        """
        Request-rate 값 가져오기 (요청 수, 시간)
        
        Args:
            url: URL
            user_agent: User-Agent
        
        Returns:
            (요청 수, 시간) 튜플 또는 None
        """
        if not self.respect_robots:
            return None
        
        try:
            parser = await self._get_parser(url)
            
            if parser is None:
                return None
            
            ua = user_agent or self.user_agent
            rate = parser.request_rate(ua)
            
            if rate:
                logger.debug("Request-rate: %s (%s)", rate, url)
            
            return rate
            
        except Exception as e:
            logger.error("Request-rate 확인 오류: %s - %s", url, str(e))
            return None
    
    def clear_cache(self, domain: Optional[str] = None):
        """
        캐시 삭제
        
        Args:
            domain: 특정 도메인 (None이면 전체 삭제)
        """
        if domain:
            if domain in self._cache:
                del self._cache[domain]
                logger.debug("캐시 삭제: %s", domain)
        else:
            self._cache.clear()
            logger.debug("전체 캐시 삭제")
    
    def get_cache_info(self) -> Dict[str, Dict]:
        """
        캐시 정보 반환
        
        Returns:
            {domain: {"url": str, "age": float, "valid": bool}}
        """
        info = {}
        now = datetime.now()
        
        for domain, entry in self._cache.items():
            timestamp = entry.get("timestamp")
            age = (now - timestamp).total_seconds() if timestamp else None
            
            info[domain] = {
                "url": domain,
                "age": age,
                "valid": self._is_cache_valid(domain)
            }
        
        return info


# 편의 함수
async def check_robots_allowed(
    url: str,
    user_agent: str = "*",
    respect_robots: bool = True
) -> bool:
    """
    robots.txt 확인 (간단 인터페이스)
    
    Args:
        url: 확인할 URL
        user_agent: User-Agent
        respect_robots: robots.txt 준수 여부
    
    Returns:
        True: 허용, False: 차단
    """
    handler = RobotsHandler(user_agent=user_agent, respect_robots=respect_robots)
    try:
        return await handler.can_fetch(url)
    finally:
        await handler.close()
