import asyncio
import argparse
import os
import sys
import time
from typing import List, Optional, Dict
from datetime import datetime
from modules.crawler import AsyncCrawler
from modules.rss_reader import RSSReader
from modules.database import init_db, save_item
from modules.logger import setup_logger, get_logger, log_stats
from modules.config_loader import load_config, ConfigLoader
from modules.notifier import Notifier, MetricsCollector

try:
    from tqdm.asyncio import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    tqdm = None


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


async def collect_all(targets: List[str], db_path: str, max_concurrent: int = 5, skip_duplicates: bool = True, show_progress: bool = True, **crawler_kwargs):
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
        
        # tqdm 진행률 표시
        if TQDM_AVAILABLE and show_progress:
            results = []
            for coro in tqdm.as_completed(tasks, desc="수집 진행", total=len(tasks)):
                result = await coro
                results.append(result)
        else:
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
    
    # 알림 설정
    notifications_config = cfg.to_dict().get("notifications", {})
    notifier = None
    metrics = MetricsCollector()
    
    if notifications_config.get("enabled", False):
        email_config = notifications_config.get("email", {}) if notifications_config.get("email", {}).get("enabled") else None
        slack_config = notifications_config.get("slack", {}) if notifications_config.get("slack", {}).get("enabled") else None
        discord_config = notifications_config.get("discord", {}) if notifications_config.get("discord", {}).get("enabled") else None
        
        notifier = Notifier(
            email_config=email_config,
            slack_config=slack_config,
            discord_config=discord_config,
            enabled=True
        )
    
    # 메트릭 수집 시작
    metrics.start()
    start_time = time.time()

    await init_db(db_path)
    
    try:
        # HTML 페이지 수집
        if targets:
            results = await collect_all(
                targets, 
                db_path, 
                max_concurrent=max_concurrent,
                skip_duplicates=skip_duplicates,
                timeout=timeout,
                max_retries=max_retries,
                delay=delay,
                user_agent=user_agent
            )
            
            # 메트릭 기록
            for result in results:
                if result is None or isinstance(result, Exception):
                    metrics.record_failure(str(result) if result else "Unknown error")
                elif isinstance(result, dict) and result.get("skipped"):
                    metrics.record_skip()
                else:
                    metrics.record_success()
        
        # RSS 피드 수집
        rss_feeds = cfg.get("rss_feeds", [])
        if rss_feeds:
            rss_results = await collect_rss_feeds(
                rss_feeds,
                db_path,
                timeout=timeout,
                user_agent=user_agent
            )
            
            # RSS 결과도 메트릭에 반영
            for result in rss_results:
                if result:
                    metrics.record_success()
                else:
                    metrics.record_failure("RSS feed collection failed")
        
        # 메트릭 수집 종료
        metrics.end()
        duration = time.time() - start_time
        
        # 통계 로깅
        logger.info(metrics.get_summary())
        
        # 알림 전송
        if notifier and notifications_config.get("notify_on_complete", True):
            collected_metrics = metrics.get_metrics()
            await notifier.notify_collection_complete(
                total=collected_metrics["total_requests"],
                success=collected_metrics["successful_requests"],
                failed=collected_metrics["failed_requests"],
                skipped=collected_metrics["skipped_requests"],
                duration=duration
            )
            
            # 실패율 체크
            error_threshold = notifications_config.get("error_threshold", 50)
            if collected_metrics["success_rate"] < (100 - error_threshold):
                await notifier.notify_error(
                    f"높은 실패율 감지: {100 - collected_metrics['success_rate']:.1f}%",
                    f"총 {collected_metrics['total_requests']}개 중 {collected_metrics['failed_requests']}개 실패"
                )
    
    except Exception as e:
        logger.error("수집 작업 중 심각한 오류: %s", str(e), exc_info=True)
        
        # 에러 알림
        if notifier and notifications_config.get("notify_on_error", True):
            await notifier.notify_error(
                "수집 작업 실패",
                str(e)
            )
    
    finally:
        if notifier:
            await notifier.close()


