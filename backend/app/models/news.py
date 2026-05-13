from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean,
    Index,
)
from sqlalchemy.sql import func

from app.database import Base


class News(Base):
    """新闻主表"""
    __tablename__ = "news"

    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False, comment="标题")
    link = Column(String(2048), nullable=False, unique=True, comment="原文链接")
    source_name = Column(String(100), nullable=False, comment="来源名称")
    source_type = Column(String(20), default="crawler", comment="来源类型: crawler/user_submitted")
    summary = Column(Text, comment="摘要")
    pub_time = Column(DateTime(timezone=True), comment="原始发布时间")
    crawled_at = Column(DateTime(timezone=True), server_default=func.now(), comment="抓取时间")
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index("idx_news_pub_time", pub_time.desc()),
        Index("idx_news_source", source_name),
    )

    def __repr__(self):
        return f"<News(id={self.id}, title={self.title[:30]})>"
