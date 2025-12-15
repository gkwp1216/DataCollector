# Desktop GUI Guide

Data Collector의 PyQt5 기반 데스크톱 GUI 가이드입니다.

## 🖥️ 데스크톱 GUI 개요

PyQt5를 사용한 네이티브 데스크톱 애플리케이션으로, Windows/Linux/Mac에서 실행 가능합니다.

### 주요 기능

- **대시보드**: 수집 통계 실시간 모니터링
- **데이터 수집**: URL 입력, 백그라운드 수집, 실시간 진행 상황
- **수집 결과**: 테이블 뷰, 검색, 페이징
- **설정 관리**: GUI에서 직접 설정 편집
- **로그 뷰어**: 자동 새로고침 로그 뷰어

### 웹 GUI와의 차이점

| 특징 | 데스크톱 GUI | 웹 GUI |
|------|------------|--------|
| 플랫폼 | 네이티브 앱 | 브라우저 |
| 성능 | 빠름 | 중간 |
| 배포 | 실행 파일 | 서버 필요 |
| UI | PyQt5 | Bootstrap |
| 멀티태스킹 | 스레드 | 웹워커 |

## 🚀 시작하기

### 1. 의존성 설치

```powershell
# PyQt5 설치
pip install -r requirements.txt
```

### 2. GUI 실행

```powershell
# 데스크톱 GUI 실행
python desktop_gui.py
```

## 📋 기능 상세

### 1. 대시보드 탭 (📊)

**표시 정보:**
- 총 수집 항목 수 (큰 숫자로 표시)
- 오늘 수집 항목 수
- 도메인 수
- 시스템 상태 (🟢 대기 중 / 🟡 실행 중)

**기능:**
- 🔄 통계 새로고침 버튼
- 자동 통계 업데이트 (수집 완료 시)

### 2. 데이터 수집 탭 (🚀)

**URL 입력:**
- 멀티라인 텍스트 박스
- 한 줄에 하나씩 URL 입력
- 📄 설정에서 불러오기 버튼

**제어 버튼:**
- ▶ 수집 시작 (녹색)
- ⏹ 중지 (빨간색)

**진행 상황:**
- 프로그레스 바 (시각적 진행률)
- 숫자 표시 (현재/전체)
- 실시간 결과 로그
  - ✅ 성공 항목 (제목 + URL)
  - ❌ 실패 항목 (에러 메시지)

**특징:**
- 백그라운드 스레드 실행 (UI 블록 없음)
- 실시간 진행 상황 업데이트
- 중지 버튼으로 언제든 중단 가능

### 3. 수집 결과 탭 (📋)

**검색 기능:**
- 제목 또는 URL 검색
- 🔍 검색 버튼
- 🔄 새로고침 버튼

**테이블 뷰:**
- ID, 제목, URL, 수집 일시 컬럼
- 정렬 가능한 헤더
- 행 선택 가능

**페이징:**
- ◀ 이전 / 다음 ▶ 버튼
- 현재 페이지 표시
- 페이지당 50개 항목

### 4. 설정 탭 (⚙️)

**크롤러 설정:**
- 동시 요청 수 (1-20)
- 타임아웃 (5-60초)
- 재시도 횟수 (0-10)
- 본문 추출 사용 (체크박스)
- 동적 페이지 지원 (체크박스)
- robots.txt 준수 (체크박스)

**저장:**
- 💾 설정 저장 버튼
- config.yaml에 직접 저장
- 성공/실패 메시지 표시

### 5. 로그 탭 (📄)

**기능:**
- 로그 파일 선택 (드롭다운)
- 자동 새로고침 (5초마다)
- 최근 200줄 표시
- 자동 스크롤 (최신 로그)

**로그 파일:**
- collector.log (전체)
- collector_YYYY-MM-DD.log (일별)
- error.log (에러만)

## 🎨 UI 특징

### 모던 디자인

- **Fusion 스타일**: Qt의 모던한 기본 스타일
- **그룹박스**: 기능별 섹션 구분
- **아이콘**: 이모지 기반 직관적 UI
- **색상 코딩**:
  - 녹색: 시작/성공
  - 빨간색: 중지/실패
  - 파란색: 정보/설정

### 반응형 레이아웃

- 창 크기 조절 가능
- 자동 레이아웃 조정
- 스크롤 가능한 콘텐츠

## 🔧 고급 사용법

### 백그라운드 수집

수집 작업은 별도 스레드에서 실행되어 UI가 멈추지 않습니다:

