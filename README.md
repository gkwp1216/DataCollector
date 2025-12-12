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

### 프로파일 사용
```powershell
# 개발 환경 설정으로 실행
python main.py --profile dev

# 프로덕션 환경 설정으로 실행
python main.py --profile prod

# 환경 변수로 프로파일 지정
$env:APP_PROFILE="dev"
python main.py
```

### 환경 변수 사용
```powershell
# .env 파일 생성 (선택 사항)
cp .env.example .env
# .env 파일 편집하여 설정 변경

# 환경 변수는 config.yaml 설정을 오버라이드합니다
$env:CRAWLER_MAX_CONCURRENT="10"
$env:LOG_LEVEL="DEBUG"
python main.py
```

### 스케줄러 모드
```powershell
# config.yaml에서 scheduler.enabled=true 설정 후
python main.py --schedule

# 프로파일과 함께 사용
python main.py --schedule --profile prod
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

# 로깅
logging:
  log_dir: logs              # 로그 파일 디렉터리
  level: INFO                # 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  enable_file_logging: true  # 파일 로깅 활성화
  enable_console_logging: true  # 콘솔 로깅 활성화
  max_bytes: 10485760        # 로그 파일 최대 크기 (10MB)
  backup_count: 5            # 로테이션된 로그 파일 보관 개수

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

## 로깅

프로젝트는 3가지 로그 파일을 생성합니다:

1. **collector.log**: 모든 로그 (INFO 레벨 이상)
2. **error.log**: 에러만 분리 기록
3. **collector_YYYY-MM-DD.log**: 일별 로그

로그 파일은 10MB 크기 제한으로 자동 로테이션되며, 최근 5개 파일을 보관합니다.

```powershell
# 로그 확인
Get-Content logs/collector.log -Tail 50
Get-Content logs/error.log
```

## 고급 설정

### 프로파일 시스템

프로파일을 사용하면 환경별로 다른 설정을 쉽게 관리할 수 있습니다.

- `config.yaml`: 기본 설정
- `config.dev.yaml`: 개발 환경 (DEBUG 로그, 낮은 동시성)
- `config.prod.yaml`: 프로덕션 환경 (INFO 로그, 높은 동시성)

프로파일 파일은 기본 설정을 오버라이드합니다.

### 환경 변수 지원

`.env` 파일 또는 시스템 환경 변수로 설정을 오버라이드할 수 있습니다.

**우선순위**: 환경 변수 > 프로파일 설정 > 기본 설정

```bash
# .env 파일 예시
DB_PATH=production.db
LOG_LEVEL=INFO
CRAWLER_MAX_CONCURRENT=10
TARGETS=https://site1.com,https://site2.com
```

### 타겟별 상세 설정

`config.yaml`에서 타겟별로 개별 설정을 지정할 수 있습니다.

```yaml
target_configs:
  - url: https://example.com
    name: "Example Site"
    timeout: 15
    max_retries: 5
    delay: 2.0
    headers:
      User-Agent: "Custom Agent"
```

## 파일 구조

- `main.py`: 진입점 및 스케줄러
- `modules/crawler.py`: 비동기 크롤러 (에러 처리, 재시도)
- `modules/rss_reader.py`: RSS/Atom 피드 리더
- `modules/database.py`: SQLite DB 인터페이스 (중복 검사)
- `modules/logger.py`: 로깅 모듈 (파일/콘솔, 로그 로테이션)
- `modules/config_loader.py`: 설정 로더 (환경 변수, 프로파일 지원)
- `config.yaml`: 기본 설정 파일
- `config.dev.yaml`: 개발 환경 설정
- `config.prod.yaml`: 프로덕션 환경 설정
- `.env.example`: 환경 변수 템플릿
- `requirements.txt`: 패키지 목록
- `tests/`: 단위 테스트
- `logs/`: 로그 파일 디렉터리

## Docker 사용법

### Docker 빌드 및 실행

```powershell
# Docker Desktop 실행 확인

# 이미지 빌드
docker build -t data-collector:latest .

# 컨테이너 실행 (일회성)
docker run --rm data-collector:latest

# 백그라운드 실행
docker run -d --name collector data-collector:latest

# 볼륨 마운트 (데이터 및 로그 유지)
docker run -d --name collector `
  -v ${PWD}/data.db:/app/data.db `
  -v ${PWD}/logs:/app/logs `
  data-collector:latest

# 환경 변수 전달
docker run -d --name collector `
  -e APP_PROFILE=prod `
  -e LOG_LEVEL=INFO `
  -e CRAWLER_MAX_CONCURRENT=10 `
  data-collector:latest

# 로그 확인
docker logs collector
docker logs -f collector  # 실시간

# 컨테이너 중지/시작/삭제
docker stop collector
docker start collector
docker rm collector
```

### Docker Compose 사용

```powershell
# 서비스 시작 (백그라운드)
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 서비스 중지
docker-compose down

# 서비스 재시작
docker-compose restart

# 이미지 재빌드 후 시작
docker-compose up -d --build
```

### Docker Compose 설정 커스터마이징

`docker-compose.yml`에서 다음을 수정할 수 있습니다:

```yaml
# 환경 변수 변경
environment:
  - APP_PROFILE=prod
  - LOG_LEVEL=INFO
  - CRAWLER_MAX_CONCURRENT=10

# 리소스 제한 조정
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 1G
```

### 프로덕션 배포 예시

```powershell
# 프로덕션 설정으로 빌드
docker build -t data-collector:prod .

# 스케줄러 모드로 실행
docker run -d --name collector_prod `
  --restart unless-stopped `
  -v ${PWD}/data.db:/app/data.db `
  -v ${PWD}/logs:/app/logs `
  -v ${PWD}/config.prod.yaml:/app/config.prod.yaml `
  -e APP_PROFILE=prod `
  data-collector:prod `
  python main.py --schedule --profile prod
```

### 트러블슈팅

```powershell
# 컨테이너 내부 접속
docker exec -it collector /bin/bash

# 컨테이너 상태 확인
docker ps -a
docker inspect collector

# 이미지 목록
docker images

# 사용하지 않는 이미지/컨테이너 정리
docker system prune -a
```
