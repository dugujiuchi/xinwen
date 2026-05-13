from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.news import News
from app.schemas.news import NewsItem, NewsQueryParams
from app.schemas.common import PaginatedResponse, PaginatedData

router = APIRouter(prefix="/api/news", tags=["news"])


def _build_search_query(db: Session, params: NewsQueryParams):
    """构建带搜索和过滤的查询"""
    query = db.query(News).filter(News.is_active.is_(True))

    # 关键词搜索（标题 + 来源 + 摘要）
    if params.search:
        keyword = f"%{params.search}%"
        query = query.filter(
            or_(
                News.title.ilike(keyword),
                News.source_name.ilike(keyword),
                News.summary.ilike(keyword),
            )
        )

    # 来源过滤
    if params.source:
        query = query.filter(News.source_name == params.source)

    return query


@router.get("", response_model=PaginatedResponse[NewsItem])
def list_news(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """获取新闻列表（分页、搜索、过滤）"""
    params = NewsQueryParams(page=page, size=size, search=search, source=source)
    query = _build_search_query(db, params)

    total = query.count()
    items = (
        query.order_by(News.pub_time.desc().nullslast())
        .offset((params.page - 1) * params.size)
        .limit(params.size)
        .all()
    )

    return PaginatedResponse[NewsItem](
        data=PaginatedData[NewsItem](
            items=[NewsItem.model_validate(item) for item in items],
            total=total,
            page=params.page,
            size=params.size,
        )
    )
