# Web GUI Guide

Data Collector의 웹 기반 그래픽 사용자 인터페이스(GUI) 가이드입니다.

## 🌐 웹 GUI 개요

웹 GUI는 Flask 기반으로 구축되었으며, 브라우저를 통해 직관적으로 크롤러를 관리할 수 있습니다.

### 주요 기능

- **대시보드**: 수집 통계 및 시스템 상태 모니터링
- **데이터 수집**: URL 입력 및 실시간 수집 진행 상황 확인
- **수집 결과**: 데이터베이스 조회, 검색, 페이징
- **설정 관리**: 웹에서 config.yaml 편집
- **스케줄러 제어**: 스케줄러 설정 및 모니터링
- **로그 뷰어**: 실시간 로그 확인

## 🚀 시작하기

### 1. 의존성 설치

```powershell
# Flask 및 관련 패키지 설치
pip install -r requirements.txt
```

### 2. 웹 서버 실행

```powershell
# 개발 모드로 실행
python web_gui.py

# 또는 프로덕션 모드 (Gunicorn 사용 - Linux/Mac)
gunicorn -w 4 -b 0.0.0.0:5000 web_gui:app
```

### 3. 브라우저 접속

```
http://localhost:5000
```

## 📋 페이지 설명

### 1. 대시보드 (`/`)

**주요 정보:**
- 총 수집 항목 수
- 오늘 수집한 항목 수
- 크롤러 실행 상태
- 대상 사이트 개수

**기능:**
- 현재 설정 요약 보기
- 실행 중인 수집 진행 상황 (실시간)
- 빠른 작업 버튼 (새 수집 시작, 데이터 조회, 설정)

### 2. 데이터 수집 (`/collect`)

**기능:**
- 여러 URL 한 번에 입력 (한 줄에 하나씩)
- 설정 파일의 targets 자동 로드
- 수집 시작 버튼
- 현재 크롤러 상태 확인

**사용법:**
1. URL 입력란에 수집할 사이트 URL 입력
2. "수집 시작" 버튼 클릭
3. 자동으로 진행 상황 페이지로 이동

### 3. 수집 진행 상황 (`/progress`)

**실시간 업데이트:**
- 전체 진행률 프로그레스 바
- 성공/실패 카운트
- 성공한 항목 목록 (제목 + URL)
- 실패한 항목 목록 (에러 메시지)

**기능:**
- 2초마다 자동 갱신
- 크롤러 중지 버튼
- 실시간 결과 표시

### 4. 수집 결과 (`/data`)

**통계:**
- 총 수집 항목
- 오늘 수집 항목
- 도메인 수

**기능:**
- 검색 (제목/URL)
- 페이징 (20/50/100개씩)
- 상세 정보 보기 (제목, 내용 미리보기, URL, 수집 일시)
- 외부 링크 열기

**사용법:**
1. 검색어 입력 (선택사항)
2. 표시 개수 선택
3. "검색" 버튼 클릭
4. 결과 테이블에서 항목 확인

### 5. 설정 관리 (`/config`)

**편집 가능한 설정:**

**크롤러 설정:**
- 동시 요청 수 (1-20)
- 타임아웃 (5-60초)
- 재시도 횟수 (0-10)
- 요청 간 지연 (0-10초)
- 중복 건너뛰기 (토글)
- 본문 추출 사용 (토글)
- 동적 페이지 지원 (토글)
- robots.txt 준수 (토글)

**대상 사이트:**
- URL 목록 (한 줄에 하나씩)

**RSS 피드:**
- RSS/Atom 피드 URL 목록

**로깅 설정:**
- 로그 레벨 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- 파일 로깅 활성화
- 콘솔 로깅 활성화

**스케줄러 설정:**
- 스케줄러 활성화
- 실행 간격 (분)

**저장:**
- "설정 저장" 버튼 클릭 시 `config.yaml`에 저장

### 6. 스케줄러 (`/scheduler`)

**정보 표시:**
- 스케줄러 활성화/비활성화 상태
- 실행 간격
- 현재 설정 요약

**사용 가이드:**
- CLI 명령어 예시
- 권장 실행 간격 (사이트 유형별)
- 활성화 방법 단계별 안내

**참고:**
- 스케줄러는 CLI에서 `python main.py schedule` 명령으로 실행해야 합니다
- 웹 GUI는 설정만 관리하고, 실제 실행은 별도 프로세스

### 7. 로그 보기 (`/logs`)

**기능:**
- 로그 파일 목록 (사이드바)
- 로그 내용 보기 (최근 N줄)
- 표시 줄 수 선택 (50/100/200/500)
- 새로고침 버튼

