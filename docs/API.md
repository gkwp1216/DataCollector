# API 문서

Data Collector의 주요 모듈 및 API 사용법을 설명합니다.

## 목차

- [AsyncCrawler](#asynccrawler)
- [RSSReader](#rssreader)
- [Database](#database)
- [ConfigLoader](#configloader)
- [Logger](#logger)
- [Notifier](#notifier)
- [RobotsHandler](#robotshandler)
- [DynamicPageHandler](#dynamicpagehandler)
- [ContentExtractor](#contentextractor)

---

## AsyncCrawler

비동기 웹 크롤러. HTML 페이지를 수집하고 파싱합니다.

### 클래스: `AsyncCrawler`

**위치**: `modules/crawler.py`

#### 생성자

```python
AsyncCrawler(
    timeout: int = 10,
    max_retries: int = 3,
    delay: float = 1.0,
    user_agent: Optional[str] = None,
    use_playwright: bool = False,
    use_trafilatura: bool = False,
    respect_robots: bool = True
)
```

**매개변수:**
- `timeout` (int): HTTP 요청 타임아웃 (초). 기본값: 10
- `max_retries` (int): 실패 시 재시도 횟수. 기본값: 3
- `delay` (float): 재시도 간 지연 (초). 기본값: 1.0
- `user_agent` (str, optional): 사용자 정의 User-Agent
- `use_playwright` (bool): Playwright로 동적 페이지 렌더링. 기본값: False
- `use_trafilatura` (bool): trafilatura로 본문 추출. 기본값: False
- `respect_robots` (bool): robots.txt 준수. 기본값: True

#### 메서드

##### `fetch(url: str) -> Optional[str]`

URL에서 HTML을 가져옵니다.

```python
crawler = AsyncCrawler(timeout=15)
html = await crawler.fetch("https://example.com")
```

**반환**: HTML 문자열 또는 실패 시 None

##### `parse(html: str) -> Dict`

HTML을 파싱하여 데이터를 추출합니다.

```python
data = crawler.parse(html)
# {"title": "...", "content": "...", "links": [...]}
```

**반환**: 파싱된 데이터 딕셔너리

##### `fetch_and_parse(url: str) -> Optional[Dict]`

fetch와 parse를 결합한 편의 메서드.

```python
data = await crawler.fetch_and_parse("https://example.com")
```

##### `close()`

세션을 종료합니다.

```python
await crawler.close()
```

#### 사용 예제

```python
import asyncio
from modules.crawler import AsyncCrawler

async def main():
    crawler = AsyncCrawler(
        timeout=15,
        max_retries=5,
        use_trafilatura=True,
        respect_robots=True
    )
    
    try:
        # 단일 페이지 수집
        data = await crawler.fetch_and_parse("https://example.com")
        print(f"Title: {data['title']}")
        
        # 여러 페이지 동시 수집
        urls = ["https://example.com", "https://httpbin.org/html"]
        tasks = [crawler.fetch_and_parse(url) for url in urls]
        results = await asyncio.gather(*tasks)
        
    finally:
        await crawler.close()

asyncio.run(main())
```

---

## RSSReader

RSS 및 Atom 피드를 읽고 파싱합니다.

### 클래스: `RSSReader`

**위치**: `modules/rss_reader.py`

#### 생성자

```python
RSSReader(
    timeout: int = 10,
    user_agent: Optional[str] = None
)
```

#### 메서드

##### `fetch_feed(feed_url: str) -> List[Dict]`

RSS 피드를 가져와 항목을 파싱합니다.

```python
reader = RSSReader(timeout=15)
entries = await reader.fetch_feed("https://news.ycombinator.com/rss")

for entry in entries:
    print(f"{entry['title']}: {entry['link']}")
```

**반환**: 피드 항목 리스트

```python
[
    {
        "title": "Article Title",
        "link": "https://...",
        "content": "Description...",
        "published": "2025-12-15 10:00:00"
    },
    ...
]
```

#### 사용 예제

```python
from modules.rss_reader import RSSReader

async def fetch_news():
    reader = RSSReader()
    
    feeds = [
        "https://news.ycombinator.com/rss",
        "https://hnrss.org/newest?points=100"
    ]
    
    for feed_url in feeds:
        entries = await reader.fetch_feed(feed_url)
        print(f"Fetched {len(entries)} entries from {feed_url}")
```

---

## Database

SQLite 데이터베이스 인터페이스.

### 함수

**위치**: `modules/database.py`

#### `init_db(db_path: str)`

데이터베이스를 초기화하고 테이블을 생성합니다.

```python
await init_db("data.db")
```

#### `save_item(db_path: str, item: Dict)`

항목을 데이터베이스에 저장합니다.

```python
item = {
    "url": "https://example.com",
    "title": "Example",
    "content": "Content...",
    "collected_at": "2025-12-15 10:00:00"
}
await save_item("data.db", item)
```

#### `url_exists(db_path: str, url: str) -> bool`

URL이 이미 존재하는지 확인합니다 (중복 검사).

```python
if await url_exists("data.db", "https://example.com"):
    print("URL already collected")
```

#### 사용 예제

```python
from modules.database import init_db, save_item, url_exists

async def collect_with_dedup(urls):
    await init_db("data.db")
    
    for url in urls:
        if await url_exists("data.db", url):
            print(f"Skipping duplicate: {url}")
            continue
        
        # 수집 로직...
        item = {"url": url, "title": "...", "content": "..."}
        await save_item("data.db", item)
```

---

## ConfigLoader

설정 파일 및 환경 변수 로더.

### 클래스: `ConfigLoader`

**위치**: `modules/config_loader.py`

#### 생성자

```python
ConfigLoader(
    config_path: str = "config.yaml",
    profile: Optional[str] = None
)
```

#### 메서드

##### `get(key: str, default: Any = None) -> Any`

점 표기법으로 설정 값을 가져옵니다.

```python
config = ConfigLoader("config.yaml", profile="prod")

db_path = config.get("db.path", "data.db")
max_concurrent = config.get("crawler.max_concurrent", 5)
```

##### `to_dict() -> Dict`

전체 설정을 딕셔너리로 반환합니다.

```python
config_dict = config.to_dict()
print(config_dict)
```

#### 사용 예제

```python
from modules.config_loader import load_config

# 기본 설정
config = load_config("config.yaml")

# 프로파일 사용
prod_config = load_config("config.yaml", profile="prod")

# 환경 변수 오버라이드 자동 적용
db_path = config.get("db.path")  # DB_PATH 환경 변수가 우선
```

---

## Logger

구조화된 로깅 시스템.

### 함수

**위치**: `modules/logger.py`

#### `setup_logger(...) -> logging.Logger`

로거를 설정하고 반환합니다.

```python
logger = setup_logger(
    name="my_app",
    log_dir="logs",
    level="INFO",
    enable_file_logging=True,
    enable_console_logging=True,
    max_bytes=10485760,  # 10MB
    backup_count=5
)
```

**매개변수:**
- `name`: 로거 이름
- `log_dir`: 로그 파일 디렉터리
- `level`: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `enable_file_logging`: 파일 로깅 활성화
- `enable_console_logging`: 콘솔 로깅 활성화
- `max_bytes`: 로그 파일 최대 크기
- `backup_count`: 보관할 로테이션 파일 수

#### `get_logger(name: str) -> logging.Logger`

기존 로거를 가져옵니다.

```python
logger = get_logger("my_app")
logger.info("Message")
```

#### 사용 예제

```python
from modules.logger import setup_logger

logger = setup_logger(
    name="crawler",
    log_dir="logs",
    level="DEBUG",
    enable_file_logging=True
)

logger.debug("Detailed debug info")
logger.info("Normal operation")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)
```

---

## Notifier

멀티 플랫폼 알림 시스템.

### 클래스: `Notifier`

**위치**: `modules/notifier.py`

#### 생성자

```python
Notifier(
    email_config: Optional[Dict] = None,
    slack_config: Optional[Dict] = None,
    discord_config: Optional[Dict] = None,
    enabled: bool = True
)
```

**설정 예제:**

```python
email_config = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "username": "user@gmail.com",
    "password": "app_password",
    "from": "user@gmail.com",
    "to": "recipient@example.com"
}

slack_config = {
    "webhook_url": "https://hooks.slack.com/services/..."
}

discord_config = {
    "webhook_url": "https://discord.com/api/webhooks/..."
}

notifier = Notifier(
    email_config=email_config,
    slack_config=slack_config,
    discord_config=discord_config,
    enabled=True
)
```

#### 메서드

##### `send_email(subject: str, body: str, html: bool = False)`

이메일을 전송합니다.

```python
notifier.send_email(
    subject="Data Collection Complete",
    body="Successfully collected 100 items"
)
```

##### `send_slack(text: str, attachments: List = None, blocks: List = None)`

Slack 메시지를 전송합니다.

```python
await notifier.send_slack(
    text="Collection complete",
    attachments=[{
        "color": "good",
        "title": "Results",
        "text": "100 items collected"
    }]
)
```

##### `send_discord(content: str, embeds: List = None)`

Discord 메시지를 전송합니다.

```python
await notifier.send_discord(
    content="Collection complete",
    embeds=[{
        "title": "Results",
        "description": "100 items collected",
        "color": 0x00ff00
    }]
)
```

##### `notify_collection_complete(total, success, failed, skipped, duration)`

수집 완료 알림 (모든 플랫폼).

```python
await notifier.notify_collection_complete(
    total=100,
    success=95,
    failed=3,
    skipped=2,
    duration=120.5
)
```

##### `notify_error(error_message: str, details: str = None)`

에러 알림.

```python
await notifier.notify_error(
    error_message="Database connection failed",
    details="Timeout after 30 seconds"
)
```

### 클래스: `MetricsCollector`

수집 통계를 추적합니다.

#### 메서드

```python
metrics = MetricsCollector()

metrics.start()
metrics.record_success()
metrics.record_failure("Error message")
metrics.record_skip()
metrics.end()

# 메트릭 조회
stats = metrics.get_metrics()
print(metrics.get_summary())
```

---

## RobotsHandler

robots.txt 파일을 처리하고 크롤링 권한을 확인합니다.

### 클래스: `RobotsHandler`

**위치**: `modules/robots_handler.py`

#### 생성자

```python
RobotsHandler(
    user_agent: str = "DataCollectorBot/1.0",
    cache_expire: int = 3600
)
```

#### 메서드

##### `can_fetch(url: str, user_agent: str = None) -> bool`

URL 크롤링 권한을 확인합니다.

```python
handler = RobotsHandler()

if await handler.can_fetch("https://example.com/page"):
    # 크롤링 허용
    pass
else:
    # 크롤링 금지
    pass
```

##### `get_crawl_delay(url: str) -> Optional[float]`

권장 크롤 지연 시간을 가져옵니다.

```python
delay = await handler.get_crawl_delay("https://example.com")
if delay:
    await asyncio.sleep(delay)
```

#### 사용 예제

```python
from modules.robots_handler import RobotsHandler

async def ethical_crawl(urls):
    handler = RobotsHandler(user_agent="MyBot/1.0")
    
    for url in urls:
        # 권한 확인
        if not await handler.can_fetch(url):
            print(f"Blocked by robots.txt: {url}")
            continue
        
        # 크롤 지연 적용
        delay = await handler.get_crawl_delay(url)
        if delay:
            await asyncio.sleep(delay)
        
        # 크롤링 수행
        # ...
```

---

## DynamicPageHandler

Playwright를 사용한 JavaScript 렌더링.

### 클래스: `DynamicPageHandler`

**위치**: `modules/dynamic_page_handler.py`

#### 생성자

```python
DynamicPageHandler(
    headless: bool = True,
    timeout: int = 30000
)
```

#### 메서드

##### `fetch_page(...) -> str`

JavaScript가 실행된 후의 HTML을 가져옵니다.

```python
handler = DynamicPageHandler(headless=True)

await handler.start()
html = await handler.fetch_page(
    url="https://spa-site.com",
    wait_until="networkidle",
    wait_for_selector="#content",
    screenshot="screenshot.png"
)
await handler.close()
```

**매개변수:**
- `url`: 방문할 URL
- `wait_until`: 대기 조건 ("load", "domcontentloaded", "networkidle")
- `wait_for_selector`: 특정 요소 대기
- `screenshot`: 스크린샷 저장 경로
- `execute_js`: 실행할 JavaScript 코드

#### Context Manager 사용

```python
async with DynamicPageHandler() as handler:
    html = await handler.fetch_page("https://spa-site.com")
```

---

## ContentExtractor

trafilatura를 사용한 본문 추출.

### 클래스: `ContentExtractor`

**위치**: `modules/content_extractor.py`

#### 메서드

##### `extract(html: str, url: str = None, **kwargs) -> Dict`

HTML에서 본문과 메타데이터를 추출합니다.

```python
from modules.content_extractor import ContentExtractor

extractor = ContentExtractor()
result = extractor.extract(
    html=html_content,
    url="https://example.com",
    include_links=True,
    include_images=True
)

print(result["title"])
print(result["text"])
print(result["links"])
```

**반환 구조:**
```python
{
    "title": "Article Title",
    "author": "Author Name",
    "text": "Main content...",
    "date": "2025-12-15",
    "links": ["https://...", ...],
    "images": ["https://image1.jpg", ...],
    "language": "en"
}
```

---

## 통합 사용 예제

### 전체 파이프라인

```python
import asyncio
from modules.crawler import AsyncCrawler
from modules.database import init_db, save_item, url_exists
from modules.logger import setup_logger
from modules.config_loader import load_config
from modules.notifier import Notifier, MetricsCollector

async def main():
    # 설정 로드
    config = load_config("config.yaml", profile="prod")
    
    # 로거 설정
    logger = setup_logger(
        name="collector",
        log_dir=config.get("logging.log_dir", "logs"),
        level=config.get("logging.level", "INFO")
    )
    
    # 데이터베이스 초기화
    db_path = config.get("db.path", "data.db")
    await init_db(db_path)
    
    # 크롤러 설정
    crawler = AsyncCrawler(
        timeout=config.get("crawler.timeout", 10),
        max_retries=config.get("crawler.max_retries", 3),
        use_trafilatura=True,
        respect_robots=True
    )
    
    # 알림 설정
    notifier = Notifier(
        email_config=config.get("notifications.email"),
        enabled=config.get("notifications.enabled", False)
    )
    
    # 메트릭 수집
    metrics = MetricsCollector()
    metrics.start()
    
    try:
        urls = config.get("targets", [])
        
        for url in urls:
            # 중복 검사
            if await url_exists(db_path, url):
                logger.info(f"Skipping duplicate: {url}")
                metrics.record_skip()
                continue
            
            # 수집
            data = await crawler.fetch_and_parse(url)
            
            if data:
                await save_item(db_path, data)
                logger.info(f"Collected: {data['title']}")
                metrics.record_success()
            else:
                logger.error(f"Failed: {url}")
                metrics.record_failure(f"Failed to collect {url}")
        
        # 완료 알림
        metrics.end()
        collected_metrics = metrics.get_metrics()
        
        await notifier.notify_collection_complete(
            total=collected_metrics["total_requests"],
            success=collected_metrics["successful_requests"],
            failed=collected_metrics["failed_requests"],
            skipped=collected_metrics["skipped_requests"],
            duration=collected_metrics["total_duration"]
        )
        
    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)
        await notifier.notify_error("Collection failed", str(e))
        
    finally:
        await crawler.close()
        await notifier.close()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 에러 처리

모든 비동기 함수는 예외를 발생시킬 수 있습니다. 적절한 에러 처리를 권장합니다:

```python
try:
    data = await crawler.fetch_and_parse(url)
except asyncio.TimeoutError:
    logger.error(f"Timeout: {url}")
except aiohttp.ClientError as e:
    logger.error(f"HTTP error: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
```

---

## 타입 힌트

모든 공개 API는 타입 힌트를 제공합니다:

```python
from typing import Optional, Dict, List

async def fetch_and_parse(url: str) -> Optional[Dict[str, Any]]:
    ...
```

IDE의 자동 완성 및 타입 체크를 활용할 수 있습니다.

---

## 추가 정보

- **CLI 가이드**: [`CLI_GUIDE.md`](../CLI_GUIDE.md)
- **아키텍처**: [`ARCHITECTURE.md`](ARCHITECTURE.md)
- **기여 가이드**: [`CONTRIBUTING.md`](../CONTRIBUTING.md)
- **소스 코드**: `modules/` 디렉터리
