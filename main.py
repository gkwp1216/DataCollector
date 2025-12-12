import asyncio
import argparse
import os
from typing import List, Optional, Dict
from datetime import datetime
from modules.crawler import AsyncCrawler
from modules.rss_reader import RSSReader
from modules.database import init_db, save_item
from modules.logger import setup_logger, get_logger, log_stats
from modules.config_loader import load_config, ConfigLoader


def initialize_logger(config_loader: ConfigLoader):
    """설정 로더로부터 로거 초기화"""
    try:
        return setup_logger(
            name="data_collector",
            log_dir=config_loader.get("logging.log_dir", "logs"),
            level=config_loader.get("logging.level", "INFO"),
            enable_file_logging=config_loader.get("logging.enable_file_logging", True),
            enable_console_logging=config_loader.get("logging.enable_console_logging", True),
            max_bytes=config_loader.get("logging.max_bytes", 10485760),
            backup_count=config_loader.get("logging.backup_count", 5)
        )
    except Exception as e:
        # 설정 로드 실패 시 기본 로거 사용
        return setup_logger(
            name="data_collector",
            log_dir="logs",
            level="INFO",
            enable_file_logging=True,
            enable_console_logging=True
        )


# 로거 초기화 (전역)
logger = None


async def collect_url(crawler: AsyncCrawler, url: str, db_path: str, semaphore: asyncio.Semaphore, skip_duplicates: bool = True) -> Optional[Dict]:
    """단일 URL 수집 (Semaphore로 동시 실행 제한)"""
    async with semaphore:
        # 중복 검사
        if skip_duplicates:
            from modules.database import url_exists
            if await url_exists(db_path, url):
                logger.info("⏭ 중복 URL 건너뛜: %s", url)
                return {"skipped": True, "url": url}
        
        logger.info("수집 시작: %s", url)
        try:
            item = await crawler.fetch_and_parse(url)
            if item:
                await save_item(db_path, item)
                logger.info("✓ 수집 및 저장됨: %s", item.get("title"))
                return item
            else:
                logger.warning("✗ 수집 실패 (응답 없음): %s", url)
                return None
        except Exception as e:
            logger.error("✗ 수집 중 예외 발생: %s - %s", url, str(e), exc_info=True)
            return None


