# DataCollector

비동기 웹 크롤러 및 RSS 리더 프로젝트입니다. 동시성 처리, 에러 복구, 중복 검사, 스케줄링 기능을 제공합니다.

## 주요 기능

- ⚡ **비동기 크롤링**: asyncio + aiohttp 기반 고성능 수집
- 🔄 **RSS/Atom 지원**: feedparser 통합
- 🛡️ **에러 처리**: 지수 백오프 재시도, HTTP 상태 코드별 처리
- 🎯 **중복 방지**: URL 해시 기반 중복 검사
- ⏰ **스케줄러**: 주기적 자동 실행 (cron/interval)
- 📊 **SQLite 저장**: 비동기 DB 저장

## 빠른 시작 (Windows - PowerShell)

```powershell
# 가상환경 생성
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 의존성 설치
pip install -r requirements.txt

# 일회성 실행
python main.py

# 스케줄러 모드 (백그라운드 주기 실행)
python main.py --schedule

# 테스트 실행
python -m pytest -q
```

## 사용법

### 일회성 실행
```powershell
python main.py
```

### 스케줄러 모드
```powershell
# config.yaml에서 scheduler.enabled=true 설정 후
python main.py --schedule
```

### 설정 파일 지정
```powershell
python main.py --config custom_config.yaml
```

## 설정 (config.yaml)

```yaml
# 데이터베이스
db:
  path: data.db

# 크롤러 설정
crawler:
  max_concurrent: 5          # 최대 동시 요청 수
  timeout: 10                # 타임아웃 (초)
  max_retries: 3             # 재시도 횟수
  delay_between_requests: 1.0  # 요청 간 지연 (초)
  skip_duplicates: true      # 중복 URL 건너뛰기

# 수집 대상 (HTML)
targets:
  - https://example.com

# RSS 피드
rss_feeds:
  - https://news.ycombinator.com/rss

# 스케줄러
scheduler:
  enabled: false             # 활성화 여부
  interval_minutes: 60       # 분 단위 간격
  cron: "0 */6 * * *"        # 또는 cron 표현식
```

## 파일 구조

- `main.py`: 진입점 및 스케줄러
- `modules/crawler.py`: 비동기 크롤러 (에러 처리, 재시도)
- `modules/rss_reader.py`: RSS/Atom 피드 리더
- `modules/database.py`: SQLite DB 인터페이스 (중복 검사)
- `config.yaml`: 설정 파일
- `requirements.txt`: 패키지 목록
- `tests/`: 단위 테스트
