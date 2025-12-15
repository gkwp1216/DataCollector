# 아키텍처 문서

Data Collector의 시스템 아키텍처와 설계 원칙을 설명합니다.

## 목차

- [시스템 개요](#시스템-개요)
- [아키텍처 다이어그램](#아키텍처-다이어그램)
- [핵심 컴포넌트](#핵심-컴포넌트)
- [데이터 흐름](#데이터-흐름)
- [설계 원칙](#설계-원칙)
- [확장성](#확장성)

---

## 시스템 개요

Data Collector는 **비동기 이벤트 기반 아키텍처**를 사용하는 웹 크롤링 시스템입니다.

### 주요 특징

- **비동기 I/O**: asyncio + aiohttp로 동시 처리
- **모듈화**: 독립적인 컴포넌트로 구성
- **확장 가능**: 플러그인 형태로 기능 추가 가능
- **설정 기반**: 코드 변경 없이 동작 변경 가능
- **에러 회복**: 재시도 및 fallback 메커니즘

---

## 아키텍처 다이어그램

### 전체 시스템 구조

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI Layer                            │
│  (main.py - 서브커맨드 기반: collect/schedule/config)        │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────┼────────────────────────────────────────┐
│                    │      Core Layer                         │
│                    │                                         │
│  ┌─────────────────▼─────────────┐                          │
│  │   ConfigLoader                 │  ◄── 환경 변수           │
│  │   - YAML 파싱                  │  ◄── 프로파일            │
│  │   - 환경 변수 오버라이드        │                          │
│  └────────────────────────────────┘                          │
│                    │                                         │
│  ┌─────────────────▼─────────────┐                          │
│  │   Logger                       │                          │
│  │   - 파일/콘솔 로깅             │                          │
│  │   - 로그 로테이션              │                          │
│  └────────────────────────────────┘                          │
└─────────────────────────────────────────────────────────────┘
                     │
┌────────────────────┼────────────────────────────────────────┐
│                    │    Collection Layer                     │
│                    │                                         │
│  ┌─────────────────▼─────────────┐                          │
│  │   AsyncCrawler                 │                          │
│  │   ├─ RobotsHandler            │  robots.txt 준수         │
│  │   ├─ DynamicPageHandler       │  JavaScript 렌더링       │
│  │   └─ ContentExtractor         │  본문 추출               │
│  └────────────────┬───────────────┘                          │
│                   │                                          │
│  ┌────────────────▼───────────────┐                          │
│  │   RSSReader                    │                          │
│  │   - feedparser 래퍼            │                          │
│  └────────────────┬───────────────┘                          │
└───────────────────┼──────────────────────────────────────────┘
                    │
┌───────────────────┼──────────────────────────────────────────┐
│                   │      Storage Layer                        │
│  ┌────────────────▼───────────────┐                          │
│  │   Database (SQLite)            │                          │
│  │   - 비동기 I/O (aiosqlite)     │                          │
│  │   - 중복 검사 (URL 해시)       │                          │
│  └────────────────────────────────┘                          │
└─────────────────────────────────────────────────────────────┘
                    │
┌───────────────────┼──────────────────────────────────────────┐
│                   │   Monitoring Layer                        │
│  ┌────────────────▼───────────────┐                          │
│  │   Notifier                     │                          │
│  │   ├─ Email (SMTP)             │                          │
│  │   ├─ Slack (Webhook)          │                          │
│  │   └─ Discord (Webhook)        │                          │
│  └────────────────┬───────────────┘                          │
│                   │                                          │
│  ┌────────────────▼───────────────┐                          │
│  │   MetricsCollector             │                          │
│  │   - 성공/실패 추적             │                          │
│  │   - 통계 계산                  │                          │
│  └────────────────────────────────┘                          │
└─────────────────────────────────────────────────────────────┘
                    │
┌───────────────────┼──────────────────────────────────────────┐
│                   │    Scheduler Layer                        │
│  ┌────────────────▼───────────────┐                          │
│  │   APScheduler                  │                          │
│  │   - Cron/Interval 트리거       │                          │
│  │   - 비동기 작업 실행           │                          │
│  └────────────────────────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

### 컴포넌트 의존성

```
┌────────────┐
│   main.py  │
└─────┬──────┘
      │
      ├──► ConfigLoader ──► dotenv
      │
      ├──► Logger ──► logging, RotatingFileHandler
      │
      ├──► AsyncCrawler ──┬──► aiohttp
      │                   ├──► BeautifulSoup4
      │                   ├──► RobotsHandler (urllib.robotparser)
      │                   ├──► DynamicPageHandler (Playwright)
      │                   └──► ContentExtractor (trafilatura)
      │
      ├──► RSSReader ──► feedparser, aiohttp
      │
      ├──► Database ──► aiosqlite
      │
      ├──► Notifier ──┬──► smtplib (email)
      │               ├──► aiohttp (Slack/Discord)
      │               └──► MetricsCollector
      │
      └──► APScheduler (optional)
```

---

## 핵심 컴포넌트

### 1. CLI Layer (main.py)

**책임:**
- 명령줄 인터페이스 제공
- 설정 로드 및 검증
- 작업 오케스트레이션

**구현:**
```python
# 서브커맨드 기반 CLI
- collect: 일회성 수집
- schedule: 주기적 수집
- config: 설정 관리
```

**패턴:** Command Pattern

---

### 2. ConfigLoader

**책임:**
- 설정 파일 (YAML) 로드
- 환경 변수 오버라이드
- 프로파일 관리 (dev/prod)

**설정 우선순위:**
```
환경 변수 > 프로파일 설정 > 기본 설정
```

**패턴:** Singleton, Builder

---

### 3. AsyncCrawler

**책임:**
- HTTP 요청 (비동기)
- HTML 파싱
- 에러 처리 및 재시도
- robots.txt 준수
- 동적 페이지 렌더링 (선택)
- 본문 추출 (선택)

**주요 기능:**
- **재시도 메커니즘**: 지수 백오프
- **타임아웃**: 설정 가능
- **User-Agent**: 커스터마이징
- **세션 관리**: aiohttp.ClientSession 재사용

**패턴:** Strategy Pattern (use_playwright, use_trafilatura)

---

### 4. RSSReader

**책임:**
- RSS/Atom 피드 파싱
- 항목 정규화

**구현:**
- feedparser 래퍼
- 비동기 HTTP 요청

---

### 5. Database

**책임:**
- SQLite 비동기 I/O
- 데이터 저장
- 중복 검사 (URL 해시)

**스키마:**
```sql
CREATE TABLE items (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE,
    url_hash TEXT UNIQUE,
    title TEXT,
    content TEXT,
    collected_at TEXT
);
```

**패턴:** Repository Pattern

---

### 6. RobotsHandler

**책임:**
- robots.txt 다운로드 및 파싱
- 크롤링 권한 확인
- 크롤 지연 권장값 조회
- 도메인별 캐싱

**구현:**
- urllib.robotparser 사용
- 1시간 캐시 (설정 가능)

---

### 7. DynamicPageHandler

**책임:**
- JavaScript 렌더링
- SPA (Single Page Application) 지원
- 스크린샷 캡처

**구현:**
- Playwright (Chromium) 사용
- Context Manager 지원

---

### 8. ContentExtractor

**책임:**
- HTML에서 본문 추출
- 메타데이터 추출
- 링크 및 이미지 수집

**구현:**
- trafilatura 사용
- Readability 알고리즘

---

### 9. Notifier

**책임:**
- 멀티 플랫폼 알림 전송
- 수집 완료/에러 알림
- 메트릭 리포팅

**지원 플랫폼:**
- Email (SMTP)
- Slack (Webhook)
- Discord (Webhook)

**패턴:** Observer Pattern

---

### 10. MetricsCollector

**책임:**
- 수집 통계 추적
- 성공률 계산
- 시간 측정

**메트릭:**
- total_requests
- successful_requests
- failed_requests
- skipped_requests
- success_rate
- total_duration
- avg_duration

---

## 데이터 흐름

### 일회성 수집 (collect)

```
1. CLI 시작
   ↓
2. ConfigLoader: 설정 로드
   ↓
3. Logger: 로거 초기화
   ↓
4. Database: DB 초기화
   ↓
5. AsyncCrawler 생성
   ├─ RobotsHandler 초기화
   ├─ DynamicPageHandler 초기화 (옵션)
   └─ ContentExtractor 초기화 (옵션)
   ↓
6. Notifier 생성 (옵션)
   ↓
7. MetricsCollector 시작
   ↓
8. URL 목록 순회
   ├─ 중복 검사 (Database)
   ├─ robots.txt 확인 (RobotsHandler)
   ├─ 크롤 지연 적용
   ├─ HTML 수집 (AsyncCrawler)
   │  ├─ 동적 렌더링 (DynamicPageHandler, 옵션)
   │  └─ 본문 추출 (ContentExtractor, 옵션)
   ├─ 데이터 저장 (Database)
   └─ 메트릭 기록 (MetricsCollector)
   ↓
9. RSS 피드 수집 (RSSReader)
   ↓
10. MetricsCollector 종료
   ↓
11. 알림 전송 (Notifier)
   ├─ 수집 완료 알림
   └─ 에러 알림 (실패율 임계값 초과 시)
   ↓
12. 리소스 정리
    ├─ AsyncCrawler.close()
    ├─ Notifier.close()
    └─ DynamicPageHandler.close()
```

### 스케줄러 모드 (schedule)

```
1. CLI 시작
   ↓
2. ConfigLoader: 스케줄러 설정 확인
   ↓
3. APScheduler 초기화
   ├─ Cron 트리거 또는
   └─ Interval 트리거
   ↓
4. 작업 등록
   ├─ run_collection() 함수
   └─ 트리거 설정
   ↓
5. 초기 실행 (즉시)
   ↓
6. 스케줄러 시작
   ↓
7. 무한 루프
   ├─ 트리거 대기
   ├─ run_collection() 실행
   ├─ (데이터 흐름은 "일회성 수집"과 동일)
   └─ 다음 트리거 대기
   ↓
8. Ctrl+C 시그널
   ↓
9. 스케줄러 종료
   ↓
10. 리소스 정리
```

---

## 설계 원칙

### 1. 비동기 우선 (Async-First)

모든 I/O 작업은 비동기로 구현:
- HTTP 요청 (aiohttp)
- 데이터베이스 (aiosqlite)
- 파일 I/O

**장점:**
- 높은 동시성
- 효율적인 리소스 사용
- 빠른 응답 시간

### 2. 모듈화 (Modularity)

각 컴포넌트는 독립적:
- 명확한 책임 분리
- 테스트 용이성
- 재사용 가능

**예시:**
```python
# 크롤러만 독립적으로 사용
from modules.crawler import AsyncCrawler

crawler = AsyncCrawler()
html = await crawler.fetch("https://example.com")
```

### 3. 설정 기반 (Configuration-Driven)

코드 변경 없이 동작 변경:
- YAML 설정 파일
- 환경 변수 지원
- 프로파일 시스템

### 4. 에러 회복 (Error Recovery)

실패에 강인한 시스템:
- 자동 재시도
- 지수 백오프
- 부분 실패 허용

### 5. 관찰 가능성 (Observability)

시스템 상태 모니터링:
- 구조화된 로깅
- 메트릭 수집
- 알림 시스템

---

## 동시성 모델

### asyncio 이벤트 루프

```python
# 단일 이벤트 루프에서 여러 작업 동시 실행
async def main():
    tasks = [
        collect_url(url1),
        collect_url(url2),
        collect_url(url3)
    ]
    results = await asyncio.gather(*tasks)
```

### Semaphore를 사용한 동시성 제어

```python
semaphore = asyncio.Semaphore(5)  # 최대 5개 동시 실행

async def collect_url(url):
    async with semaphore:
        # 크롤링 로직
        pass
```

**장점:**
- 서버 부하 방지
- 네트워크 대역폭 관리
- 안정적인 실행

---

## 확장성

### 수평 확장 (Horizontal Scaling)

여러 인스턴스 실행:
```bash
# 인스턴스 1
python main.py collect --url https://site1.com

# 인스턴스 2
python main.py collect --url https://site2.com
```

### 수직 확장 (Vertical Scaling)

동시성 증가:
```yaml
crawler:
  max_concurrent: 50  # 기본값: 5
```

### 플러그인 아키텍처

새 기능 추가:
```python
# 커스텀 extractor
class CustomExtractor:
    def extract(self, html):
        # 커스텀 로직
        pass

# AsyncCrawler에 주입
crawler = AsyncCrawler(extractor=CustomExtractor())
```

---

## 보안 고려사항

### 1. robots.txt 준수

윤리적 크롤링:
```python
handler = RobotsHandler()
if not await handler.can_fetch(url):
    return  # 크롤링 금지
```

### 2. Rate Limiting

서버 부하 방지:
```python
delay = await handler.get_crawl_delay(url)
await asyncio.sleep(delay)
```

### 3. 인증 정보 보호

환경 변수 사용:
```bash
# .env 파일 (git ignore)
EMAIL_PASSWORD=***
SLACK_WEBHOOK_URL=***
```

### 4. SQL Injection 방지

파라미터화된 쿼리:
```python
cursor.execute(
    "INSERT INTO items (url) VALUES (?)",
    (url,)
)
```

---

## 성능 최적화

### 1. 연결 풀링

```python
# aiohttp 세션 재사용
session = aiohttp.ClientSession()
# ... 여러 요청 ...
await session.close()
```

### 2. 캐싱

```python
# robots.txt 캐싱 (1시간)
# 도메인별로 캐시 유지
```

### 3. 비동기 I/O

```python
# 블로킹 작업 회피
await asyncio.sleep(1)  # ✓
time.sleep(1)           # ✗
```

### 4. 리소스 정리

```python
try:
    # 작업 수행
    pass
finally:
    await crawler.close()  # 항상 정리
```

---

## 테스트 전략

### 단위 테스트

```python
# tests/test_crawler.py
async def test_fetch():
    crawler = AsyncCrawler(timeout=5)
    html = await crawler.fetch("https://httpbin.org/html")
    assert html is not None
```

### 통합 테스트

```python
# tests/test_integration.py
async def test_full_pipeline():
    # 설정 → 크롤링 → 저장 → 알림
    pass
```

### 목킹 (Mocking)

```python
from unittest.mock import patch, AsyncMock

@patch('aiohttp.ClientSession.get')
async def test_fetch_with_mock(mock_get):
    mock_get.return_value.__aenter__.return_value.text = AsyncMock(return_value="<html>...")
    # 테스트 로직
```

---

## 배포 아키텍처

### Docker 컨테이너

```
┌─────────────────────────────────┐
│  Docker Container               │
│  ┌───────────────────────────┐  │
│  │  Data Collector           │  │
│  │  - Python 3.12+           │  │
│  │  - Dependencies           │  │
│  │  - Config                 │  │
│  └───────────────────────────┘  │
│                                 │
│  Volumes:                       │
│  - ./data:/app/data (DB)        │
│  - ./logs:/app/logs             │
│  - ./config.yaml:/app/config... │
└─────────────────────────────────┘
```

### CI/CD 파이프라인

```
GitHub Push
    ↓
GitHub Actions
    ├─ Test (pytest)
    ├─ Lint (flake8)
    ├─ Security (bandit)
    └─ Build Docker Image
         ↓
    Docker Hub
         ↓
    Production Deploy
```

---

## 미래 개선 사항

### 1. 분산 크롤링

- Celery + Redis로 작업 큐
- 여러 워커 노드

### 2. 고급 스토리지

- PostgreSQL 지원
- 엘라스틱서치 통합

### 3. 웹 UI

- 대시보드
- 실시간 모니터링
- 작업 관리

### 4. 머신러닝 통합

- 자동 콘텐츠 분류
- 중복 감지 개선

---

## 참고 자료

- **Python asyncio**: https://docs.python.org/3/library/asyncio.html
- **aiohttp**: https://docs.aiohttp.org/
- **Playwright**: https://playwright.dev/python/
- **trafilatura**: https://trafilatura.readthedocs.io/

---

## 문의 및 기여

- **이슈**: GitHub Issues
- **기여 가이드**: [`CONTRIBUTING.md`](../CONTRIBUTING.md)
- **API 문서**: [`docs/API.md`](API.md)
