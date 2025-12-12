# TODO - Data Collector 프로젝트

작성일: 2025-11-18

## 🎯 현재 상태

### ✅ 완료된 기능
- [x] 기본 프로젝트 구조 (venv, requirements.txt, config.yaml)
- [x] AsyncCrawler 클래스 (비동기 fetch, HTML 파싱)
- [x] SQLite 데이터베이스 (init_db, save_item)
- [x] 단위 테스트 (파서 테스트, DB 테스트)
- [x] 기본 로깅 설정
- [x] README 작성

### ✅ 최근 완료
- [x] 동시성 처리 (asyncio.gather + Semaphore)
- [x] 에러 처리 및 재시도 로직 (지수 백오프)
- [x] Rate Limiting (요청 간 지연, User-Agent)
- [x] 중복 검사 (URL 해시 + DB 확인)
- [x] RSS/Atom 피드 리더 (feedparser 통합)
- [x] 스케줄러 (APScheduler, cron/interval 지원)

### 🚧 진행 중 (2025-12-13)
- [x] 로깅 개선 (2.4) - 파일 로깅, 로그 로테이션, 레벨별 분리 ✅ 완료

### 📅 이번 주 계획
1. ~~**로깅 개선** (우선순위: 최고) - 15-20분~~ ✅ **완료**
2. **설정 파일 확장** - 타겟별 설정, 환경 변수 지원 (다음 작업)
3. **본문 정제 개선** - trafilatura 통합

### 📅 다음 주 계획
1. Docker 컨테이너화
2. CI/CD 파이프라인 기본 설정
3. 블로그 콘텐츠 분석 모듈 시작

---

## 📋 다음 작업 목록

### 1단계: 핵심 기능 강화 (우선순위: 높음)

#### 
- [x] asyncio.gather를 사용한 병렬 URL 수집
- [x] asyncio.Semaphore로 동시 요청 수 제한 (예: 최대 5개)
- [x] 워커 풀 패턴 구현 (선택)
- [x] 진행률 표시 (수집 완료/전체)

**예상 시간:** 20분  
**파일:** `main.py`, `modules/crawler.py`

#### 1.2 에러 처리 및 재시도 로직
- [x] 지수 백오프를 사용한 재시도 (최대 3회)
- [x] HTTP 상태 코드별 처리 (4xx, 5xx)
- [x] 타임아웃 설정 강화
- [x] 실패한 URL 로깅 및 별도 저장

**예상 시간:** 15분  
**파일:** `modules/crawler.py`

#### 1.3 Rate Limiting
- [x] 요청 간 지연 시간 설정 (config에서 설정 가능)
- [x] 도메인별 rate limit 관리
- [x] User-Agent 설정

**예상 시간:** 10분  
**파일:** `modules/crawler.py`, `config.yaml`

#### 1.4 중복 검사
- [x] URL 해시를 사용한 중복 수집 방지
- [x] DB에서 기존 URL 확인 후 건너뛰기
- [x] 중복 체크 옵션 (config에서 설정)

**예상 시간:** 10분  
**파일:** `modules/database.py`, `main.py`

---

### 2단계: 실용성 향상 (우선순위: 중간)

#### 2.1 RSS/Atom 피드 리더 구현
- [x] feedparser 라이브러리 추가
- [x] RSS/Atom 피드 파싱 함수
- [x] 피드 항목별 메타데이터 추출 (published_date, author 등)
- [x] RSS 전용 테스트 작성

**예상 시간:** 25분  
**파일:** `modules/rss_reader.py`, `requirements.txt`, `tests/test_rss_reader.py`

#### 2.2 스케줄러 추가
- [x] APScheduler 라이브러리 추가
- [x] 주기적 실행 설정 (cron 스타일)
- [x] 스케줄 설정을 config.yaml에 추가
- [x] 백그라운드 실행 모드

**예상 시간:** 15분  
**파일:** `main.py`, `requirements.txt`, `config.yaml`

#### 2.3 설정 파일 확장
- [ ] 타겟별 설정 (URL, 파서 규칙, 헤더 등)
- [ ] 여러 프로파일 지원 (dev, prod)
- [ ] 환경 변수 지원 (.env 파일)
- [ ] 설정 검증 함수

