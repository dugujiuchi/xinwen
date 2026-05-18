from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func

from app.database import Base


class Source(Base):
    """数据源配置表 —— 驱动所有抓取行为"""
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, comment="数据源标识（英文）")
    display_name = Column(String(100), nullable=False, comment="显示名称（中文）")
    category = Column(String(50), nullable=False, index=True, comment="栏目: ai/industry/tech/media")
    crawl_type = Column(String(20), nullable=False, comment="抓取方式: api/selector/browser")
    config = Column(JSON, nullable=False, default=dict, comment="抓取配置JSON")
    is_active = Column(Boolean, default=True, comment="是否启用抓取")
    sort_order = Column(Integer, default=0, comment="排序序号")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    def __repr__(self):
        return f"<Source(id={self.id}, name={self.name}, display_name={self.display_name})>"
