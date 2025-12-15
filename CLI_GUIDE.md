# CLI 사용 가이드

Data Collector의 명령줄 인터페이스(CLI) 사용법을 설명합니다.

## 목차

- [기본 사용법](#기본-사용법)
- [서브커맨드](#서브커맨드)
  - [collect - 데이터 수집](#collect---데이터-수집)
  - [schedule - 스케줄러 실행](#schedule---스케줄러-실행)
  - [config - 설정 관리](#config---설정-관리)
- [공통 옵션](#공통-옵션)
- [사용 예제](#사용-예제)

---

## 기본 사용법

```bash
python main.py <command> [options]
```

도움말 확인:
```bash
python main.py --help
python main.py <command> --help
```

---

## 서브커맨드

### collect - 데이터 수집

웹 페이지 및 RSS 피드에서 데이터를 일회성으로 수집합니다.

#### 사용법

```bash
python main.py collect [options]
```

#### 옵션

| 옵션 | 설명 | 예제 |
|------|------|------|
| `--url URL` | 수집할 URL (여러 번 지정 가능) | `--url https://example.com` |
| `--rss RSS` | 수집할 RSS 피드 URL (여러 번 지정 가능) | `--rss https://news.ycombinator.com/rss` |
| `--no-progress` | 진행률 표시 비활성화 | `--no-progress` |
| `--max-concurrent N` | 최대 동시 실행 수 | `--max-concurrent 10` |

#### 예제

```bash
# config.yaml의 targets 사용
python main.py collect

# 특정 URL 수집
python main.py collect --url https://example.com

# 여러 URL 동시 수집
python main.py collect --url https://example.com --url https://httpbin.org/html

# RSS 피드 수집
python main.py collect --rss https://news.ycombinator.com/rss

# 진행률 표시 없이 수집
python main.py collect --no-progress

# 동시 실행 수 제한
python main.py collect --max-concurrent 3
```

---

### schedule - 스케줄러 실행

백그라운드에서 주기적으로 데이터를 수집합니다.

#### 사용법

```bash
python main.py schedule [options]
```

#### 옵션

| 옵션 | 설명 | 예제 |
|------|------|------|
| `--interval N` | 실행 간격 (분). config 설정을 오버라이드 | `--interval 30` |
| `--once` | 즉시 한 번만 실행하고 종료 | `--once` |

#### 예제

```bash
# config.yaml의 스케줄 설정 사용
python main.py schedule

# 30분 간격으로 실행
python main.py schedule --interval 30

# 즉시 한 번만 실행
python main.py schedule --once
```

#### 주의사항

- `config.yaml`에서 `scheduler.enabled: true`로 설정해야 합니다
- 종료하려면 `Ctrl+C`를 누르세요
- 첫 실행은 즉시 시작되며, 이후 설정된 간격으로 반복됩니다

---

### config - 설정 관리

설정 파일을 확인하거나 검증합니다.

#### 사용법

```bash
python main.py config [options]
```

#### 옵션

| 옵션 | 설명 | 예제 |
|------|------|------|
| `--show` | 현재 설정 표시 | `--show` |
| `--validate` | 설정 파일 유효성 검사 | `--validate` |
| `--export FILE` | 설정을 JSON 파일로 내보내기 | `--export config.json` |

#### 예제

```bash
# 현재 설정 확인
python main.py config --show

# 설정 유효성 검사
python main.py config --validate

# JSON으로 내보내기
python main.py config --export config.json
```

---

## 공통 옵션

모든 서브커맨드에서 사용 가능한 공통 옵션입니다.

| 옵션 | 설명 | 예제 |
|------|------|------|
| `--config FILE` | 설정 파일 경로 (기본값: config.yaml) | `--config prod.yaml` |
| `--profile NAME` | 프로파일 이름 (dev, prod 등) | `--profile prod` |
| `--verbose`, `-v` | 로그 레벨 증가 (-v: INFO, -vv: DEBUG) | `-vv` |
| `--quiet`, `-q` | 최소한의 출력만 표시 | `-q` |

### 프로파일 사용

프로파일을 사용하면 환경별로 다른 설정을 적용할 수 있습니다.

```bash
# 개발 환경
python main.py --profile dev collect

# 프로덕션 환경
python main.py --profile prod schedule

# 환경 변수로 설정
export APP_PROFILE=prod
python main.py collect
```

---

## 사용 예제

### 시나리오 1: 개발 중 테스트

```bash
# DEBUG 로그로 단일 URL 수집
python main.py -vv collect --url https://example.com --no-progress
```

### 시나리오 2: 프로덕션 배포

```bash
# 프로덕션 설정으로 스케줄러 실행
python main.py --profile prod --quiet schedule
```

### 시나리오 3: 대량 수집

```bash
# 여러 URL 동시 수집 (동시 실행 10개)
python main.py collect \
  --url https://site1.com \
  --url https://site2.com \
  --url https://site3.com \
  --max-concurrent 10
```

### 시나리오 4: CI/CD 파이프라인

```bash
# 설정 검증
python main.py config --validate || exit 1

# 한 번만 실행
python main.py schedule --once

# 결과 확인
python main.py config --show
```

### 시나리오 5: 커스텀 설정 파일

```bash
# 특정 설정 파일 사용
python main.py --config custom.yaml collect

# 다른 프로파일과 함께 사용
python main.py --config custom.yaml --profile staging schedule
```

---

## 진행률 표시

`tqdm` 패키지가 설치되어 있으면 자동으로 진행률 표시가 활성화됩니다.

```bash
# 진행률 표시 (기본값)
python main.py collect

# 진행률 표시 비활성화
python main.py collect --no-progress
```

진행률 표시 예:
```
수집 진행: 100%|██████████| 10/10 [00:15<00:00,  1.50s/it]
```

---

## 로그 레벨

로그 상세도를 조정할 수 있습니다:

```bash
# 기본 로그 (config.yaml 설정)
python main.py collect

# INFO 레벨 로그
python main.py -v collect

# DEBUG 레벨 로그 (매우 상세)
python main.py -vv collect

# 최소 출력 (ERROR만)
python main.py -q collect
```

---

## 종료 코드

프로그램은 다음 종료 코드를 반환합니다:

- `0`: 성공
- `1`: 오류 발생
- `130`: 사용자 중단 (Ctrl+C)

이를 활용한 스크립트 예:

```bash
#!/bin/bash

python main.py config --validate
if [ $? -ne 0 ]; then
    echo "설정 파일에 오류가 있습니다!"
    exit 1
fi

python main.py collect
if [ $? -eq 0 ]; then
    echo "수집 성공!"
else
    echo "수집 실패!"
fi
```

---

## 문제 해결

### 설정 파일을 찾을 수 없음

```bash
# 설정 파일 경로 확인
python main.py --config /path/to/config.yaml collect
```

### 수집할 대상이 없음

```bash
# config.yaml에 targets 또는 rss_feeds 추가
# 또는 명령행에서 직접 지정
python main.py collect --url https://example.com
```

### 스케줄러가 시작되지 않음

```bash
# 설정 검증
python main.py config --validate

# config.yaml에서 scheduler.enabled: true 확인
```

### 진행률 표시가 보이지 않음

```bash
# tqdm 설치
pip install tqdm

# 또는 requirements.txt 재설치
pip install -r requirements.txt
```

---

## 추가 정보

- 전체 설정 옵션: `config.yaml` 참조
- 환경 변수 설정: `.env.example` 참조
- API 문서: `docs/API.md` (예정)
