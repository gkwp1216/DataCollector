"""RSS/Atom 피드 리더

feedparser를 사용하여 RSS/Atom 피드를 파싱하고 항목을 추출합니다.
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
import time

import aiohttp
import feedparser


class RSSReader:
    def __init__(self, timeout: int = 10, user_agent: str = None):
        self._timeout = timeout
        self._user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RSS Reader"
        self._session = None

    async def _ensure_session(self):
        if self._session is None:
            headers = {"User-Agent": self._user_agent}
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout),
                headers=headers
            )

    async def fetch_feed(self, url: str) -> Optional[str]:
        """피드 XML/HTML 가져오기"""
        await self._ensure_session()
        try:
            async with self._session.get(url) as resp:
                resp.raise_for_status()
                return await resp.text()
        except Exception as e:
            logging.error("피드 가져오기 실패: %s - %s", url, str(e))
            return None

    def parse_feed(self, content: str, feed_url: str = "") -> Dict:
        """피드 파싱 (feedparser 사용)"""
        feed = feedparser.parse(content)
        
        result = {
            "feed_url": feed_url,
            "title": feed.feed.get("title", ""),
            "description": feed.feed.get("description", ""),
            "link": feed.feed.get("link", ""),
            "updated": self._parse_date(feed.feed.get("updated_parsed")),
            "entries": []
        }
        
        for entry in feed.entries:
            item = self._parse_entry(entry)
            result["entries"].append(item)
        
        return result

    def _parse_entry(self, entry) -> Dict:
        """개별 피드 항목 파싱"""
        return {
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "description": self._clean_html(entry.get("description", "")),
            "summary": self._clean_html(entry.get("summary", "")),
            "author": entry.get("author", ""),
            "published": self._parse_date(entry.get("published_parsed")),
            "updated": self._parse_date(entry.get("updated_parsed")),
            "categories": [tag.get("term", "") for tag in entry.get("tags", [])],
            "id": entry.get("id", ""),
        }

    def _parse_date(self, date_tuple) -> Optional[str]:
        """날짜 튜플을 ISO 형식 문자열로 변환"""
        if date_tuple:
            try:
                dt = datetime(*date_tuple[:6])
                return dt.isoformat()
            except:
                return None
        return None

    def _clean_html(self, text: str) -> str:
        """HTML 태그 제거 (간단한 정제)"""
        if not text:
            return ""
        # feedparser가 이미 일부 정제를 하지만 추가 정제
        import re
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:500]  # 최대 500자

    async def fetch_and_parse(self, url: str) -> Optional[Dict]:
        """피드 가져오기 및 파싱"""
        content = await self.fetch_feed(url)
        if not content:
            return None
        return self.parse_feed(content, feed_url=url)

    async def close(self):
        if self._session is not None:
            await self._session.close()


# 편의 함수
async def fetch_rss(url: str, timeout: int = 10) -> Optional[Dict]:
    """RSS 피드 가져오기 (간단 인터페이스)"""
    reader = RSSReader(timeout=timeout)
    try:
        return await reader.fetch_and_parse(url)
    finally:
        await reader.close()
