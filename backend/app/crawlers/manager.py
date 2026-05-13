from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.crawl import CrawlLog
from app.models.news import News
from app.crawlers.base import BaseCrawler


class CrawlerManager:
    """爬虫管理器。

    - 串行执行所有注册爬虫（内存限制）
    - 自动去重、写入数据库
    - 记录运行日志
    """

    def __init__(self):
        self._crawlers: list[BaseCrawler] = []

    def register(self, crawler: BaseCrawler):
        """注册一个爬虫"""
        self._crawlers.append(crawler)

    def register_all(self, crawlers: list[BaseCrawler]):
        """批量注册"""
        self._crawlers.extend(crawlers)

    @property
    def crawlers(self) -> list[BaseCrawler]:
        return list(self._crawlers)

    def run_all(self) -> list[dict]:
        """串行执行所有爬虫"""
        results = []
        for crawler in self._crawlers:
            result = self.run_one(crawler.name)
            results.append(result)
        return results

    def run_one(self, name: str) -> dict:
        """执行单个爬虫"""
        crawler = next((c for c in self._crawlers if c.name == name), None)
        if not crawler:
            return {"name": name, "status": "failed", "error": "未找到爬虫"}

        db = SessionLocal()
        log = CrawlLog(
            source_name=crawler.source_name,
            started_at=datetime.now(timezone.utc),
        )
        db.add(log)
        db.commit()

        try:
            print(f"[{crawler.name}] 开始抓取...")
            items = crawler.fetch()
            count = self._save_items(db, items, crawler.source_name)

            log.status = "success"
            log.items_count = count
            log.finished_at = datetime.now(timezone.utc)
            db.commit()

            print(f"[{crawler.name}] 完成，获取 {count} 条")
            return {"name": crawler.name, "status": "success", "count": count}
        except Exception as e:
            log.status = "failed"
            log.error_message = str(e)
            log.finished_at = datetime.now(timezone.utc)
            db.commit()
            print(f"[{crawler.name}] 失败: {e}")
            return {"name": crawler.name, "status": "failed", "error": str(e)}
        finally:
            db.close()

    def _save_items(self, db: Session, items: list[dict], source_name: str) -> int:
        """保存抓取结果到数据库（去重）"""
        count = 0
        for item in items:
            exists = db.query(News).filter(News.link == item["link"]).first()
            if exists:
                continue

            news = News(
                title=item["title"],
                link=item["link"],
                source_name=source_name,
                summary=item.get("summary", ""),
                pub_time=item.get("time"),
            )
            db.add(news)
            count += 1

        db.commit()
        return count