async def main():
    """메인 함수: 서브커맨드 기반 CLI"""
    global logger
    
    # 메인 파서
    parser = argparse.ArgumentParser(
        description="Data Collector - 웹 크롤러 및 RSS 리더",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # 일회성 수집 실행
  python main.py collect
  
  # 특정 URL 수집
  python main.py collect --url https://example.com
  
  # 스케줄러 모드로 실행
  python main.py schedule
  
  # 설정 파일 확인
  python main.py config --show
  
  # 설정 유효성 검사
  python main.py config --validate
        """
    )
    
    # 공통 인수
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="설정 파일 경로 (default: config.yaml)"
    )
    parser.add_argument(
        "--profile",
        help="프로파일 이름 (dev, prod 등). APP_PROFILE 환경 변수로도 설정 가능"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="count",
        default=0,
        help="로그 레벨 증가 (-v: INFO, -vv: DEBUG)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="최소한의 출력만 표시"
    )
    
    # 서브커맨드
    subparsers = parser.add_subparsers(dest="command", help="사용 가능한 명령어")
    
    # collect 서브커맨드
    collect_parser = subparsers.add_parser(
        "collect",
        help="데이터 수집 실행 (일회성)",
        description="웹 페이지 및 RSS 피드에서 데이터를 수집합니다."
    )
    collect_parser.add_argument(
        "--url",
        action="append",
        help="수집할 URL (여러 번 지정 가능)"
    )
    collect_parser.add_argument(
        "--rss",
        action="append",
        help="수집할 RSS 피드 URL (여러 번 지정 가능)"
    )
    collect_parser.add_argument(
        "--no-progress",
        action="store_true",
        help="진행률 표시 비활성화"
    )
    collect_parser.add_argument(
        "--max-concurrent",
        type=int,
        help="최대 동시 실행 수 (기본값: config 파일 설정)"
    )
    
    # schedule 서브커맨드
    schedule_parser = subparsers.add_parser(
        "schedule",
        help="스케줄러 모드로 실행",
        description="백그라운드에서 주기적으로 데이터를 수집합니다."
    )
    schedule_parser.add_argument(
        "--interval",
        type=int,
        help="실행 간격 (분). config 설정을 오버라이드합니다."
    )
    schedule_parser.add_argument(
        "--once",
        action="store_true",
        help="즉시 한 번만 실행하고 종료"
    )
    
    # config 서브커맨드
    config_parser = subparsers.add_parser(
        "config",
        help="설정 관리",
        description="설정 파일을 확인하거나 검증합니다."
    )
    config_parser.add_argument(
        "--show",
        action="store_true",
        help="현재 설정 표시"
    )
    config_parser.add_argument(
        "--validate",
        action="store_true",
        help="설정 파일 유효성 검사"
    )
    config_parser.add_argument(
        "--export",
        metavar="FILE",
        help="설정을 JSON 파일로 내보내기"
    )
    
    args = parser.parse_args()
    
    # 명령어가 지정되지 않은 경우
    if not args.command:
        parser.print_help()
        return
    
    # 프로파일 결정
    profile = args.profile or os.getenv("APP_PROFILE")
    
    # ConfigLoader 초기화
    try:
        config = load_config(args.config, profile)
        
        # 로그 레벨 조정
        if args.quiet:
            log_level = "ERROR"
        elif args.verbose >= 2:
            log_level = "DEBUG"
        elif args.verbose == 1:
            log_level = "INFO"
        else:
            log_level = config.get("logging.level", "INFO")
        
        # 로거 초기화 (레벨 오버라이드)
        original_level = config.get("logging.level")
        config.config["logging"]["level"] = log_level
        logger = initialize_logger(config)
        config.config["logging"]["level"] = original_level
        
        if profile:
            logger.info("프로파일 사용: %s", profile)
    except Exception as e:
        print(f"❌ 설정 로드 실패: {e}", file=sys.stderr)
        return 1
    
    # 서브커맨드 처리
    try:
        if args.command == "collect":
            await handle_collect_command(args, config, profile)
        elif args.command == "schedule":
            await handle_schedule_command(args, config, profile)
        elif args.command == "config":
            handle_config_command(args, config)
        
        return 0
    
    except KeyboardInterrupt:
        logger.info("\n사용자에 의해 중단되었습니다.")
        return 130
    except Exception as e:
        logger.error("예상치 못한 오류: %s", str(e), exc_info=True)
        return 1


async def handle_collect_command(args: argparse.Namespace, config: ConfigLoader, profile: Optional[str]):
    """collect 명령어 처리"""
    # URL 결정 (명령행 > config)
    targets = args.url if args.url else config.get("targets", [])
    rss_feeds = args.rss if args.rss else config.get("rss_feeds", [])
    
    if not targets and not rss_feeds:
        logger.error("수집할 URL이 없습니다. --url 또는 --rss 옵션을 사용하거나 config.yaml에 targets를 설정하세요.")
        return
    
    # 설정 로드
    db_path = config.get("db.path", "data.db")
    max_concurrent = args.max_concurrent or config.get("crawler.max_concurrent", 5)
    timeout = config.get("crawler.timeout", 10)
    max_retries = config.get("crawler.max_retries", 3)
    delay = config.get("crawler.delay_between_requests", 1.0)
    user_agent = config.get("crawler.user_agent")
    skip_duplicates = config.get("crawler.skip_duplicates", True)
    show_progress = not args.no_progress
    
    await init_db(db_path)
    
    # HTML 페이지 수집
    if targets:
        logger.info("수집 대상: %d개 URL", len(targets))
        await collect_all(
            targets,
            db_path,
            max_concurrent=max_concurrent,
            skip_duplicates=skip_duplicates,
            timeout=timeout,
            max_retries=max_retries,
            delay=delay,
            user_agent=user_agent,
            show_progress=show_progress
        )
    
    # RSS 피드 수집
    if rss_feeds:
        logger.info("RSS 수집 대상: %d개 피드", len(rss_feeds))
        await collect_rss_feeds(
            rss_feeds,
            db_path,
            timeout=timeout,
            user_agent=user_agent
        )
    
    logger.info("✅ 수집 완료")


async def handle_schedule_command(args: argparse.Namespace, config: ConfigLoader, profile: Optional[str]):
    """schedule 명령어 처리"""
    scheduler_config = config.to_dict().get("scheduler", {})
    
    if not scheduler_config.get("enabled", False) and not args.once:
        logger.warning("스케줄러가 비활성화되어 있습니다. --once 옵션을 사용하거나 config.yaml에서 scheduler.enabled=true로 설정하세요.")
        return
    
    if args.once:
        # 즉시 한 번만 실행
        logger.info("일회성 실행 모드")
        await run_collection(args.config, profile)
        return
    
    # 스케줄러 모드
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    
    scheduler = AsyncIOScheduler()
    
    # 트리거 설정 (명령행 인수 > config)
    if args.interval:
        trigger = IntervalTrigger(minutes=args.interval)
        logger.info("스케줄러 설정: %d분 간격 (명령행 오버라이드)", args.interval)
    elif scheduler_config.get("cron"):
        cron_expr = scheduler_config["cron"]
        trigger = CronTrigger.from_crontab(cron_expr)
        logger.info("스케줄러 설정: cron='%s'", cron_expr)
    else:
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
    
    logger.info("=" * 60)
    logger.info("스케줄러 시작됨. 종료하려면 Ctrl+C를 누르세요.")
    logger.info("=" * 60)
    
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


def handle_config_command(args: argparse.Namespace, config: ConfigLoader):
    """config 명령어 처리"""
    import json
    from pprint import pprint
    
    if args.show:
        # 설정 표시
        print("\n=== 현재 설정 ===\n")
        pprint(config.to_dict())
        print()
    
    elif args.validate:
        # 설정 유효성 검사
        print("🔍 설정 파일 유효성 검사 중...")
        
        errors = []
        warnings = []
        
        # 필수 항목 확인
        if not config.get("db.path"):
            errors.append("db.path가 설정되지 않았습니다")
        
        if not config.get("targets") and not config.get("rss_feeds"):
            warnings.append("targets와 rss_feeds가 모두 비어있습니다")
        
        # 크롤러 설정 확인
        max_concurrent = config.get("crawler.max_concurrent", 5)
        if max_concurrent < 1 or max_concurrent > 100:
            warnings.append(f"crawler.max_concurrent 값이 비정상적입니다: {max_concurrent}")
        
        timeout = config.get("crawler.timeout", 10)
        if timeout < 1:
            warnings.append(f"crawler.timeout 값이 너무 작습니다: {timeout}")
        
        # 결과 출력
        if errors:
            print("\n❌ 오류:")
            for error in errors:
                print(f"  - {error}")
        
        if warnings:
            print("\n⚠️  경고:")
            for warning in warnings:
                print(f"  - {warning}")
        
        if not errors and not warnings:
            print("✅ 설정 파일이 유효합니다.")
        
        print()
    
    elif args.export:
        # JSON으로 내보내기
        try:
            with open(args.export, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
            print(f"✅ 설정을 {args.export}에 저장했습니다.")
        except Exception as e:
            print(f"❌ 설정 내보내기 실패: {e}", file=sys.stderr)
    
    else:
        print("옵션을 지정하세요: --show, --validate, --export")


async def main_legacy():
    """레거시 메인 함수 (하위 호환성)"""
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
    # 서브커맨드 기반 CLI 사용
    exit_code = asyncio.run(main())
    sys.exit(exit_code or 0)

