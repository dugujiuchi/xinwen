from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel


class SourceConfig(BaseModel):
    """数据源配置（JSON字段的schema提示）"""
    url: str = ""
    method: str = "GET"
    headers: Optional[dict[str, Any]] = None
    body: Optional[str] = None
    encoding: Optional[str] = None
    response_type: Optional[str] = None
    item_path: Optional[str] = None
    list_selector: Optional[str] = None
    extract_mode: Optional[str] = None
    state_key: Optional[str] = None
    state_path: Optional[str] = None
    scroll_times: Optional[int] = None
    wait_selector: Optional[str] = None
    mapping: Optional[dict[str, Any]] = None
    fetch_content: bool = False

    model_config = {"extra": "allow"}


class SourceBase(BaseModel):
    """数据源基础字段"""
    name: str
    display_name: str
    category: str = "ai"  # ai/industry/tech/media
    crawl_type: str = "browser"  # api/selector/browser
    config: dict = {}
    is_active: bool = True
    sort_order: int = 0


class SourceCreate(SourceBase):
    """创建数据源请求"""
    pass


class SourceUpdate(BaseModel):
    """更新数据源请求（所有字段可选）"""
    display_name: Optional[str] = None
    category: Optional[str] = None
    crawl_type: Optional[str] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class SourceResponse(SourceBase):
    """数据源响应体"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
