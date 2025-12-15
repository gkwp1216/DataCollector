"""
Keyword Search Module
Supports Google, Naver, Bing search with image download capability
"""

import asyncio
import aiohttp
import re
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup

from modules.logger import get_logger

logger = get_logger(__name__)


class KeywordSearcher:
    """Keyword-based search and collection"""
    
    def __init__(
        self,
        save_images: bool = True,
        image_dir: str = "images",
        max_images: int = 10,
        timeout: int = 10
    ):
        """
        Args:
            save_images: 이미지 저장 여부
            image_dir: 이미지 저장 디렉터리
            max_images: 페이지당 최대 이미지 수
            timeout: 타임아웃 (초)
        """
        self.save_images = save_images
        self.image_dir = Path(image_dir)
        self.max_images = max_images
        self.timeout = timeout
        
        if save_images:
            self.image_dir.mkdir(exist_ok=True)
        
        self.session: Optional[aiohttp.ClientSession] = None
    
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
        페이지에서 이미지 추출 및 다운로드
        
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
            
            # 이미지 태그 찾기
            img_tags = soup.find_all('img', src=True)
            
            for idx, img in enumerate(img_tags[:self.max_images]):
                img_url = img.get('src', '')
                
                # 상대 URL을 절대 URL로 변환
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    img_url = urljoin(url, img_url)
                elif not img_url.startswith('http'):
                    continue
                
                # 이미지 다운로드
                saved_path = await self.download_image(img_url, idx)
                if saved_path:
                    saved_images.append(saved_path)
        
        except Exception as e:
            logger.error(f"Error extracting images from {url}: {e}")
        
        return saved_images
    
    async def download_image(self, img_url: str, index: int) -> Optional[str]:
        """
        이미지 다운로드
        
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
                content = await response.read()
                with open(filepath, 'wb') as f:
                    f.write(content)
                
                logger.info(f"Image saved: {filepath}")
                return str(filepath)
        
        except Exception as e:
            logger.error(f"Error downloading image {img_url}: {e}")
            return None
    
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
