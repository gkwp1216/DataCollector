"""
콘텐츠 추출 모듈
- trafilatura를 사용한 본문 추출
- 메타데이터 추출 (og:tags, twitter:card)
- 이미지 및 링크 추출
"""

import trafilatura
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class ContentExtractor:
    """고급 콘텐츠 추출기"""
    
    def __init__(self, include_comments: bool = False, include_tables: bool = True):
        """
        Args:
            include_comments: 댓글 포함 여부
            include_tables: 테이블 포함 여부
        """
        self.include_comments = include_comments
        self.include_tables = include_tables
    
    def extract_content(self, html: str, url: Optional[str] = None) -> Dict[str, Any]:
        """
        HTML에서 콘텐츠 추출
        
        Args:
            html: HTML 문자열
            url: 원본 URL (선택)
        
        Returns:
            추출된 콘텐츠 딕셔너리
        """
        result = {
            "text": None,
            "title": None,
            "author": None,
            "date": None,
            "description": None,
            "language": None,
            "metadata": {},
            "images": [],
            "links": []
        }
        
        try:
            # trafilatura로 본문 추출
            result["text"] = trafilatura.extract(
                html,
                include_comments=self.include_comments,
                include_tables=self.include_tables,
                include_images=False,
                include_links=False,
                url=url
            )
            
            # 메타데이터 추출
            metadata = trafilatura.extract_metadata(html)
            if metadata:
                result["title"] = metadata.title
                result["author"] = metadata.author
                result["date"] = metadata.date
                result["description"] = metadata.description
                result["language"] = metadata.language
                result["metadata"] = {
                    "sitename": metadata.sitename,
                    "categories": metadata.categories,
                    "tags": metadata.tags,
                }
            
            # BeautifulSoup으로 추가 정보 추출
            soup = BeautifulSoup(html, 'lxml')
            
            # Open Graph 메타데이터
            result["metadata"]["og"] = self._extract_og_tags(soup)
            
            # Twitter Card 메타데이터
            result["metadata"]["twitter"] = self._extract_twitter_tags(soup)
            
            # 이미지 추출
            result["images"] = self._extract_images(soup, url)
            
            # 링크 추출
            result["links"] = self._extract_links(soup, url)
            
        except Exception as e:
            logger.error(f"콘텐츠 추출 실패: {e}", exc_info=True)
        
        return result
    
    def _extract_og_tags(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Open Graph 메타데이터 추출"""
        og_data = {}
        og_tags = soup.find_all("meta", property=lambda x: x and x.startswith("og:"))
        
        for tag in og_tags:
            property_name = tag.get("property", "").replace("og:", "")
            content = tag.get("content", "")
            if property_name and content:
                og_data[property_name] = content
        
        return og_data
    
    def _extract_twitter_tags(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Twitter Card 메타데이터 추출"""
        twitter_data = {}
        twitter_tags = soup.find_all("meta", attrs={"name": lambda x: x and x.startswith("twitter:")})
        
        for tag in twitter_tags:
            name = tag.get("name", "").replace("twitter:", "")
            content = tag.get("content", "")
            if name and content:
                twitter_data[name] = content
        
        return twitter_data
    
    def _extract_images(self, soup: BeautifulSoup, base_url: Optional[str] = None) -> List[Dict[str, str]]:
        """이미지 추출"""
        images = []
        
        for img in soup.find_all("img"):
            src = img.get("src", "")
            alt = img.get("alt", "")
            title = img.get("title", "")
            
            if src:
                # 상대 경로를 절대 경로로 변환 (간단 버전)
                if base_url and src.startswith("/"):
                    from urllib.parse import urljoin
                    src = urljoin(base_url, src)
                
                images.append({
                    "src": src,
                    "alt": alt,
                    "title": title
                })
        
        return images[:10]  # 상위 10개만
    
    def _extract_links(self, soup: BeautifulSoup, base_url: Optional[str] = None) -> List[Dict[str, str]]:
        """링크 추출"""
        links = []
        
        # article 또는 main 태그 내의 링크만 추출 (본문 링크)
        content_area = soup.find("article") or soup.find("main") or soup
        
        for link in content_area.find_all("a", href=True):
            href = link.get("href", "")
            text = link.get_text(strip=True)
            title = link.get("title", "")
            
            if href and not href.startswith("#"):
                # 상대 경로를 절대 경로로 변환
                if base_url and href.startswith("/"):
                    from urllib.parse import urljoin
                    href = urljoin(base_url, href)
                
                links.append({
                    "href": href,
                    "text": text,
                    "title": title
                })
        
        return links[:20]  # 상위 20개만
    
    def extract_readability(self, html: str) -> Dict[str, Any]:
        """
        Readability 알고리즘으로 본문 추출 (trafilatura 대체)
        
        Args:
            html: HTML 문자열
        
        Returns:
            추출된 콘텐츠
        """
        try:
            # trafilatura의 bare_extraction 사용 (더 많은 정보)
            data = trafilatura.bare_extraction(
                html,
                include_comments=self.include_comments,
                include_tables=self.include_tables,
                include_images=True,
                include_links=True
            )
            
            return data or {}
            
        except Exception as e:
            logger.error(f"Readability 추출 실패: {e}", exc_info=True)
            return {}


def extract_main_content(html: str, url: Optional[str] = None) -> Optional[str]:
    """
    간단한 본문 추출 함수 (편의 함수)
    
    Args:
        html: HTML 문자열
        url: 원본 URL
    
    Returns:
        추출된 본문 텍스트
    """
    try:
        return trafilatura.extract(html, url=url)
    except Exception as e:
        logger.error(f"본문 추출 실패: {e}")
        return None


def extract_metadata(html: str) -> Optional[Dict[str, Any]]:
    """
    메타데이터만 추출 (편의 함수)
    
    Args:
        html: HTML 문자열
    
    Returns:
        메타데이터 딕셔너리
    """
    try:
        metadata = trafilatura.extract_metadata(html)
        if metadata:
            return {
                "title": metadata.title,
                "author": metadata.author,
                "date": metadata.date,
                "description": metadata.description,
                "sitename": metadata.sitename,
                "categories": metadata.categories,
                "tags": metadata.tags,
                "language": metadata.language
            }
    except Exception as e:
        logger.error(f"메타데이터 추출 실패: {e}")
    
    return None
