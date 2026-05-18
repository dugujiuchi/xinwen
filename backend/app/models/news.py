from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean,
    ForeignKey, Index,
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
    category = Column(String(50), index=True, comment="栏目: ai/industry/tech/media")
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="SET NULL"), nullable=True, index=True)
    content = Column(Text, comment="正文内容（深度抓取时填充）")
    tags = Column(String(500), comment="标签，逗号分隔")
    pub_time = Column(DateTime(timezone=False), comment="原始发布时间（北京时间）")
    crawled_at = Column(DateTime(timezone=True), server_default=func.now(), comment="抓取时间")
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index("idx_news_pub_time", pub_time.desc()),
        Index("idx_news_source", source_name),
        Index("idx_news_category_pub_time", category, pub_time.desc()),
    )

    def __repr__(self):
        return f"<News(id={self.id}, title={self.title[:30]})>"
