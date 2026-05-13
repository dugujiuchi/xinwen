from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.crawl import CrawlLog
from app.crawlers import CrawlerManager
from app.crawlers.sources import GeekParkCrawler

router = APIRouter(prefix="/api/crawl", tags=["crawl"])

# 初始化爬虫管理器（全局单例）
crawl_manager = CrawlerManager()
crawl_manager.register(GeekParkCrawler())


@router.post("/trigger")
def trigger_crawl():
    """手动触发全量爬虫"""
    results = crawl_manager.run_all()
    return {
        "code": 200,
        "message": "爬虫执行完成",
        "data": results,
    }


@router.get("/logs")
def get_crawl_logs(
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
):
    """获取爬虫运行日志"""
    total = db.query(CrawlLog).count()
    logs = (
        db.query(CrawlLog)
        .order_by(CrawlLog.started_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": [
                {
                    "id": log.id,
                    "source_name": log.source_name,
                    "started_at": log.started_at.isoformat() if log.started_at else None,
                    "finished_at": log.finished_at.isoformat() if log.finished_at else None,
                    "status": log.status,
                    "items_count": log.items_count,
                    "error_message": log.error_message,
                }
                for log in logs
            ],
            "total": total,
            "page": page,
            "size": size,
        },
    }
