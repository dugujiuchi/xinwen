"""爬虫管理器 — DB 驱动，从 Source 表读取活跃源并抓取"""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.crawl import CrawlLog
from app.models.news import News
from app.models.source import Source
from app.crawlers.factory import CrawlerFactory

logger = logging.getLogger("crawler.manager")


class CrawlerManager:
    """爬虫管理器。

    - 从 Source 表读取所有 is_active 的数据源
    - 通过 CrawlerFactory 自动选择合适的 Fetcher
    - 串行执行，自动去重、写入数据库
    - 记录运行日志
    """

    def run_all(self) -> list[dict]:
        """遍历所有活跃 Source，串行抓取。

        Returns:
            每个源的抓取结果列表
        """
        db = SessionLocal()
        try:
            sources = (
                db.query(Source)
                .filter(Source.is_active.is_(True))
                .order_by(Source.sort_order)
                .all()
            )
        finally:
            db.close()

        results = []
        for source in sources:
            result = self.run_one(source.id)
            results.append(result)
        return results

    def run_one(self, source_id: int) -> dict:
        """抓取单个源（按 source.id）。

        Args:
            source_id: 数据源 ID

        Returns:
            {"name": ..., "status": "success"|"failed", "count": ..., "error": ...}
        """
        db = SessionLocal()
        try:
            source = db.query(Source).filter(Source.id == source_id).first()
            if not source:
                return {"name": f"id={source_id}", "status": "failed", "error": "数据源不存在"}

            if not source.is_active:
                return {"name": source.name, "status": "skipped", "error": "数据源未启用"}

            # 创建抓取日志
            log = CrawlLog(
                source_name=source.display_name,
                source_id=source.id,
                started_at=datetime.now(timezone.utc),
            )
            db.add(log)
            db.commit()

            try:
                logger.info("[%s] 开始抓取...", source.name)

                crawler = CrawlerFactory.get_crawler(source.crawl_type)
                items = crawler.fetch(source)

                count = self._save_items(db, items, source)

                log.status = "success"
                log.items_count = count
                log.finished_at = datetime.now(timezone.utc)
                db.commit()

                logger.info("[%s] 完成，获取 %d 条", source.name, count)
                return {"name": source.name, "status": "success", "count": count}
            except Exception as e:
                log.status = "failed"
                log.error_message = repr(e)
                log.finished_at = datetime.now(timezone.utc)
                db.commit()
                logger.warning("[%s] 失败: %r", source.name, e)
                return {"name": source.name, "status": "failed", "error": repr(e)}
        finally:
            db.close()

    def _save_items(
        self, db: Session, items: list[dict], source: Source
    ) -> int:
        """保存抓取结果到数据库（按 link 去重）。

        Args:
            db: 数据库会话
            items: 新闻列表
            source: 对应的 Source 模型实例

        Returns:
            新增条数
        """
        count = 0
        for item in items:
            # link 截断（字段长度 2048）
            link = (item.get("link") or "")[:2048]
            if not link:
                continue

            # 按 link 去重
            exists = db.query(News).filter(News.link == link).first()
            if exists:
                continue

            # tags：优先用抓取到的标签，没有则用数据源名称
            tags = item.get("tags")
            if isinstance(tags, list):
                tags = ",".join(tags)
            if not tags:
                tags = source.display_name

            pub_time = item.get("time")
            if not isinstance(pub_time, datetime):
                pub_time = None  # 解析失败留空，不伪造时间

            news = News(
                title=item.get("title", ""),
                link=link,
                source_name=source.display_name,
                source_id=source.id,
                category=source.category,
                summary=item.get("summary", ""),
                content=item.get("content", ""),
                tags=tags or "",
                pub_time=pub_time,
            )
            db.add(news)
            count += 1

        db.commit()
        return count
