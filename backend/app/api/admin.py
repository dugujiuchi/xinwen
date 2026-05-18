"""管理端 API — 数据源 CRUD、爬虫触发、统计"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func as sa_func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.news import News
from app.models.source import Source
from app.models.crawl import CrawlLog
from app.schemas.source import SourceCreate, SourceUpdate, SourceResponse
from app.crawlers.factory import CrawlerFactory
from app.crawlers.manager import CrawlerManager
from app.crawlers.auto_detect import analyze_url
from app.api.auth import verify_admin

logger = logging.getLogger("api.admin")

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/sources")
def list_sources(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    """数据源列表（分页 + 搜索）"""
    query = db.query(Source)
    if search:
        kw = f"%{search}%"
        query = query.filter(
            or_(Source.name.ilike(kw), Source.display_name.ilike(kw))
        )
    if category:
        query = query.filter(Source.category == category)

    total = query.count()
    items = (
        query.order_by(Source.sort_order, Source.id)
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return {
        "code": 200,
        "data": {
            "items": [SourceResponse.model_validate(s) for s in items],
            "total": total,
            "page": page,
            "size": size,
        },
    }


@router.get("/sources/{source_id}")
def get_source(
    source_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    """获取单个数据源详情"""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="数据源不存在")
    return {
        "code": 200,
        "data": SourceResponse.model_validate(source).model_dump(),
    }


@router.post("/sources", status_code=201)
def create_source(
    body: SourceCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    """新增数据源"""
    # 检查名称是否已存在
    existing = db.query(Source).filter(Source.name == body.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"数据源名称 '{body.name}' 已存在")

    source = Source(**body.model_dump())
    db.add(source)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"数据源名称 '{body.name}' 已存在")
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="创建数据源失败，请检查配置后重试")
    db.refresh(source)
    return {
        "code": 201,
        "message": "数据源创建成功",
        "data": SourceResponse.model_validate(source).model_dump(),
    }


@router.put("/sources/{source_id}")
def update_source(
    source_id: int,
    body: SourceUpdate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    """编辑数据源"""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="数据源不存在")

    old_category = source.category
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(source, key, value)

    # 如果栏目变更，同步更新该源下所有新闻的栏目
    new_category = update_data.get("category")
    if new_category is not None and new_category != old_category:
        updated_rows = (
            db.query(News)
            .filter(News.source_id == source_id)
            .update({"category": new_category}, synchronize_session=False)
        )
        print(f"[admin] 数据源 '{source.name}' 栏目变更 ({old_category} -> {new_category})，已同步更新 {updated_rows} 条新闻", flush=True)

    db.commit()
    db.refresh(source)
    return {
        "code": 200,
        "message": "数据源更新成功",
        "data": SourceResponse.model_validate(source).model_dump(),
    }


@router.delete("/sources/{source_id}")
def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    """删除数据源（关联的 news 记录保留但 source_id 变为孤立）"""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="数据源不存在")

    db.delete(source)
    db.commit()
    return {"code": 200, "message": "数据源已删除"}


@router.post("/sources/analyze")
def analyze_source(
    body: dict,
    _: bool = Depends(verify_admin),
):
    """根据 URL 自动分析数据源类型和配置。

    接收 {"url": "..."} ，返回建议的 crawl_type、config 和预览数据。
    """
    url = (body.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="请输入 URL")
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="URL 必须以 http:// 或 https:// 开头")

    result = analyze_url(url)
    return {"code": 200, "data": result}


@router.post("/sources/test-config")
def test_config_crawl(
    body: dict,
    _: bool = Depends(verify_admin),
):
    """根据原始 config 测试抓取（无需事先保存数据源）。

    接收 {"crawl_type": "selector", "config": {...}} ，返回预览数据。
    """
    crawl_type = (body.get("crawl_type") or "").strip()
    config = body.get("config") or {}

    if not crawl_type:
        raise HTTPException(status_code=400, detail="请指定抓取方式 crawl_type")
    if not config:
        raise HTTPException(status_code=400, detail="请提供抓取配置 config")

    # 构造临时 Source 对象
    from app.models.source import Source as TempSource
    tmp = TempSource()
    tmp.crawl_type = crawl_type
    tmp.config = config
    tmp.name = "_test_"
    tmp.display_name = "测试"
    tmp.category = "ai"

    try:
        fetcher = CrawlerFactory.get_crawler(crawl_type)
        items = fetcher.fetch(tmp)
        return {
            "code": 200,
            "data": {
                "source": "测试配置",
                "count": len(items),
                "items": items[:10],
            },
        }
    except Exception:
        logger.exception("测试配置抓取失败 crawl_type=%s", crawl_type)
        raise HTTPException(status_code=500, detail="测试抓取失败，请检查数据源配置或网络连接")


@router.post("/sources/{source_id}/test")
def test_crawl_source(
    source_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    """测试抓取单个数据源（返回预览数据，不写入数据库）"""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="数据源不存在")

    try:
        fetcher = CrawlerFactory.get_crawler(source.crawl_type)
        items = fetcher.fetch(source)
        return {
            "code": 200,
            "data": {
                "source": source.display_name,
                "count": len(items),
                "items": items[:10],
            },
        }
    except Exception:
        logger.exception("测试抓取失败 source_id=%d name=%s", source_id, source.name)
        raise HTTPException(status_code=500, detail="测试抓取失败，请检查数据源配置或网络连接")


@router.post("/sources/{source_id}/crawl")
def crawl_single_source(
    source_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    """正式抓取单个数据源（写入数据库，按 link 去重）"""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="数据源不存在")

    manager = CrawlerManager()
    result = manager.run_one(source_id)

    if result.get("status") == "success":
        return {"code": 200, "message": f"抓取完成，新增 {result.get('count', 0)} 条", "data": result}
    elif result.get("status") == "skipped":
        return {"code": 200, "message": result.get("error", "数据源未启用"), "data": result}
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "抓取失败"))


@router.post("/crawl/trigger")
def trigger_crawl(_: bool = Depends(verify_admin)):
    """触发全量爬取"""
    manager = CrawlerManager()
    results = manager.run_all()
    return {"code": 200, "message": "爬取完成", "data": results}


@router.get("/crawl/logs")
def get_crawl_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    """爬取日志（分页）"""
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
        "data": {
            "items": [
                {
                    "id": log.id,
                    "source_name": log.source_name,
                    "source_id": log.source_id,
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


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    """仪表盘统计"""
    # 数据源总数
    total_sources = db.query(Source).count()
    active_sources = db.query(Source).filter(Source.is_active.is_(True)).count()

    # 新闻总数
    total_news = db.query(News).count()

    # 今日新增新闻
    today = sa_func.current_date()
    today_news = (
        db.query(News)
        .filter(sa_func.date(News.crawled_at) == today)
        .count()
    )

    # 最近爬取日志
    last_crawl = (
        db.query(CrawlLog)
        .order_by(CrawlLog.started_at.desc())
        .first()
    )

    # 各栏目新闻数
    category_counts = (
        db.query(News.category, sa_func.count(News.id))
        .filter(News.category.isnot(None))
        .group_by(News.category)
        .all()
    )

    return {
        "code": 200,
        "data": {
            "total_sources": total_sources,
            "active_sources": active_sources,
            "total_news": total_news,
            "today_news": today_news,
            "last_crawl_time": (
                last_crawl.started_at.isoformat() if last_crawl else None
            ),
            "last_crawl_status": last_crawl.status if last_crawl else None,
            "category_news_count": dict(category_counts),
        },
    }