**로그 파일:**
- `collector.log`: 전체 로그
- `collector_YYYY-MM-DD.log`: 일별 로그
- `error.log`: 에러만 분리

**사용법:**
1. 사이드바에서 로그 파일 선택
2. 표시 줄 수 선택
3. "새로고침" 버튼으로 최신 로그 확인

## 🔒 보안 고려사항

### 개발 환경

현재 구성은 개발/테스트 환경용입니다.

```python
# web_gui.py
app.secret_key = 'dev-secret-key-change-in-production'
app.run(host='0.0.0.0', port=5000, debug=True)
```

### 프로덕션 배포 시 권장사항

1. **Secret Key 변경:**
   ```python
   app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
   ```

2. **Debug 모드 비활성화:**
   ```python
   app.run(host='0.0.0.0', port=5000, debug=False)
   ```

3. **HTTPS 사용:**
   - Nginx/Apache 리버스 프록시
   - SSL/TLS 인증서 (Let's Encrypt)

4. **인증 추가:**
   - Flask-Login 또는 Flask-HTTPAuth
   - 사용자 인증/권한 관리

5. **프로덕션 서버 사용:**
   ```powershell
   # Gunicorn (Linux/Mac)
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 web_gui:app
   
   # Waitress (Windows)
   pip install waitress
   waitress-serve --host=0.0.0.0 --port=5000 web_gui:app
   ```

## 🐳 Docker로 웹 GUI 실행

### Dockerfile 수정

기존 `Dockerfile`에 웹 서버 포트 추가:

```dockerfile
# 웹 GUI 포트 노출
EXPOSE 5000

# 웹 서버 실행
CMD ["python", "web_gui.py"]
```

### Docker Compose 설정

```yaml
# docker-compose.yml
version: '3.8'

services:
  web-gui:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./data.db:/app/data.db
      - ./logs:/app/logs
      - ./config.yaml:/app/config.yaml
    environment:
      - SECRET_KEY=your-secret-key-here
      - PORT=5000
```

### 실행

```powershell
# 빌드 및 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 접속
# http://localhost:5000
```

## 🎨 UI 커스터마이징

### Bootstrap 테마 변경

`templates/base.html`에서 Bootstrap CDN 변경:

```html
<!-- 다른 Bootstrap 테마 -->
<link href="https://cdn.jsdelivr.net/npm/bootswatch@5.3.0/dist/darkly/bootstrap.min.css" rel="stylesheet">
```

### 스타일 수정

`templates/base.html`의 `<style>` 블록에서 CSS 수정:

```css
.sidebar {
    background-color: #f8f9fa;  /* 사이드바 배경색 */
}

.stat-card {
    border-left: 4px solid #007bff;  /* 통계 카드 강조색 */
}
```

## 📱 반응형 디자인

웹 GUI는 Bootstrap 5를 사용하여 모바일 친화적입니다:

- **데스크톱**: 사이드바 + 메인 컨텐츠
- **태블릿/모바일**: 햄버거 메뉴로 전환

## 🔧 트러블슈팅

### 포트 충돌

```powershell
# 다른 포트로 실행
$env:PORT=8080
python web_gui.py
```

### 크롤러가 실행되지 않음

웹 GUI는 크롤러를 별도 스레드에서 실행합니다. 에러 확인:

1. 로그 페이지에서 에러 확인
2. 콘솔 출력 확인
3. 설정 검증 (`/config` 페이지)

### 데이터베이스 연결 실패

```powershell
# 데이터베이스 파일 권한 확인
Get-Acl data.db

# 데이터베이스 초기화
python -c "import asyncio; from modules.database import init_db; asyncio.run(init_db('data.db'))"
```

### 템플릿 로딩 실패

```powershell
# templates 디렉터리 확인
Test-Path templates
Get-ChildItem templates
```

## 🚀 향후 개선사항

- [ ] 사용자 인증/권한 관리
- [ ] WebSocket을 통한 실시간 업데이트
- [ ] REST API 엔드포인트
- [ ] 데이터 내보내기 (CSV/JSON)
- [ ] 시각화 차트 (수집 통계)
- [ ] 스케줄러 웹에서 직접 제어
- [ ] 다국어 지원 (i18n)
- [ ] 다크 모드 토글

## 📚 관련 문서

- [CLI 가이드](CLI_GUIDE.md)
- [API 문서](docs/API.md)
- [아키텍처](docs/ARCHITECTURE.md)

---

**Happy Crawling with Web GUI! 🎨**
