import asyncio
import logging
from typing import Optional, Dict

import aiohttp
from bs4 import BeautifulSoup
from modules.content_extractor import ContentExtractor, extract_main_content
from modules.dynamic_page_handler import DynamicPageHandler
from modules.robots_handler import RobotsHandler


class AsyncCrawler:
    def __init__(
        self, 
        *, 
        timeout: int = 10, 
        max_retries: int = 3, 
        delay: float = 1.0, 
        user_agent: str = None, 
        use_trafilatura: bool = False,
        use_playwright: bool = False,
        playwright_headless: bool = True,
        respect_robots: bool = True,
        robots_cache_duration: int = 3600
    ):
        # ClientSession은 이벤트 루프가 실행중일 때 생성해야 하므로 지연 생성합니다.
        self._session = None
        self._timeout = timeout
        self._max_retries = max_retries
        self._delay = delay
        self._user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self._use_trafilatura = use_trafilatura
        self._extractor = ContentExtractor() if use_trafilatura else None
        self._use_playwright = use_playwright
        self._playwright_handler: Optional[DynamicPageHandler] = None
        self._playwright_headless = playwright_headless
        self._respect_robots = respect_robots
        self._robots_handler: Optional[RobotsHandler] = None
        self._robots_cache_duration = robots_cache_duration

    async def _ensure_session(self):
        if self._session is None:
            headers = {"User-Agent": self._user_agent}
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout),
                headers=headers
            )
    
    async def _ensure_playwright(self):
        """Playwright 핸들러 초기화"""
        if self._playwright_handler is None:
            self._playwright_handler = DynamicPageHandler(
                headless=self._playwright_headless,
                timeout=self._timeout * 1000,  # 초 -> 밀리초
                user_agent=self._user_agent
            )
            await self._playwright_handler.start()
    
    async def _ensure_robots_handler(self):
        """RobotsHandler 초기화"""
        if self._robots_handler is None:
            self._robots_handler = RobotsHandler(
                user_agent=self._user_agent,
                cache_duration=self._robots_cache_duration,
                respect_robots=self._respect_robots
            )

    async def fetch(self, url: str, use_playwright_override: Optional[bool] = None, check_robots: bool = True) -> Optional[str]:
        """
        URL을 가져오며, 실패 시 지수 백오프로 재시도합니다.
        
        Args:
            url: 가져올 URL
            use_playwright_override: Playwright 사용 여부 오버라이드 (None이면 기본 설정 사용)
            check_robots: robots.txt 확인 여부 (기본: True)
        
        Returns:
            HTML 문자열 또는 None
        """
        # robots.txt 확인
        if check_robots and self._respect_robots:
            await self._ensure_robots_handler()
            
            allowed = await self._robots_handler.can_fetch(url)
            if not allowed:
                logging.warning("robots.txt에 의해 차단됨: %s", url)
                return None
            
            # Crawl-delay 확인 및 적용
            crawl_delay = await self._robots_handler.get_crawl_delay(url)
            if crawl_delay and crawl_delay > self._delay:
                logging.debug("Crawl-delay 적용: %s초 (%s)", crawl_delay, url)
                await asyncio.sleep(crawl_delay)
        
        use_playwright = use_playwright_override if use_playwright_override is not None else self._use_playwright
        
        # Playwright 사용
        if use_playwright:
            return await self._fetch_with_playwright(url)
        
        # 기본 aiohttp 사용
        await self._ensure_session()
        
        for attempt in range(self._max_retries):
            try:
                # Rate limiting: 요청 간 지연
                if attempt > 0 or self._delay > 0:
                    await asyncio.sleep(self._delay * (2 ** attempt) if attempt > 0 else self._delay)
                
                async with self._session.get(url) as resp:
                    # HTTP 상태 코드별 처리
                    if resp.status == 404:
                        logging.warning("404 Not Found: %s", url)
                        return None
                    elif resp.status == 403:
                        logging.warning("403 Forbidden: %s", url)
                        return None
                    elif resp.status >= 500:
                        logging.warning("서버 오류 %d: %s (재시도 %d/%d)", resp.status, url, attempt + 1, self._max_retries)
                        if attempt < self._max_retries - 1:
                            continue
                        return None
                    
                    resp.raise_for_status()
                    text = await resp.text()
                    return text
                    
            except aiohttp.ClientError as e:
                logging.warning("네트워크 오류: %s - %s (재시도 %d/%d)", url, str(e), attempt + 1, self._max_retries)
                if attempt < self._max_retries - 1:
                    continue
                return None
            except asyncio.TimeoutError:
                logging.warning("타임아웃: %s (재시도 %d/%d)", url, attempt + 1, self._max_retries)
                if attempt < self._max_retries - 1:
                    continue
                return None
            except Exception as e:
                logging.error("예상치 못한 오류: %s - %s", url, str(e))
                return None
        
        return None
    
    async def _fetch_with_playwright(self, url: str) -> Optional[str]:
        """Playwright로 동적 페이지 가져오기"""
        await self._ensure_playwright()
        
        try:
            logging.info("Playwright로 페이지 수집: %s", url)
            result = await self._playwright_handler.fetch_page(
                url,
                wait_until="networkidle"
            )
            
            if result and result.get("html"):
                return result["html"]
            return None
            
        except Exception as e:
            logging.error("Playwright 수집 실패: %s - %s", url, str(e), exc_info=True)
            return None

    def parse_html(self, html: str, url: str = "") -> Dict[str, str]:
        """HTML 파싱: trafilatura 사용 여부에 따라 다른 방식 적용"""
        if self._use_trafilatura and self._extractor:
            # trafilatura로 고급 추출
            extracted = self._extractor.extract_content(html, url)
            return {
                "url": url,
                "title": extracted.get("title") or "",
                "content": extracted.get("text") or "",
                "author": extracted.get("author"),
                "date": extracted.get("date"),
                "description": extracted.get("description"),
                "metadata": extracted.get("metadata", {}),
                "images": extracted.get("images", []),
                "links": extracted.get("links", [])
            }
        else:
            # 기존 간단 파서
            soup = BeautifulSoup(html, "html.parser")
            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            # 본문 텍스트: body의 첫 200자
            body = soup.body.get_text(separator=" ", strip=True) if soup.body else ""
            snippet = (body[:200] + "...") if len(body) > 200 else body
            return {"url": url, "title": title, "content": snippet}

    async def fetch_and_parse(self, url: str, use_playwright_override: Optional[bool] = None, check_robots: bool = True) -> Optional[Dict[str, str]]:
        """
        URL 가져오기 및 파싱
        
        Args:
            url: 가져올 URL
            use_playwright_override: Playwright 사용 오버라이드
            check_robots: robots.txt 확인 여부
        
        Returns:
            파싱된 데이터 딕셔너리
        """
        html = await self.fetch(url, use_playwright_override=use_playwright_override, check_robots=check_robots)
        if not html:
            return None
        return self.parse_html(html, url=url)

    async def close(self):
        """리소스 정리"""
        if self._session is not None:
            await self._session.close()
        
        if self._playwright_handler is not None:
            await self._playwright_handler.close()
        
        if self._robots_handler is not None:
            await self._robots_handler.close()


# 편의 함수(동기 호출용)
def parse_html(html: str, url: str = "") -> Dict[str, str]:
    """독립형 파서 유틸리티(세션 없이 사용 가능)"""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    body = soup.body.get_text(separator=" ", strip=True) if soup.body else ""
    snippet = (body[:200] + "...") if len(body) > 200 else body
    return {"url": url, "title": title, "content": snippet}
