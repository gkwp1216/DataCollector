# DataCollector (초기 템플릿)

간단한 비동기 크롤러 템플릿입니다. 이 레포는 최소한의 스캐폴딩과 크롤러 골격을 포함합니다.

빠른 시작 (Windows - PowerShell):

```powershell
# 가상환경 생성
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 의존성 설치
pip install -r requirements.txt

# 예제 실행
python main.py

# 테스트 실행
python -m pytest -q
```

파일 설명:

- `main.py`: 간단한 진입점이며 `config.yaml`의 targets를 수집합니다.
- `modules/crawler.py`: aiohttp 기반 비동기 크롤러와 HTML 파서
- `modules/database.py`: aiosqlite를 이용한 간단 DB 초기화 및 저장
- `config.yaml`: 기본 설정
- `requirements.txt`: 필요한 패키지 목록
