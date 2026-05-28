"""访客访问记录模型"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, func

from app.database import Base


class VisitorLog(Base):
    __tablename__ = "visitor_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String(45), nullable=False, index=True, comment="访问者IP")
    country = Column(String(50), comment="国家")
    region = Column(String(50), comment="省份")
    city = Column(String(50), comment="城市")
    isp = Column(String(100), comment="运营商")
    visit_time = Column(DateTime, server_default=func.now(), index=True, comment="访问时间")

    def __repr__(self):
        return f"<VisitorLog id={self.id} ip={self.ip} time={self.visit_time}>"
