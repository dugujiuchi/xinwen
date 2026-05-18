from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NewsItem(BaseModel):
    """新闻响应体"""
    id: int
    title: str
    link: str
    source_name: str
    summary: Optional[str] = None
    category: Optional[str] = None
    source_id: Optional[int] = None
    content: Optional[str] = None
    tags: Optional[str] = None
    pub_time: Optional[datetime] = None
    crawled_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class NewsQueryParams(BaseModel):
    """新闻查询参数"""
    page: int = 1
    size: int = 20
    search: Optional[str] = None
    source: Optional[str] = None
    source_id: Optional[int] = None
    category: Optional[str] = None
    tags: Optional[str] = None
