"""
Keyword Search Module
Supports Google, Naver, Bing search with image download capability
"""

import asyncio
import aiohttp
import re
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Set
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
from PIL import Image
import io

from modules.logger import get_logger

logger = get_logger(__name__)


class KeywordSearcher:
    """Keyword-based search and collection"""
    
    def __init__(
        self,
        save_images: bool = True,
        image_dir: str = "images",
        max_images: int = 10,
        timeout: int = 10,
        min_image_size: tuple = (200, 200),
        max_file_size: int = 10 * 1024 * 1024  # 10MB
    ):
        """
        Args:
            save_images: 이미지 저장 여부
            image_dir: 이미지 저장 디렉터리
            max_images: 페이지당 최대 이미지 수
            timeout: 타임아웃 (초)
            min_image_size: 최소 이미지 크기 (width, height)
            max_file_size: 최대 파일 크기 (bytes)
        """
        self.save_images = save_images
        self.image_dir = Path(image_dir)
        self.max_images = max_images
        self.timeout = timeout
        self.min_image_size = min_image_size
        self.max_file_size = max_file_size
        
        if save_images:
            self.image_dir.mkdir(exist_ok=True)
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.image_hashes: Set[str] = set()  # 중복 이미지 감지용
    
    async def __aenter__(self):
        """Context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            await self.session.close()
    
    async def search_google(self, keyword: str, num_results: int = 10) -> List[Dict]:
        """
        Google 검색
        
        Args:
            keyword: 검색 키워드
            num_results: 결과 수
            
        Returns:
            List of {url, title, snippet, images}
        """
        results = []
        
        try:
            search_url = f"https://www.google.com/search?q={quote(keyword)}&num={num_results}"
            
            async with self.session.get(search_url) as response:
                if response.status != 200:
                    logger.warning(f"Google search failed: {response.status}")
                    return results
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 검색 결과 파싱
                for g in soup.find_all('div', class_='g'):
                    title_elem = g.find('h3')
                    link_elem = g.find('a')
                    snippet_elem = g.find('div', class_=['VwiC3b', 'yXK7lf'])
                    
                    if title_elem and link_elem:
                        url = link_elem.get('href', '')
                        if url.startswith('http'):
                            result = {
                                'url': url,
                                'title': title_elem.get_text(strip=True),
                                'snippet': snippet_elem.get_text(strip=True) if snippet_elem else '',
                                'images': []
                            }
                            
                            # 이미지 수집 활성화 시
                            if self.save_images:
                                result['images'] = await self.extract_images(url)
                            
                            results.append(result)
                            
                            if len(results) >= num_results:
                                break
        
        except Exception as e:
            logger.error(f"Google search error for '{keyword}': {e}")
        
        return results
    
    async def search_naver(self, keyword: str, num_results: int = 10) -> List[Dict]:
        """
        Naver 검색
        
        Args:
            keyword: 검색 키워드
            num_results: 결과 수
            
        Returns:
            List of {url, title, snippet, images}
        """
        results = []
        
        try:
            search_url = f"https://search.naver.com/search.naver?query={quote(keyword)}"
            
            async with self.session.get(search_url) as response:
                if response.status != 200:
                    logger.warning(f"Naver search failed: {response.status}")
                    return results
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 검색 결과 파싱
                for item in soup.find_all('div', class_=['total_wrap', 'api_subject_bx']):
                    title_elem = item.find('a', class_=['total_tit', 'api_txt_lines'])
                    desc_elem = item.find('div', class_=['total_dsc', 'api_txt_lines'])
                    
                    if title_elem:
                        url = title_elem.get('href', '')
                        if url:
                            result = {
                                'url': url,
                                'title': title_elem.get_text(strip=True),
                                'snippet': desc_elem.get_text(strip=True) if desc_elem else '',
                                'images': []
                            }
                            
                            if self.save_images:
                                result['images'] = await self.extract_images(url)
                            
                            results.append(result)
                            
                            if len(results) >= num_results:
                                break
        
        except Exception as e:
            logger.error(f"Naver search error for '{keyword}': {e}")
        
        return results
    
    async def search_url_with_keyword(self, url: str, keyword: str) -> Dict:
        """
        특정 URL에서 키워드로 콘텐츠 검색
        
        Args:
            url: 대상 URL
            keyword: 검색 키워드
            
        Returns:
            {url, title, content, keyword_matches, images}
        """
        result = {
            'url': url,
            'title': '',
            'content': '',
            'keyword_matches': 0,
            'images': []
        }
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {url}: {response.status}")
                    return result
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 제목
                title = soup.find('title')
                if title:
                    result['title'] = title.get_text(strip=True)
                
                # 본문 텍스트
                for script in soup(['script', 'style']):
                    script.decompose()
                
                text = soup.get_text(separator=' ', strip=True)
                result['content'] = text[:1000]  # 처음 1000자
                
                # 키워드 매칭 횟수
                result['keyword_matches'] = len(re.findall(
                    re.escape(keyword), 
                    text, 
                    re.IGNORECASE
                ))
                
                # 이미지 수집
                if self.save_images:
                    result['images'] = await self.extract_images(url, soup)
        
        except Exception as e:
            logger.error(f"Error searching {url} with keyword '{keyword}': {e}")
        
        return result
    
    async def extract_images(
        self, 
        url: str, 
        soup: Optional[BeautifulSoup] = None
    ) -> List[str]:
        """
        페이지에서 콘텐츠 이미지 추출 및 다운로드 (지능형 필터링)
        
        Args:
            url: 페이지 URL
            soup: BeautifulSoup 객체 (없으면 새로 요청)
            
        Returns:
            저장된 이미지 경로 리스트
        """
        saved_images = []
        
        try:
            if soup is None:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        return saved_images
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
            
            # 모든 이미지 태그 찾기
            img_tags = soup.find_all('img', src=True)
            
            # 콘텐츠 이미지만 필터링
            content_images = []
            for img in img_tags:
                if self._is_content_image(img):
                    content_images.append(img)
            
            logger.info(f"Found {len(img_tags)} total images, {len(content_images)} content images")
            
            # 최대 이미지 수만큼 다운로드
            for idx, img in enumerate(content_images[:self.max_images]):
                img_url = img.get('src', '')
                
                # 상대 URL을 절대 URL로 변환
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    img_url = urljoin(url, img_url)
                elif not img_url.startswith('http'):
                    continue
                
                # data URL 스킵
                if img_url.startswith('data:'):
                    continue
                
                # 이미지 다운로드
                saved_path = await self.download_image(img_url, idx)
                if saved_path:
                    saved_images.append(saved_path)
        
        except Exception as e:
            logger.error(f"Error extracting images from {url}: {e}")
        
        return saved_images
    
    def _is_content_image(self, img_tag) -> bool:
        """
        콘텐츠 이미지인지 판별 (UI 요소, 광고 등 제외)
        
        Args:
            img_tag: BeautifulSoup img 태그
            
        Returns:
            콘텐츠 이미지 여부
        """
        # 제외할 CSS 클래스 키워드
        exclude_classes = [
            'icon', 'logo', 'nav', 'menu', 'ad', 'advertisement',
            'banner', 'thumb', 'avatar', 'profile', 'button',
            'badge', 'tag', 'social', 'share', 'emoji', 'sprite'
        ]
        
        # 제외할 ID 키워드
        exclude_ids = [
            'logo', 'nav', 'menu', 'ad', 'banner', 'header', 'footer'
        ]
        
        # CSS 클래스 체크
        img_classes = img_tag.get('class', [])
        if isinstance(img_classes, str):
            img_classes = [img_classes]
        
        for cls in img_classes:
            cls_lower = cls.lower()
            if any(exc in cls_lower for exc in exclude_classes):
                return False
        
        # ID 체크
        img_id = img_tag.get('id', '').lower()
        if any(exc in img_id for exc in exclude_ids):
            return False
        
        # 크기 체크 (너무 작은 이미지 제외)
        width = img_tag.get('width')
        height = img_tag.get('height')
        
        try:
            if width and int(width) < 100:
                return False
            if height and int(height) < 100:
                return False
        except (ValueError, TypeError):
            pass
        
        # alt 텍스트가 너무 짧거나 없으면 감점 (하지만 완전 제외는 안 함)
        alt = img_tag.get('alt', '')
        
        # src에서 파일명 추출하여 체크
        src = img_tag.get('src', '')
        src_lower = src.lower()
        
        # 제외할 파일명 패턴
        exclude_patterns = [
            'icon', 'logo', 'ad', 'banner', 'sprite', '1x1', 
            'pixel', 'blank', 'transparent', 'placeholder'
        ]
        
        if any(pattern in src_lower for pattern in exclude_patterns):
            return False
        
        # 콘텐츠 영역 내부 이미지인지 체크
        parent = img_tag.parent
        content_tags = ['article', 'main', 'content', 'post', 'entry']
        
        # 최대 5단계까지 부모 탐색
        for _ in range(5):
            if parent is None:
                break
            
            parent_class = parent.get('class', [])
            if isinstance(parent_class, str):
                parent_class = [parent_class]
            
            parent_id = parent.get('id', '')
            
            # 콘텐츠 영역에 포함되어 있으면 우선순위 높임
            for tag in content_tags:
                if (tag in str(parent_class).lower() or 
                    tag in parent_id.lower() or
                    parent.name == 'article' or
                    parent.name == 'main'):
                    return True
            
            parent = parent.parent
        
        # 기본적으로 허용 (너무 엄격하면 이미지를 못 찾을 수 있음)
        return True
    
    async def download_image(self, img_url: str, index: int) -> Optional[str]:
        """
        이미지 다운로드 및 품질 검증
        
        Args:
            img_url: 이미지 URL
            index: 파일명 인덱스
            
        Returns:
            저장된 파일 경로 (실패 시 None)
        """
        try:
            async with self.session.get(img_url) as response:
                if response.status != 200:
                    return None
                
                # 이미지 내용 읽기
                content = await response.read()
                
                # 파일 크기 체크
                if len(content) > self.max_file_size:
                    logger.debug(f"Image too large: {len(content)} bytes")
                    return None
                
                if len(content) < 1024:  # 1KB 미만은 의심스러움
                    logger.debug(f"Image too small: {len(content)} bytes")
                    return None
                
                # 중복 이미지 체크
                img_hash = self._calculate_image_hash(content)
                if img_hash in self.image_hashes:
                    logger.debug(f"Duplicate image detected: {img_url}")
                    return None
                
                # 이미지 품질 검증 (실제 이미지인지, 크기는 적절한지)
                try:
                    img = Image.open(io.BytesIO(content))
                    width, height = img.size
                    
                    # 최소 크기 체크
                    if width < self.min_image_size[0] or height < self.min_image_size[1]:
                        logger.debug(f"Image too small: {width}x{height}")
                        return None
                    
                    # 이상한 비율 체크 (너무 가늘거나 긴 이미지는 배너일 가능성)
                    aspect_ratio = max(width, height) / min(width, height)
                    if aspect_ratio > 10:
                        logger.debug(f"Suspicious aspect ratio: {aspect_ratio}")
                        return None
                    
                except Exception as e:
                    logger.debug(f"Invalid image format: {e}")
                    return None
                
                # 확장자 추출
                ext = '.jpg'
                content_type = response.headers.get('Content-Type', '')
                if 'png' in content_type:
                    ext = '.png'
                elif 'gif' in content_type:
                    ext = '.gif'
                elif 'webp' in content_type:
                    ext = '.webp'
                
                # 파일명 생성
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"img_{timestamp}_{index}{ext}"
                filepath = self.image_dir / filename
                
                # 이미지 저장
                with open(filepath, 'wb') as f:
                    f.write(content)
                
                # 중복 방지를 위해 해시 저장
                self.image_hashes.add(img_hash)
                
                logger.info(f"Image saved: {filepath} ({width}x{height}, {len(content)} bytes)")
                return str(filepath)
        
        except Exception as e:
            logger.error(f"Error downloading image {img_url}: {e}")
            return None
    
    def _calculate_image_hash(self, content: bytes) -> str:
        """
        이미지 내용의 해시 계산 (중복 감지용)
        
        Args:
            content: 이미지 바이너리 데이터
            
        Returns:
            SHA256 해시 문자열
        """
        return hashlib.sha256(content).hexdigest()
    
    async def batch_search(
        self,
        urls: List[str],
        keyword: str,
        min_matches: int = 1
    ) -> List[Dict]:
        """
        여러 URL에서 키워드 일괄 검색
        
        Args:
            urls: URL 리스트
            keyword: 검색 키워드
            min_matches: 최소 매칭 횟수 (필터링)
            
        Returns:
            매칭된 결과 리스트
        """
        tasks = [self.search_url_with_keyword(url, keyword) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리 및 필터링
        filtered_results = []
        for result in results:
            if isinstance(result, dict) and result.get('keyword_matches', 0) >= min_matches:
                filtered_results.append(result)
        
        return filtered_results


# 편의 함수
async def search_google(keyword: str, num_results: int = 10, save_images: bool = False) -> List[Dict]:
    """Google 검색 편의 함수"""
    async with KeywordSearcher(save_images=save_images) as searcher:
        return await searcher.search_google(keyword, num_results)


async def search_naver(keyword: str, num_results: int = 10, save_images: bool = False) -> List[Dict]:
    """Naver 검색 편의 함수"""
    async with KeywordSearcher(save_images=save_images) as searcher:
        return await searcher.search_naver(keyword, num_results)


async def search_with_keyword(url: str, keyword: str, save_images: bool = True) -> Dict:
    """URL + 키워드 검색 편의 함수"""
    async with KeywordSearcher(save_images=save_images) as searcher:
        return await searcher.search_url_with_keyword(url, keyword)
