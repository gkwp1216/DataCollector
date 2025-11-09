import asyncio
import logging
import yaml
from modules.crawler import AsyncCrawler
from modules.database import init_db, save_item


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


async def main():
    with open("config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    db_path = cfg.get("db", {}).get("path", "data.db")
    targets = cfg.get("targets", [])

    await init_db(db_path)

    crawler = AsyncCrawler()
    try:
        # 간단히 순차 실행: 대상 목록을 순회하여 수집 및 저장
        for url in targets:
            logging.info("수집 시작: %s", url)
            item = await crawler.fetch_and_parse(url)
            if item:
                await save_item(db_path, item)
                logging.info("수집 및 저장됨: %s", item.get("title"))
            else:
                logging.warning("수집 실패: %s", url)
    finally:
        await crawler.close()


if __name__ == "__main__":
    asyncio.run(main())
