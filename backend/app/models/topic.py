from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey,
)
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY

from app.database import Base


class Topic(Base):
    """主题/方向表（预置 + 自定义统一存储）"""
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True, comment="主题名称")
    type = Column(String(20), default="preset", comment="类型: preset/custom")
    description = Column(Text, comment="描述")
    keywords = Column(ARRAY(String), comment="关联搜索关键词")
    created_by = Column(Integer, nullable=True, comment="创建者（第二期关联 users 表）")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class NewsTopic(Base):
    """新闻-主题关联表"""
    __tablename__ = "news_topics"

    news_id = Column(Integer, ForeignKey("news.id", ondelete="CASCADE"), primary_key=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True)
    relevance = Column(Float, default=1.0, comment="相关度评分（预留）")
