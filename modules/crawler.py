import asyncio
import logging
from typing import Optional, Dict

import aiohttp
from bs4 import BeautifulSoup


class AsyncCrawler:
    def __init__(self, *, timeout: int = 10, max_retries: int = 3, delay: float = 1.0, user_agent: str = None):
        # ClientSession은 이벤트 루프가 실행중일 때 생성해야 하므로 지연 생성합니다.
        self._session = None
        self._timeout = timeout
        self._max_retries = max_retries
        self._delay = delay
        self._user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    async def _ensure_session(self):
        if self._session is None:
            headers = {"User-Agent": self._user_agent}
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout),
                headers=headers
            )

    async def fetch(self, url: str) -> Optional[str]:
        """URL을 가져오며, 실패 시 지수 백오프로 재시도합니다."""
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

    def parse_html(self, html: str, url: str = "") -> Dict[str, str]:
        """간단 파서: title과 본문 일부 추출"""
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        # 본문 텍스트: body의 첫 200자
        body = soup.body.get_text(separator=" ", strip=True) if soup.body else ""
        snippet = (body[:200] + "...") if len(body) > 200 else body
        return {"url": url, "title": title, "content": snippet}

    async def fetch_and_parse(self, url: str) -> Optional[Dict[str, str]]:
        html = await self.fetch(url)
        if not html:
            return None
        return self.parse_html(html, url=url)

    async def close(self):
        if self._session is not None:
            await self._session.close()


# 편의 함수(동기 호출용)
def parse_html(html: str, url: str = "") -> Dict[str, str]:
    """독립형 파서 유틸리티(세션 없이 사용 가능)"""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    body = soup.body.get_text(separator=" ", strip=True) if soup.body else ""
    snippet = (body[:200] + "...") if len(body) > 200 else body
    return {"url": url, "title": title, "content": snippet}
