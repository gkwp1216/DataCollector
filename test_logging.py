"""로깅 모듈 테스트 스크립트"""
import asyncio
from modules.logger import setup_logger, log_collection_start, log_collection_success, log_collection_failure

async def test_logging():
    """로깅 테스트"""
    logger = setup_logger(
        name="test_logger",
        log_dir="logs",
        level="DEBUG",
        enable_file_logging=True,
        enable_console_logging=True
    )
    
    logger.info("=" * 60)
    logger.info("로깅 시스템 테스트 시작")
    logger.info("=" * 60)
    
    # 다양한 로그 레벨 테스트
    logger.debug("디버그 메시지 테스트")
    logger.info("정보 메시지 테스트")
    logger.warning("경고 메시지 테스트")
    logger.error("에러 메시지 테스트")
    
    # 수집 로그 테스트
    log_collection_start(logger, "https://example.com")
    log_collection_success(logger, "https://example.com", "Example Domain", 100)
    
    log_collection_start(logger, "https://invalid-url.test")
    log_collection_failure(logger, "https://invalid-url.test", "404 Not Found")
    
    # 예외 로깅 테스트
    try:
        raise ValueError("테스트 예외")
    except Exception as e:
        logger.error("예외 발생 테스트: %s", str(e), exc_info=True)
    
    logger.info("=" * 60)
    logger.info("로깅 시스템 테스트 완료")
    logger.info("=" * 60)
    logger.info("로그 파일 확인: logs/test_logger.log")
    logger.info("에러 로그 확인: logs/error.log")

if __name__ == "__main__":
    asyncio.run(test_logging())
