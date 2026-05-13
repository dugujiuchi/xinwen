from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, DateTime, Text,
)
from sqlalchemy.sql import func

from app.database import Base


class CrawlLog(Base):
    """爬虫运行日志"""
    __tablename__ = "crawl_logs"

    id = Column(Integer, primary_key=True)
    source_name = Column(String(100), nullable=False, comment="来源名称")
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True))
    status = Column(String(20), default="running", comment="running/success/failed")
    items_count = Column(Integer, default=0)
    error_message = Column(Text)
