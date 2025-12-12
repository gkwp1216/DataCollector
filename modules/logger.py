"""로깅 설정 모듈

파일 로깅, 로그 로테이션, 레벨별 분리 기능을 제공합니다.
"""
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime


def setup_logger(
    name: str = "data_collector",
    log_dir: str = "logs",
    level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_file_logging: bool = True,
    enable_console_logging: bool = True,
    log_format: str = None
) -> logging.Logger:
    """
    로거 설정
    
    Args:
        name: 로거 이름
        log_dir: 로그 파일 저장 디렉터리
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_bytes: 로그 파일 최대 크기 (바이트)
        backup_count: 백업 파일 개수
        enable_file_logging: 파일 로깅 활성화 여부
        enable_console_logging: 콘솔 로깅 활성화 여부
        log_format: 로그 포맷 (None이면 기본 포맷 사용)
    
    Returns:
        설정된 Logger 객체
    """
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 기존 핸들러 제거 (중복 방지)
    logger.handlers.clear()
    
    # 로그 포맷
    if log_format is None:
        log_format = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
    
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
    
    # 콘솔 핸들러
    if enable_console_logging:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # 파일 핸들러
    if enable_file_logging:
        # 로그 디렉터리 생성
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
        
        # 1. 통합 로그 (INFO 이상, 로테이션)
        all_log_file = log_path / "collector.log"
        rotating_handler = logging.handlers.RotatingFileHandler(
            all_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        rotating_handler.setLevel(logging.INFO)
        rotating_handler.setFormatter(formatter)
        logger.addHandler(rotating_handler)
        
        # 2. 에러 로그 (ERROR 이상만)
        error_log_file = log_path / "error.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
        
        # 3. 일별 로그 (날짜별 파일)
        today = datetime.now().strftime("%Y-%m-%d")
        daily_log_file = log_path / f"collector_{today}.log"
        daily_handler = logging.FileHandler(
            daily_log_file,
            encoding="utf-8"
        )
        daily_handler.setLevel(logging.DEBUG)
        daily_handler.setFormatter(formatter)
        logger.addHandler(daily_handler)
    
    return logger


def get_logger(name: str = "data_collector") -> logging.Logger:
    """
    기존 로거 가져오기
    
    Args:
        name: 로거 이름
    
    Returns:
        Logger 객체
    """
    return logging.getLogger(name)


# 편의 함수들
def log_collection_start(logger: logging.Logger, url: str, source_type: str = "HTML"):
    """수집 시작 로그"""
    logger.info(f"[{source_type}] 수집 시작: {url}")


def log_collection_success(logger: logging.Logger, url: str, title: str, source_type: str = "HTML"):
    """수집 성공 로그"""
    logger.info(f"[{source_type}] ✓ 수집 성공: {title} ({url})")


def log_collection_failure(logger: logging.Logger, url: str, reason: str, source_type: str = "HTML"):
    """수집 실패 로그"""
    logger.warning(f"[{source_type}] ✗ 수집 실패: {url} - {reason}")


def log_collection_error(logger: logging.Logger, url: str, error: Exception, source_type: str = "HTML"):
    """수집 에러 로그"""
    logger.error(f"[{source_type}] ✗ 에러 발생: {url} - {type(error).__name__}: {str(error)}", exc_info=True)


def log_stats(logger: logging.Logger, success: int, failed: int, skipped: int, total: int):
    """통계 로그"""
    logger.info(f"=" * 60)
    logger.info(f"수집 완료: 성공 {success}개, 실패 {failed}개, 중복 {skipped}개 (총 {total}개)")
    logger.info(f"=" * 60)