```python
# CrawlerWorker 클래스가 QThread 상속
worker = CrawlerWorker(urls, config)
worker.start()  # 백그라운드 실행

# Signal로 진행 상황 업데이트
worker.progress_updated.connect(self.update_progress)
worker.item_collected.connect(self.add_result)
```

### 실시간 업데이트

PyQt5 Signal/Slot 메커니즘으로 실시간 통신:

```python
# Worker에서 시그널 발생
self.progress_updated.emit(current, total)
self.item_collected.emit(url, title, success)

# UI에서 슬롯으로 수신
worker.progress_updated.connect(self.update_progress)
```

### 자동 새로고침

QTimer를 사용한 주기적 업데이트:

```python
timer = QTimer()
timer.timeout.connect(self.load_log)
timer.start(5000)  # 5초마다
```

## 📦 실행 파일 생성 (선택사항)

PyInstaller로 독립 실행 파일 생성:

```powershell
# PyInstaller 설치
pip install pyinstaller

# 단일 실행 파일 생성
pyinstaller --onefile --windowed --name="DataCollector" desktop_gui.py

# 생성된 파일: dist/DataCollector.exe
```

### PyInstaller 옵션

- `--onefile`: 단일 실행 파일
- `--windowed`: 콘솔 창 숨김 (GUI만)
- `--name`: 실행 파일 이름
- `--icon`: 아이콘 파일 지정 (선택)

## 🐛 트러블슈팅

### PyQt5 설치 실패

```powershell
# 개별 설치
pip install PyQt5==5.15.9

# 또는 conda 사용 (Anaconda 환경)
conda install pyqt
```

### "No module named 'PyQt5'" 에러

```powershell
# 가상환경 확인
.\.venv\Scripts\Activate.ps1

# PyQt5 재설치
pip install --force-reinstall PyQt5
```

### GUI가 느림

- 로그 자동 새로고침 비활성화
- 테이블 행 수 줄이기 (per_page 조정)
- 데이터베이스 인덱스 확인

### Windows에서 DLL 오류

```powershell
# Visual C++ Redistributable 설치 필요
# Microsoft 공식 사이트에서 다운로드
```

### 수집 중 GUI 멈춤

CrawlerWorker가 QThread를 상속하는지 확인:

```python
class CrawlerWorker(QThread):
    # run() 메서드에서 작업 수행
```

## 🔒 멀티스레딩 주의사항

### 스레드 안전성

- **DB 작업**: 각 스레드에서 독립적인 connection 사용
- **GUI 업데이트**: Signal/Slot으로만 통신
- **공유 데이터**: Lock 사용 (필요시)

```python
# ❌ 직접 GUI 업데이트 (불안전)
self.label.setText("Updated")

# ✅ Signal로 GUI 업데이트 (안전)
self.update_signal.emit("Updated")
```

## 📊 성능 최적화

### 대용량 데이터 처리

```python
# 페이징으로 메모리 사용 최소화
items = await get_all_items(db_path, limit=50, offset=0)

# 테이블 업데이트 시 beginResetModel/endResetModel 사용
self.table.setRowCount(0)  # 클리어
# ... 데이터 추가
```

### 반응성 유지

```python
# 긴 작업은 QThread로 분리
worker = CrawlerWorker(urls, config)
worker.start()

# 또는 QApplication.processEvents() 호출
for item in large_list:
    process(item)
    QApplication.processEvents()  # UI 반응 유지
```

## 🎯 단축키 (향후 추가 예정)

- `Ctrl+N`: 새 수집
- `Ctrl+R`: 새로고침
- `Ctrl+S`: 설정 저장
- `Ctrl+Q`: 종료
- `F5`: 현재 탭 새로고침

## 🚀 향후 개선사항

- [ ] 시스템 트레이 아이콘 (백그라운드 실행)
- [ ] 다크 모드 지원
- [ ] 차트/그래프 (수집 통계)
- [ ] 데이터 내보내기 (CSV/JSON)
- [ ] 프로파일 관리 (여러 설정)
- [ ] 스케줄러 GUI 제어
- [ ] 알림 토스트 메시지
- [ ] 다국어 지원

## 📚 관련 문서

- [CLI 가이드](CLI_GUIDE.md)
- [API 문서](docs/API.md)
- [아키텍처](docs/ARCHITECTURE.md)

## 🔗 PyQt5 학습 자료

- [PyQt5 공식 문서](https://www.riverbankcomputing.com/static/Docs/PyQt5/)
- [Qt Designer](https://doc.qt.io/qt-5/qtdesigner-manual.html) - GUI 디자이너 도구
- [PyQt5 튜토리얼](https://www.tutorialspoint.com/pyqt5/index.htm)

---

**Happy Collecting with Desktop GUI! 🖥️**