**예상 시간:** 20분  
**파일:** `config.yaml`, 새 파일 `config_loader.py`

#### 2.4 로깅 개선
- [x] 파일 로깅 (logs/ 디렉터리) ✅
- [x] 로그 로테이션 (일별/크기별) ✅
- [x] 로그 레벨별 분리 (debug, info, error) ✅
- [x] 구조화된 로깅 (JSON 형식 선택) ✅

**완료:** 2025-12-13  
**실제 소요 시간:** 약 20분  
**파일:** `main.py`, `modules/logger.py`, `config.yaml`, `test_logging.py`

**구현 내용:**
- `modules/logger.py`: 종합 로깅 모듈 생성
  - RotatingFileHandler: 10MB 제한, 5개 백업
  - 3가지 로그 파일: collector.log (전체), error.log (에러만), collector_YYYY-MM-DD.log (일별)
  - 콘솔 + 파일 동시 출력
  - 편의 함수: log_collection_start/success/failure/error/stats
- `main.py`: 로깅 시스템 통합
  - config.yaml에서 로깅 설정 읽기
  - 모든 logging 호출을 logger로 변경
  - initialize_logger() 함수로 설정 기반 초기화
- `config.yaml`: 로깅 설정 추가
  - log_dir, level, max_bytes, backup_count 등
- `test_logging.py`: 로깅 테스트 스크립트 생성

**테스트 결과:**
- ✅ 콘솔 로깅 정상 작동
- ✅ 파일 로깅 (logs/collector.log) 정상
- ✅ 에러 로그 분리 (logs/error.log) 정상
- ✅ 일별 로그 (logs/collector_2025-12-13.log) 정상
- ✅ 크롤러 통합 테스트 통과 (50개 항목 수집 성공)

---

### 3단계: 고급 기능 (우선순위: 낮음)

#### 3.1 동적 페이지 지원
- [ ] Playwright 또는 Selenium 통합
- [ ] JavaScript 렌더링 지원
- [ ] 스크린샷 캡처 옵션
- [ ] 동적 페이지 전용 설정

**예상 시간:** 40분  
**파일:** `modules/crawler.py`, `requirements.txt`

#### 3.2 robots.txt 준수
- [ ] urllib.robotparser 통합
- [ ] robots.txt 캐싱
- [ ] 수집 허용 여부 확인
- [ ] 우회 옵션 (주의해서 사용)

**예상 시간:** 20분  
**파일:** `modules/crawler.py`

#### 3.3 데이터 정제 및 추출 개선
- [ ] readability-lxml 또는 trafilatura 통합
- [ ] 본문 자동 추출
- [ ] 메타데이터 추출 (og:tags, twitter:card)
- [ ] 이미지/링크 추출

**예상 시간:** 30분  
**파일:** `modules/crawler.py`, `requirements.txt`

#### 3.4 알림 및 모니터링
- [ ] 수집 완료 알림 (이메일, Slack, Discord)
- [ ] 에러 알림
- [ ] 메트릭 수집 (수집 수, 실패율, 처리 시간)
- [ ] 대시보드 (선택)

**예상 시간:** 45분  
**파일:** 새 파일 `modules/notifier.py`, `config.yaml`

---

### 4단계: 배포 및 운영 (우선순위: 낮음)

#### 4.1 CLI 인터페이스 개선
- [ ] argparse로 명령줄 옵션 추가
- [ ] 하위 명령어 (collect, schedule, test 등)
- [ ] 상세 도움말
- [ ] 진행률 표시 (tqdm)

**예상 시간:** 25분  
**파일:** `main.py`, 새 파일 `cli.py`

#### 4.2 Docker 컨테이너화
- [ ] Dockerfile 작성
- [ ] docker-compose.yml (DB 포함 옵션)
- [ ] 최적화된 이미지 (멀티 스테이지 빌드)
- [ ] 실행 가이드

**예상 시간:** 30분  
**파일:** 새 파일 `Dockerfile`, `docker-compose.yml`

#### 4.3 CI/CD 파이프라인
- [ ] GitHub Actions 워크플로우
- [ ] 자동 테스트 실행
- [ ] 린팅 (flake8, black)
- [ ] 자동 배포 (선택)

