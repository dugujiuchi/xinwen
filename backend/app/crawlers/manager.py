"""爬虫管理器 — DB 驱动，从 Source 表读取活跃源并抓取

支持：
- 单源超时保护（默认 10 分钟），防止个别源卡住阻塞整体调度
- 总超时保护（run_all 级别），防止整体运行时间超过调度间隔
- 进度日志，便于定位慢/卡住的数据源
"""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.crawl import CrawlLog
from app.models.news import News
from app.models.source import Source
from app.crawlers.base import BaseCrawler
from app.crawlers.factory import CrawlerFactory

logger = logging.getLogger("crawler.manager")

# 单个数据源抓取超时（秒）
DEFAULT_SOURCE_TIMEOUT = 600  # 10 分钟


class SourceTimeoutError(Exception):
    """单个数据源抓取超时异常。"""
    pass


class CrawlerManager:
    """爬虫管理器。

    - 从 Source 表读取所有 is_active 的数据源
    - 通过 CrawlerFactory 自动选择合适的 Fetcher
    - 串行执行，自动去重、写入数据库
    - 记录运行日志
    - 单源超时保护 + 总超时保护
    """

    def run_all(self, timeout_seconds: float | None = None) -> list[dict]:
        """遍历所有活跃 Source，串行抓取。

        Args:
            timeout_seconds: 整体超时（秒），超时后跳过剩余源。None 表示不限制。

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

        total = len(sources)
        logger.info("共 %d 个活跃数据源待抓取", total)

        overall_start = datetime.now(timezone.utc)
        results = []

        for idx, source in enumerate(sources, start=1):
            # 整体超时检查
            if timeout_seconds:
                elapsed = (datetime.now(timezone.utc) - overall_start).total_seconds()
                if elapsed >= timeout_seconds:
                    logger.warning(
                        "整体超时（%.0fs ≥ %.0fs），跳过剩余 %d 个源",
                        elapsed, timeout_seconds, total - idx + 1,
                    )
                    for remaining in sources[idx - 1:]:
                        results.append({
                            "name": remaining.name,
                            "status": "skipped",
                            "error": "整体超时，本轮跳过",
                        })
                    break

            logger.info("[%d/%d] 正在抓取: %s", idx, total, source.name)
            result = self.run_one(source.id, timeout=DEFAULT_SOURCE_TIMEOUT)
            results.append(result)

        # 每次批量爬取结束后释放 Chrome 内存
        try:
            from app.crawlers.browser_crawler import cleanup_browser
            cleanup_browser()
        except Exception:
            pass

        # 汇总统计
        success = sum(1 for r in results if r.get("status") == "success")
        failed = sum(1 for r in results if r.get("status") == "failed")
        skipped = sum(1 for r in results if r.get("status") == "skipped")
        total_elapsed = (datetime.now(timezone.utc) - overall_start).total_seconds()
        logger.info(
            "本轮抓取完成: 成功=%d 失败=%d 跳过=%d 总耗时=%.0fs",
            success, failed, skipped, total_elapsed,
        )

        return results

    def run_one(self, source_id: int, timeout: float = DEFAULT_SOURCE_TIMEOUT) -> dict:
        """抓取单个源（按 source.id），带超时保护。

        Args:
            source_id: 数据源 ID
            timeout: 单源超时（秒），超时后返回 failed 结果

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

                items = self._fetch_with_timeout(crawler, source, timeout)

                count = self._save_items(db, items, source)

                log.status = "success"
                log.items_count = count
                log.finished_at = datetime.now(timezone.utc)
                db.commit()

                logger.info("[%s] 完成，获取 %d 条", source.name, count)
                return {"name": source.name, "status": "success", "count": count}
            except SourceTimeoutError:
                log.status = "failed"
                log.error_message = f"单源超时（{timeout}s）"
                log.finished_at = datetime.now(timezone.utc)
                db.commit()
                logger.warning("[%s] 超时（%ds），跳过", source.name, timeout)
                return {"name": source.name, "status": "failed", "error": f"超时（{timeout}s）"}
            except Exception as e:
                log.status = "failed"
                log.error_message = repr(e)
                log.finished_at = datetime.now(timezone.utc)
                db.commit()
                logger.warning("[%s] 失败: %r", source.name, e)
                return {"name": source.name, "status": "failed", "error": repr(e)}
        finally:
            db.close()

    @staticmethod
    def _fetch_with_timeout(crawler, source: Source, timeout: float) -> list[dict]:
        """在独立线程中执行抓取，超时则抛出 SourceTimeoutError。

        Args:
            crawler: Crawler 实例
            source: 数据源模型
            timeout: 超时秒数

        Returns:
            抓取结果列表

        Raises:
            SourceTimeoutError: 抓取超时
        """
        import threading

        result_container: list = []
        error_container: Exception | None = None
        done = threading.Event()

        def _target():
            nonlocal error_container
            try:
                items = crawler.fetch(source)
                result_container.extend(items)
            except Exception as e:
                error_container = e
            finally:
                done.set()

        thread = threading.Thread(target=_target, daemon=True)
        thread.start()

        if not done.wait(timeout=timeout):
            raise SourceTimeoutError(
                f"[{source.name}] 抓取超时（{timeout}s），线程将被丢弃"
            )

        if error_container:
            raise error_container

        return list(result_container)

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
        # 同批次内已见过的 link（会话 autoflush=False，DB 查询看不到待插入行，
        # 必须用本地集合兜底，否则单批次内重复 link 会触发唯一约束冲突）
        seen_links: set[str] = set()
        for item in items:
            # 归一化 link（剥离 request_id / utm_* 等追踪参数），保证去重 key 稳定；
            # 再截断（字段长度 2048）
            link = (item.get("link") or "").strip()
            if link:
                link = BaseCrawler.canonicalize_link(link)[:2048]
            if not link:
                continue

            # 按 link 去重（批次内 + 数据库）
            if link in seen_links:
                continue
            exists = db.query(News).filter(News.link == link).first()
            if exists:
                continue
            seen_links.add(link)

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
