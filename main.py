import asyncio
import logging
import yaml
import argparse
from typing import List, Optional, Dict
from datetime import datetime
from modules.crawler import AsyncCrawler
from modules.rss_reader import RSSReader
from modules.database import init_db, save_item


logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


async def collect_url(crawler: AsyncCrawler, url: str, db_path: str, semaphore: asyncio.Semaphore, skip_duplicates: bool = True) -> Optional[Dict]:
    """단일 URL 수집 (Semaphore로 동시 실행 제한)"""
    async with semaphore:
        # 중복 검사
        if skip_duplicates:
            from modules.database import url_exists
            if await url_exists(db_path, url):
                logging.info("⏭ 중복 URL 건너뛜: %s", url)
                return {"skipped": True, "url": url}
        
        logging.info("수집 시작: %s", url)
        try:
            item = await crawler.fetch_and_parse(url)
            if item:
                await save_item(db_path, item)
                logging.info("✓ 수집 및 저장됨: %s", item.get("title"))
                return item
            else:
                logging.warning("✗ 수집 실패 (응답 없음): %s", url)
                return None
        except Exception as e:
            logging.error("✗ 수집 중 예외 발생: %s - %s", url, str(e))
            return None


async def collect_all(targets: List[str], db_path: str, max_concurrent: int = 5, skip_duplicates: bool = True, **crawler_kwargs):
    """여러 URL 동시 수집"""
    crawler = AsyncCrawler(**crawler_kwargs)
    semaphore = asyncio.Semaphore(max_concurrent)
    
    logging.debug("크롤러 설정: timeout=%s, max_retries=%s, delay=%s, skip_duplicates=%s", 
                  crawler_kwargs.get('timeout'), 
                  crawler_kwargs.get('max_retries', 3),
                  crawler_kwargs.get('delay', 1.0),
                  skip_duplicates)
    
    try:
        logging.info("=" * 60)
        logging.info("수집 시작: 총 %d개 URL (최대 동시 실행: %d)", len(targets), max_concurrent)
        logging.info("=" * 60)
        
        tasks = [collect_url(crawler, url, db_path, semaphore, skip_duplicates) for url in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 집계
        skipped_count = sum(1 for r in results if isinstance(r, dict) and r.get("skipped"))
        success_count = sum(1 for r in results if r is not None and not isinstance(r, Exception) and not (isinstance(r, dict) and r.get("skipped")))
        fail_count = len(results) - success_count - skipped_count
        
        logging.info("=" * 60)
        logging.info("수집 완료: 성공 %d개, 실패 %d개, 중복 건너뛜 %d개 (총 %d개)", 
                     success_count, fail_count, skipped_count, len(targets))
        logging.info("=" * 60)
        
        return results
    finally:
        await crawler.close()


async def collect_rss_feeds(rss_urls: List[str], db_path: str, **reader_kwargs):
    """여러 RSS 피드 수집"""
    if not rss_urls:
        return []
    
    reader = RSSReader(**reader_kwargs)
    
    try:
        logging.info("=" * 60)
        logging.info("RSS 피드 수집 시작: 총 %d개", len(rss_urls))
        logging.info("=" * 60)
        
        results = []
        for feed_url in rss_urls:
            logging.info("피드 수집 시작: %s", feed_url)
            feed_data = await reader.fetch_and_parse(feed_url)
            
            if feed_data and feed_data.get("entries"):
                entries = feed_data["entries"]
                logging.info("✓ 피드 수집됨: %s (%d개 항목)", 
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
                logging.warning("✗ 피드 수집 실패: %s", feed_url)
        
        logging.info("=" * 60)
        logging.info("RSS 피드 수집 완료: 성공 %d개 (총 %d개)", len(results), len(rss_urls))
        logging.info("=" * 60)
        
        return results
    finally:
        await reader.close()


async def run_collection(config_path: str = "config.yaml"):
    """수집 작업 실행 (스케줄러에서 호출됨)"""
    logging.info("▶ 수집 작업 시작: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    db_path = cfg.get("db", {}).get("path", "data.db")
    targets = cfg.get("targets", [])
    
    # 크롤러 설정
    crawler_config = cfg.get("crawler", {})
    max_concurrent = crawler_config.get("max_concurrent", 5)
    timeout = crawler_config.get("timeout", 10)
    max_retries = crawler_config.get("max_retries", 3)
    delay = crawler_config.get("delay_between_requests", 1.0)
    user_agent = crawler_config.get("user_agent")
    skip_duplicates = crawler_config.get("skip_duplicates", True)

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
    args = parser.parse_args()
    
    if args.schedule:
        # 스케줄러 모드
        with open(args.config, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        
        scheduler_config = cfg.get("scheduler", {})
        if not scheduler_config.get("enabled", False):
            logging.warning("스케줄러가 비활성화되어 있습니다. config.yaml에서 scheduler.enabled=true로 설정하세요.")
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
            logging.info("스케줄러 설정: cron='%s'", cron_expr)
        else:
            # interval 사용
            interval_minutes = scheduler_config.get("interval_minutes", 60)
            trigger = IntervalTrigger(minutes=interval_minutes)
            logging.info("스케줄러 설정: %d분 간격", interval_minutes)
        
        # 작업 등록
        scheduler.add_job(
            lambda: asyncio.create_task(run_collection(args.config)),
            trigger=trigger,
            id="collection_job",
            name="데이터 수집 작업",
            replace_existing=True
        )
        
        logging.info("="*60)
        logging.info("스케줄러 시작됨. 종료하려면 Ctrl+C를 누르세요.")
        logging.info("="*60)
        
        # 초기 실행 (즉시)
        await run_collection(args.config)
        
        # 스케줄러 시작
        scheduler.start()
        
        try:
            # 무한 대기
            while True:
                await asyncio.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            logging.info("스케줄러 종료 중...")
            scheduler.shutdown()
            logging.info("스케줄러가 정지되었습니다.")
    else:
        # 일회성 실행
        await run_collection(args.config)


if __name__ == "__main__":
    asyncio.run(main())
