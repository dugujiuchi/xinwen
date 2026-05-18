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

    # 来源过滤（按名称，向下兼容）
    if params.source:
        query = query.filter(News.source_name == params.source)

    # 来源过滤（按 ID）
    if params.source_id is not None:
        query = query.filter(News.source_id == params.source_id)

    # 栏目过滤（精确匹配）
    if params.category:
        query = query.filter(News.category == params.category)

    # 标签过滤（模糊匹配，tags 为逗号分隔字符串）
    if params.tags:
        for tag in params.tags.split(","):
            tag = tag.strip()
            if tag:
                query = query.filter(News.tags.ilike(f"%{tag}%"))

    return query


@router.get("", response_model=PaginatedResponse[NewsItem])
def list_news(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    source: Optional[str] = None,
    source_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """获取新闻列表（分页、搜索、过滤）"""
    params = NewsQueryParams(
        page=page, size=size, search=search, source=source,
        source_id=source_id, category=category, tags=tags,
    )
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