async def collect_all(targets: List[str], db_path: str, max_concurrent: int = 5, skip_duplicates: bool = True, **crawler_kwargs):
    """여러 URL 동시 수집"""
    crawler = AsyncCrawler(**crawler_kwargs)
    semaphore = asyncio.Semaphore(max_concurrent)
    
    logger.debug("크롤러 설정: timeout=%s, max_retries=%s, delay=%s, skip_duplicates=%s", 
                  crawler_kwargs.get('timeout'), 
                  crawler_kwargs.get('max_retries', 3),
                  crawler_kwargs.get('delay', 1.0),
                  skip_duplicates)
    
    try:
        logger.info("=" * 60)
        logger.info("수집 시작: 총 %d개 URL (최대 동시 실행: %d)", len(targets), max_concurrent)
        logger.info("=" * 60)
        
        tasks = [collect_url(crawler, url, db_path, semaphore, skip_duplicates) for url in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 집계
        skipped_count = sum(1 for r in results if isinstance(r, dict) and r.get("skipped"))
        success_count = sum(1 for r in results if r is not None and not isinstance(r, Exception) and not (isinstance(r, dict) and r.get("skipped")))
        fail_count = len(results) - success_count - skipped_count
        
        log_stats(logger, success_count, fail_count, skipped_count, len(targets))
        
        return results
    finally:
        await crawler.close()


async def collect_rss_feeds(rss_urls: List[str], db_path: str, **reader_kwargs):
    """여러 RSS 피드 수집"""
    if not rss_urls:
        return []
    
    reader = RSSReader(**reader_kwargs)
    
    try:
        logger.info("=" * 60)
        logger.info("RSS 피드 수집 시작: 총 %d개", len(rss_urls))
        logger.info("=" * 60)
        
        results = []
        for feed_url in rss_urls:
            logger.info("피드 수집 시작: %s", feed_url)
            feed_data = await reader.fetch_and_parse(feed_url)
            
            if feed_data and feed_data.get("entries"):
                entries = feed_data["entries"]
                logger.info("✓ 피드 수집됨: %s (%d개 항목)", 
                            feed_data.get("title", "Unknown"), len(entries))
                
                # 각 항목을 DB에 저장
                for entry in entries:
                    item = {
                        "url": entry.get("link"),
                        "title": entry.get("title"),
                        "content": entry.get("description") or entry.get("summary"),
                    }
                    if item["url"]:
                        await save_item(db_path, item)
                
                results.append(feed_data)
            else:
                logger.warning("✗ 피드 수집 실패: %s", feed_url)
        
        logger.info("=" * 60)
        logger.info("RSS 피드 수집 완료: 성공 %d개 (총 %d개)", len(results), len(rss_urls))
        logger.info("=" * 60)
        
        return results
    finally:
        await reader.close()


async def run_collection(config_path: str = "config.yaml", profile: Optional[str] = None):
    """수집 작업 실행 (스케줄러에서 호출됨)"""
    logger.info("▶ 수집 작업 시작: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # ConfigLoader 사용
    cfg = load_config(config_path, profile)

    db_path = cfg.get("db.path", "data.db")
    targets = cfg.get("targets", [])
    
    # 크롤러 설정
    max_concurrent = cfg.get("crawler.max_concurrent", 5)
    timeout = cfg.get("crawler.timeout", 10)
    max_retries = cfg.get("crawler.max_retries", 3)
    delay = cfg.get("crawler.delay_between_requests", 1.0)
    user_agent = cfg.get("crawler.user_agent")
    skip_duplicates = cfg.get("crawler.skip_duplicates", True)

    await init_db(db_path)
    
    # HTML 페이지 수집
    if targets:
        await collect_all(
            targets, 
            db_path, 
            max_concurrent=max_concurrent,
            skip_duplicates=skip_duplicates,
            timeout=timeout,
            max_retries=max_retries,
            delay=delay,
            user_agent=user_agent
        )
    
    # RSS 피드 수집
    rss_feeds = cfg.get("rss_feeds", [])
    if rss_feeds:
        await collect_rss_feeds(
            rss_feeds,
            db_path,
            timeout=timeout,
            user_agent=user_agent
        )


async def main():
    """메인 함수: 스케줄러 또는 일회성 실행"""
    global logger
    
    parser = argparse.ArgumentParser(description="Data Collector - 웹 크롤러 및 RSS 리더")
    parser.add_argument(
        "--schedule", 
        action="store_true", 
        help="스케줄러 모드로 실행 (백그라운드 주기적 수집)"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="설정 파일 경로 (default: config.yaml)"
    )
    parser.add_argument(
        "--profile",
        help="프로파일 이름 (dev, prod 등). APP_PROFILE 환경 변수로도 설정 가능"
    )
    args = parser.parse_args()
    
    # 프로파일 결정 (명령행 인수 > 환경 변수)
    profile = args.profile or os.getenv("APP_PROFILE")
    
    # ConfigLoader 초기화
    try:
        config = load_config(args.config, profile)
        logger = initialize_logger(config)
        
        if profile:
            logger.info("프로파일 사용: %s", profile)
    except Exception as e:
        print(f"설정 로드 실패: {e}")
        return
    
    if args.schedule:
        # 스케줄러 모드
        cfg = load_config(args.config, profile)
        
        scheduler_config = cfg.to_dict().get("scheduler", {})
        if not scheduler_config.get("enabled", False):
            logger.warning("스케줄러가 비활성화되어 있습니다. config.yaml에서 scheduler.enabled=true로 설정하세요.")
            return
        
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger
        
        scheduler = AsyncIOScheduler()
        
        # 트리거 설정
        cron_expr = scheduler_config.get("cron")
        if cron_expr:
            # cron 표현식 사용
            trigger = CronTrigger.from_crontab(cron_expr)
            logger.info("스케줄러 설정: cron='%s'", cron_expr)
        else:
            # interval 사용
            interval_minutes = scheduler_config.get("interval_minutes", 60)
            trigger = IntervalTrigger(minutes=interval_minutes)
            logger.info("스케줄러 설정: %d분 간격", interval_minutes)
        
        # 작업 등록
        scheduler.add_job(
            lambda: asyncio.create_task(run_collection(args.config, profile)),
            trigger=trigger,
            id="collection_job",
            name="데이터 수집 작업",
            replace_existing=True
        )
        
        logger.info("="*60)
        logger.info("스케줄러 시작됨. 종료하려면 Ctrl+C를 누르세요.")
        logger.info("="*60)
        
        # 초기 실행 (즉시)
        await run_collection(args.config, profile)
        
        # 스케줄러 시작
        scheduler.start()
        
        try:
            # 무한 대기
            while True:
                await asyncio.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            logger.info("스케줄러 종료 중...")
            scheduler.shutdown()
            logger.info("스케줄러가 정지되었습니다.")
    else:
        # 일회성 실행
        await run_collection(args.config, profile)


if __name__ == "__main__":
    asyncio.run(main())