**예상 시간:** 35분  
**파일:** `.github/workflows/test.yml`

#### 4.4 문서화
- [ ] API 문서 (docstring 개선)
- [ ] 사용 예제 추가
- [ ] 아키텍처 다이어그램
- [ ] 기여 가이드 (CONTRIBUTING.md)

**예상 시간:** 40분  
**파일:** `README.md`, `docs/` 디렉터리

---

## 🎯 Quick Wins (즉시 시작 가능)

### 옵션 A: 동시성 + 에러 처리 (추천)
**예상 시간:** 30-40분  
**영향도:** 높음 (성능 크게 개선)
- 동시성 추가 (1.1)
- 에러 처리 강화 (1.2)
- Rate Limiting (1.3)

### 옵션 B: RSS 리더 완성
**예상 시간:** 25-30분  
**영향도:** 중간 (새 기능 추가)
- RSS/Atom 리더 구현 (2.1)
- 설정 파일 확장 (2.3 일부)

### 옵션 C: 실전 배포 준비
**예상 시간:** 45-60분  
**영향도:** 중간 (운영 준비)
- 스케줄러 추가 (2.2)
- 로깅 개선 (2.4)
- CLI 개선 (4.1)

### 옵션 D: 빠른 검증
**예상 시간:** 5-10분  
**영향도:** 낮음 (검증 목적)
- config.yaml에 실제 타겟 추가
- main.py 실행 테스트
- DB 결과 확인

---

## 📝 메모

### 기술 스택
- Python 3.13.5
- aiohttp (비동기 HTTP)
- BeautifulSoup4 (HTML 파싱)
- aiosqlite (비동기 SQLite)
- pytest + pytest-asyncio (테스트)

### 향후 고려사항
- PostgreSQL 마이그레이션 (대용량 데이터)
- 분산 크롤링 (Celery, RabbitMQ)
- 머신러닝 통합 (분류, 요약)
- API 서버 (FastAPI)

---

## 🎨 블로그 콘텐츠 생성 확장 (향후 계획)

### 현재 가능한 것
- ✅ 특정 주제 블로그 콘텐츠 자동 수집
- ✅ RSS 피드를 통한 최신 글 수집
- ✅ 메타데이터 보존 (제목, 작성자, 날짜, 카테고리)
- ✅ 중복 제거 및 자동화 스케줄링

### 추가 개발 필요 (블로그 글 작성)

#### Phase 1: 콘텐츠 분석 (예상 30분)
- [ ] 키워드 추출 (TF-IDF, spaCy)
- [ ] 주제별 분류
- [ ] 트렌드 분석
- [ ] 요약문 생성 (extractive summarization)

**파일:** 새 파일 `modules/content_analyzer.py`

#### Phase 2: LLM 통합 (예상 1-2시간)
- [ ] OpenAI/Claude API 통합
- [ ] 프롬프트 템플릿 설계
- [ ] 수집된 콘텐츠를 컨텍스트로 제공
- [ ] 생성된 글 저장 및 포맷팅

**파일:** 새 파일 `modules/content_generator.py`, `config.yaml`

#### Phase 3: 콘텐츠 큐레이션 (예상 45분)
- [ ] DB 검색 및 필터링 기능
- [ ] 좋은 글 선별 알고리즘
- [ ] 링크 모음 + 요약 생성
- [ ] Markdown/HTML 출력

**파일:** 새 파일 `modules/curator.py`

### 활용 시나리오

#### 1. 콘텐츠 큐레이션 블로그
```
매일 수집 → 좋은 글 선별 → 링크 + 요약 → 큐레이션 글 발행
```

#### 2. 트렌드 분석 리포트
```
기간별 수집 → 키워드 추출 → 트렌드 분석 → "이번 주 AI 트렌드" 리포트
```

#### 3. AI 기반 블로그 작성
```
주제별 수집 → LLM에 컨텍스트 제공 → 새 글 생성 → 검토 후 발행
```

### 참고 링크
- [aiohttp 문서](https://docs.aiohttp.org/)
- [BeautifulSoup 문서](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [asyncio 패턴](https://docs.python.org/3/library/asyncio.html)
- [OpenAI API](https://platform.openai.com/docs/api-reference)
- [Anthropic Claude API](https://docs.anthropic.com/)
