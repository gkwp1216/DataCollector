import asyncio
from typing import Optional, Dict

import aiohttp
from bs4 import BeautifulSoup


class AsyncCrawler:
    def __init__(self, *, timeout: int = 10):
        # ClientSession은 이벤트 루프가 실행중일 때 생성해야 하므로 지연 생성합니다.
        self._session = None
        self._timeout = timeout

    async def _ensure_session(self):
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self._timeout))

    async def fetch(self, url: str) -> Optional[str]:
        try:
            await self._ensure_session()
            async with self._session.get(url) as resp:
                resp.raise_for_status()
                text = await resp.text()
                return text
        except Exception:
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
