"""
동적 페이지 핸들러 모듈
- Playwright를 사용한 JavaScript 렌더링
- 스크린샷 캡처 옵션
- 대기 전략 (네트워크 idle, 특정 선택자)
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


class DynamicPageHandler:
    """Playwright 기반 동적 페이지 핸들러"""
    
    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30000,  # 밀리초
        viewport: Optional[Dict[str, int]] = None,
        user_agent: Optional[str] = None
    ):
        """
        Args:
            headless: 헤드리스 모드 여부
            timeout: 페이지 로드 타임아웃 (밀리초)
            viewport: 뷰포트 크기 {"width": 1280, "height": 720}
            user_agent: User-Agent 문자열
        """
        self.headless = headless
        self.timeout = timeout
        self.viewport = viewport or {"width": 1280, "height": 720}
        self.user_agent = user_agent
        
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
    
    async def __aenter__(self):
        """Context manager 진입"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료"""
        await self.close()
    
    async def start(self):
        """브라우저 시작"""
        if self._browser is not None:
            return
        
        try:
            self._playwright = await async_playwright().start()
            
            # Chromium 브라우저 시작
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                ]
            )
            
            # 브라우저 컨텍스트 생성
            context_options = {
                "viewport": self.viewport,
                "user_agent": self.user_agent,
            } if self.user_agent else {
                "viewport": self.viewport
            }
            
            self._context = await self._browser.new_context(**context_options)
            
            # 타임아웃 설정
            self._context.set_default_timeout(self.timeout)
            self._context.set_default_navigation_timeout(self.timeout)
            
            logger.info("Playwright 브라우저 시작됨 (headless=%s)", self.headless)
            
        except Exception as e:
            logger.error("브라우저 시작 실패: %s", str(e), exc_info=True)
            raise
    
    async def close(self):
        """브라우저 종료"""
        try:
            if self._context:
                await self._context.close()
                self._context = None
            
            if self._browser:
                await self._browser.close()
                self._browser = None
            
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
            
            logger.info("Playwright 브라우저 종료됨")
            
        except Exception as e:
            logger.error("브라우저 종료 중 오류: %s", str(e))
    
    async def fetch_page(
        self,
        url: str,
        wait_until: str = "networkidle",
        wait_for_selector: Optional[str] = None,
        screenshot: bool = False,
        screenshot_path: Optional[str] = None,
        execute_js: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        동적 페이지 가져오기
        
        Args:
            url: 페이지 URL
            wait_until: 대기 전략 ("load", "domcontentloaded", "networkidle", "commit")
            wait_for_selector: 대기할 CSS 선택자 (선택)
            screenshot: 스크린샷 캡처 여부
            screenshot_path: 스크린샷 저장 경로
            execute_js: 실행할 JavaScript 코드 (선택)
        
        Returns:
            {
                "html": str,
                "url": str,
                "title": str,
                "screenshot": bytes or None,
                "js_result": Any or None
            }
        """
        if self._context is None:
            await self.start()
        
        page: Optional[Page] = None
        
        try:
            # 새 페이지 생성
            page = await self._context.new_page()
            
            logger.debug("페이지 로드 중: %s (wait_until=%s)", url, wait_until)
            
            # 페이지 이동
            response = await page.goto(url, wait_until=wait_until)
            
            if response is None:
                logger.warning("페이지 응답 없음: %s", url)
                return {"html": None, "url": url, "title": None, "screenshot": None, "js_result": None}
            
            # HTTP 상태 코드 확인
            if response.status >= 400:
                logger.warning("HTTP 오류: %d - %s", response.status, url)
                return {"html": None, "url": url, "title": None, "screenshot": None, "js_result": None}
            
            # 선택자 대기 (선택 사항)
            if wait_for_selector:
                try:
                    await page.wait_for_selector(wait_for_selector, timeout=10000)
                    logger.debug("선택자 발견: %s", wait_for_selector)
                except PlaywrightTimeoutError:
                    logger.warning("선택자 타임아웃: %s", wait_for_selector)
            
            # JavaScript 실행 (선택 사항)
            js_result = None
            if execute_js:
                try:
                    js_result = await page.evaluate(execute_js)
                    logger.debug("JavaScript 실행 완료")
                except Exception as e:
                    logger.warning("JavaScript 실행 실패: %s", str(e))
            
            # HTML 가져오기
            html = await page.content()
            title = await page.title()
            final_url = page.url
            
            # 스크린샷 (선택 사항)
            screenshot_bytes = None
            if screenshot:
                try:
                    screenshot_bytes = await page.screenshot(
                        path=screenshot_path,
                        full_page=True
                    )
                    if screenshot_path:
                        logger.debug("스크린샷 저장: %s", screenshot_path)
                except Exception as e:
                    logger.warning("스크린샷 실패: %s", str(e))
            
            logger.info("✓ 동적 페이지 수집 성공: %s", title)
            
            return {
                "html": html,
                "url": final_url,
                "title": title,
                "screenshot": screenshot_bytes,
                "js_result": js_result
            }
            
        except PlaywrightTimeoutError:
            logger.error("페이지 로드 타임아웃: %s", url)
            return {"html": None, "url": url, "title": None, "screenshot": None, "js_result": None}
        
        except Exception as e:
            logger.error("페이지 수집 실패: %s - %s", url, str(e), exc_info=True)
            return {"html": None, "url": url, "title": None, "screenshot": None, "js_result": None}
        
        finally:
            if page:
                await page.close()
    
    async def fetch_pages(
        self,
        urls: List[str],
        max_concurrent: int = 3,
        **fetch_options
    ) -> List[Dict[str, Any]]:
        """
        여러 동적 페이지 동시 수집
        
        Args:
            urls: URL 목록
            max_concurrent: 최대 동시 수집 수
            **fetch_options: fetch_page에 전달할 옵션
        
        Returns:
            수집 결과 리스트
        """
        if self._context is None:
            await self.start()
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_with_semaphore(url: str) -> Dict[str, Any]:
            async with semaphore:
                return await self.fetch_page(url, **fetch_options)
        
        tasks = [fetch_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("수집 실패 [%s]: %s", urls[i], str(result))
                processed_results.append({
                    "html": None,
                    "url": urls[i],
                    "title": None,
                    "screenshot": None,
                    "js_result": None
                })
            else:
                processed_results.append(result)
        
        return processed_results


# 편의 함수
async def fetch_dynamic_page(
    url: str,
    headless: bool = True,
    timeout: int = 30000,
    wait_until: str = "networkidle",
    screenshot: bool = False,
    **kwargs
) -> Optional[str]:
    """
    동적 페이지 HTML 가져오기 (간단 인터페이스)
    
    Args:
        url: 페이지 URL
        headless: 헤드리스 모드
        timeout: 타임아웃 (밀리초)
        wait_until: 대기 전략
        screenshot: 스크린샷 캡처 여부
        **kwargs: 추가 옵션
    
    Returns:
        HTML 문자열 또는 None
    """
    async with DynamicPageHandler(headless=headless, timeout=timeout) as handler:
        result = await handler.fetch_page(url, wait_until=wait_until, screenshot=screenshot, **kwargs)
        return result.get("html")
