# 기여 가이드

Data Collector 프로젝트에 기여해 주셔서 감사합니다! 이 문서는 프로젝트에 기여하는 방법을 설명합니다.

## 목차

- [행동 강령](#행동-강령)
- [시작하기](#시작하기)
- [개발 환경 설정](#개발-환경-설정)
- [기여 방법](#기여-방법)
- [코딩 스타일](#코딩-스타일)
- [테스트](#테스트)
- [Pull Request 절차](#pull-request-절차)
- [커밋 메시지 규칙](#커밋-메시지-규칙)
- [이슈 리포팅](#이슈-리포팅)

---

## 행동 강령

이 프로젝트는 모든 기여자가 존중받는 환경을 유지하기 위해 행동 강령을 따릅니다:

- **존중**: 모든 의견과 관점을 존중합니다
- **포용**: 다양한 배경의 기여자를 환영합니다
- **건설적**: 건설적인 피드백을 제공합니다
- **협력**: 협력적인 태도로 작업합니다

부적절한 행동을 발견하면 프로젝트 관리자에게 보고해 주세요.

---

## 시작하기

### 1. 저장소 포크

GitHub에서 저장소를 포크합니다:
```bash
# GitHub UI에서 "Fork" 버튼 클릭
```

### 2. 로컬에 클론

```bash
git clone https://github.com/<your-username>/DataCollector.git
cd DataCollector
```

### 3. 업스트림 추가

```bash
git remote add upstream https://github.com/gkwp1216/DataCollector.git
git fetch upstream
```

---

## 개발 환경 설정

### 필수 요구사항

- **Python**: 3.10 이상
- **pip**: 최신 버전
- **Git**: 2.0 이상

### 설치

```bash
# 가상환경 생성
python -m venv .venv

# 가상환경 활성화
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Linux/macOS
source .venv/bin/activate

# 의존성 설치 (개발 도구 포함)
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 생성 예정

# 개발 도구 설치 (수동)
pip install pytest pytest-asyncio pytest-cov
pip install flake8 black isort mypy
pip install pre-commit
```

### Playwright 설치 (동적 페이지 지원)

```bash
playwright install chromium
```

### Pre-commit 훅 설정

```bash
pre-commit install
```

---

## 기여 방법

### 기여할 수 있는 것들

1. **버그 수정**: 이슈 트래커에서 버그 찾기
2. **새 기능**: 새로운 기능 제안 및 구현
3. **문서 개선**: 오타 수정, 예제 추가, 번역
4. **테스트**: 테스트 커버리지 증가
5. **코드 리뷰**: Pull Request 리뷰

### 기여 워크플로우

```
1. 이슈 생성 또는 기존 이슈 선택
   ↓
2. 브랜치 생성 (feature/issue-123)
   ↓
3. 코드 작성
   ↓
4. 테스트 작성 및 실행
   ↓
5. 커밋 (의미 있는 메시지)
   ↓
6. Push to fork
   ↓
7. Pull Request 생성
   ↓
8. 코드 리뷰
   ↓
9. 수정 반영
   ↓
10. 머지
```

---

## 코딩 스타일

### Python 스타일 가이드

**PEP 8**을 따릅니다. `flake8`과 `black`을 사용합니다.

#### 포매팅

```bash
# Black으로 자동 포매팅
black modules/ tests/

# isort로 import 정렬
isort modules/ tests/

# flake8로 스타일 검사
flake8 modules/ tests/
```

#### 주요 규칙

**1. 네이밍**

```python
# 클래스: PascalCase
class AsyncCrawler:
    pass

# 함수/변수: snake_case
def fetch_data():
    user_name = "example"

# 상수: UPPER_CASE
MAX_RETRIES = 3

# Private: _leading_underscore
def _internal_method():
    pass
```

**2. 타입 힌트**

모든 공개 함수에 타입 힌트 추가:

```python
from typing import Optional, Dict, List

async def fetch_url(
    url: str,
    timeout: int = 10
) -> Optional[str]:
    """URL에서 HTML을 가져옵니다."""
    pass
```

**3. Docstring**

모든 공개 함수/클래스에 docstring 추가:

```python
def parse_html(html: str) -> Dict:
    """
    HTML을 파싱하여 데이터를 추출합니다.
    
    Args:
        html (str): 파싱할 HTML 문자열
    
    Returns:
        Dict: 파싱된 데이터
            - title: 페이지 제목
            - content: 본문
            - links: 링크 리스트
    
    Raises:
        ValueError: HTML이 비어있을 때
    
    Example:
        >>> html = "<html><title>Test</title></html>"
        >>> parse_html(html)
        {'title': 'Test', ...}
    """
    pass
```

**4. 임포트 순서**

```python
# 1. 표준 라이브러리
import asyncio
import logging
from typing import Optional

# 2. 서드파티 라이브러리
import aiohttp
from bs4 import BeautifulSoup

# 3. 로컬 모듈
from modules.database import save_item
from modules.logger import get_logger
```

**5. 라인 길이**

최대 120자 (setup.cfg에서 설정됨)

---

## 테스트

### 테스트 작성

모든 새 기능에 테스트를 추가합니다.

#### 디렉터리 구조

```
tests/
├── test_crawler.py
├── test_rss_reader.py
├── test_database.py
├── test_config_loader.py
├── test_logger.py
├── test_notifier.py
├── test_robots_handler.py
└── test_dynamic_page_handler.py
```

#### 테스트 예제

```python
import pytest
from modules.crawler import AsyncCrawler

@pytest.mark.asyncio
async def test_fetch_success():
    """성공적인 페이지 수집 테스트"""
    crawler = AsyncCrawler(timeout=10)
    html = await crawler.fetch("https://httpbin.org/html")
    
    assert html is not None
    assert "<html>" in html.lower()
    
    await crawler.close()

@pytest.mark.asyncio
async def test_fetch_timeout():
    """타임아웃 처리 테스트"""
    crawler = AsyncCrawler(timeout=0.001)  # 매우 짧은 타임아웃
    
    html = await crawler.fetch("https://example.com")
    
    assert html is None  # 타임아웃으로 실패
    
    await crawler.close()
```

### 테스트 실행

```bash
# 모든 테스트 실행
pytest

# 특정 파일 테스트
pytest tests/test_crawler.py

# 특정 테스트 함수
pytest tests/test_crawler.py::test_fetch_success

# 커버리지 포함
pytest --cov=modules --cov-report=html

# Verbose 모드
pytest -v

# 실패 시 즉시 중단
pytest -x
```

### 테스트 커버리지

최소 80% 커버리지를 목표로 합니다:

```bash
pytest --cov=modules --cov-report=term-missing
```

---

## Pull Request 절차

### 1. 브랜치 생성

```bash
# 최신 코드 가져오기
git checkout main
git pull upstream main

# 새 브랜치 생성
git checkout -b feature/add-new-parser
# 또는
git checkout -b fix/issue-123
```

**브랜치 네이밍:**
- `feature/`: 새 기능
- `fix/`: 버그 수정
- `docs/`: 문서 변경
- `test/`: 테스트 추가/수정
- `refactor/`: 리팩토링

### 2. 코드 작성

```bash
# 코드 수정...

# 테스트 작성...

# 스타일 검사
black modules/
flake8 modules/

# 테스트 실행
pytest
```

### 3. 커밋

```bash
git add .
git commit -m "feat: Add trafilatura content extraction"
```

### 4. Push

```bash
git push origin feature/add-new-parser
```

### 5. Pull Request 생성

GitHub에서 Pull Request를 생성합니다.

**PR 템플릿:**

```markdown
## 변경 사항

간단히 설명해 주세요.

## 관련 이슈

Closes #123

## 변경 타입

- [ ] 버그 수정
- [ ] 새 기능
- [ ] 문서 업데이트
- [ ] 리팩토링
- [ ] 테스트 추가

## 체크리스트

- [ ] 테스트 추가됨
- [ ] 문서 업데이트됨
- [ ] 스타일 가이드 준수
- [ ] CI 통과

## 스크린샷 (해당하는 경우)

```

### 6. 코드 리뷰

리뷰어의 피드백을 반영합니다:

```bash
# 수정 사항 커밋
git add .
git commit -m "fix: Address review comments"
git push origin feature/add-new-parser
```

---

## 커밋 메시지 규칙

**Conventional Commits** 형식을 따릅니다:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type

- `feat`: 새 기능
- `fix`: 버그 수정
- `docs`: 문서 변경
- `style`: 코드 스타일 (포매팅, 세미콜론 등)
- `refactor`: 리팩토링
- `test`: 테스트 추가/수정
- `chore`: 빌드, 설정 등

### 예제

```bash
# 좋은 예
git commit -m "feat(crawler): Add robots.txt support"
git commit -m "fix(database): Resolve duplicate key error"
git commit -m "docs(readme): Update installation instructions"

# 나쁜 예
git commit -m "update"
git commit -m "fix bug"
git commit -m "changes"
```

### 본문 추가 (선택)

```bash
git commit -m "feat(notifier): Add Discord webhook support

- Add DiscordNotifier class
- Integrate with main notification system
- Add tests for Discord notifications

Closes #45"
```

---

## 이슈 리포팅

### 버그 리포트

버그를 발견하면 이슈를 생성해 주세요:

**이슈 템플릿:**

```markdown
## 버그 설명

명확하고 간단하게 버그를 설명해 주세요.

## 재현 방법

1. '...'로 이동
2. '...'를 클릭
3. '...'로 스크롤
4. 에러 확인

## 예상 동작

어떤 결과를 예상했는지 설명해 주세요.

## 실제 동작

실제로 무슨 일이 일어났는지 설명해 주세요.

## 스크린샷

해당하는 경우 스크린샷을 추가해 주세요.

## 환경

- OS: [예: Windows 11]
- Python 버전: [예: 3.12]
- 프로젝트 버전: [예: 1.0.0]

## 추가 정보

기타 정보를 추가해 주세요.
```

### 기능 제안

새 기능을 제안하려면:

```markdown
## 기능 설명

제안하는 기능을 명확하게 설명해 주세요.

## 동기

이 기능이 왜 필요한지 설명해 주세요.

## 제안된 솔루션

어떻게 구현할지 설명해 주세요.

## 대안

고려한 다른 방법이 있나요?

## 추가 정보

기타 정보를 추가해 주세요.
```

---

## 코드 리뷰 가이드라인

### 리뷰어

- **긍정적**: 좋은 코드는 칭찬합니다
- **구체적**: 구체적인 피드백을 제공합니다
- **건설적**: 개선 방법을 제안합니다
- **신속**: 24-48시간 내에 리뷰합니다

### 작성자

- **열린 마음**: 피드백을 받아들입니다
- **설명**: 변경 이유를 설명합니다
- **신속**: 피드백을 빠르게 반영합니다

---

## 릴리스 프로세스

### 버전 관리

**Semantic Versioning**을 따릅니다:

```
MAJOR.MINOR.PATCH

예: 1.2.3
- MAJOR: 호환되지 않는 API 변경
- MINOR: 하위 호환되는 새 기능
- PATCH: 하위 호환되는 버그 수정
```

### 릴리스 체크리스트

1. [ ] 모든 테스트 통과
2. [ ] 문서 업데이트
3. [ ] CHANGELOG.md 업데이트
4. [ ] 버전 번호 증가
5. [ ] Git 태그 생성
6. [ ] GitHub Release 생성

---

## 개발 도구

### 권장 IDE

- **VS Code**: Python 확장 설치
- **PyCharm**: Professional 또는 Community

### VS Code 확장

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.black-formatter",
    "ms-python.isort",
    "ms-python.flake8",
    "ms-python.mypy-type-checker"
  ]
}
```

### 유용한 스크립트

```bash
# 전체 검사
./scripts/check.sh

# 테스트
./scripts/test.sh

# 포매팅
./scripts/format.sh
```

---

## 커뮤니티

### 소통 채널

- **GitHub Issues**: 버그 리포트, 기능 제안
- **GitHub Discussions**: 질문, 아이디어 공유
- **Email**: gkwp1216@example.com (프로젝트 관리자)

### 도움 받기

막히는 부분이 있으면:

1. **문서 확인**: README, API.md, ARCHITECTURE.md
2. **이슈 검색**: 비슷한 문제가 있는지 확인
3. **질문하기**: GitHub Discussions에 질문

---

## 감사의 말

모든 기여자에게 감사드립니다! 🎉

기여자 목록은 [Contributors](https://github.com/gkwp1216/DataCollector/graphs/contributors)에서 확인할 수 있습니다.

---

## 라이선스

이 프로젝트에 기여하면 기여 내용은 프로젝트와 동일한 라이선스(MIT)로 제공됩니다.

---

## 추가 리소스

- **Python 스타일 가이드**: https://pep8.org/
- **asyncio 문서**: https://docs.python.org/3/library/asyncio.html
- **pytest 문서**: https://docs.pytest.org/
- **Git 가이드**: https://git-scm.com/book/ko/v2

---

**질문이 있으시면 언제든지 Issue나 Discussion을 생성해 주세요!**
