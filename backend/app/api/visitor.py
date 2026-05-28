"""访客记录 API — 公开记录 + 管理端统计"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.visitor_log import VisitorLog
from app.api.auth import verify_admin
from app.utils.ip_lookup import lookup_ip

logger = logging.getLogger("visitor")

router = APIRouter(prefix="/api/visitor", tags=["visitor"])


@router.post("/record")
async def record_visit(request: Request, db: Session = Depends(get_db)):
    """记录一次访问（公开接口，前端首页加载时调用）"""
    client_ip = _get_client_ip(request)
    location = {}
    try:
        location = await lookup_ip(client_ip)
    except Exception:
        pass

    log_entry = VisitorLog(
        ip=client_ip,
        country=location.get("country", ""),
        region=location.get("region", ""),
        city=location.get("city", ""),
        isp=location.get("isp", ""),
    )
    db.add(log_entry)
    db.commit()
    return {"code": 200, "message": "ok"}


# ------------------------------------------------------------------
# 管理端统计 API
# ------------------------------------------------------------------

@router.get("/admin/logs")
def get_visitor_logs(
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    _=Depends(verify_admin),
):
    """访客记录列表（分页）"""
    total = db.query(func.count(VisitorLog.id)).scalar() or 0
    rows = (
        db.query(VisitorLog)
        .order_by(VisitorLog.visit_time.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    items = [
        {
            "id": r.id,
            "ip": r.ip,
            "country": r.country,
            "region": r.region,
            "city": r.city,
            "isp": r.isp,
            "visit_time": r.visit_time.isoformat() if r.visit_time else None,
        }
        for r in rows
    ]
    return {"code": 200, "data": {"items": items, "total": total, "page": page, "size": size}}


@router.get("/admin/stats")
def get_visitor_stats(
    period: str = "week",  # week / month
    db: Session = Depends(get_db),
    _=Depends(verify_admin),
):
    """访客统计数据（按周/月汇总）"""
    now = datetime.utcnow()
    if period == "week":
        start = now - timedelta(days=7)
    else:
        start = now - timedelta(days=30)

    # 按天分组统计
    daily_rows = (
        db.query(
            cast(VisitorLog.visit_time, Date).label("day"),
            func.count(VisitorLog.id).label("cnt"),
        )
        .filter(VisitorLog.visit_time >= start)
        .group_by("day")
        .order_by("day")
        .all()
    )

    # 按省份分组统计
    region_rows = (
        db.query(
            VisitorLog.region,
            func.count(VisitorLog.id).label("cnt"),
        )
        .filter(
            VisitorLog.visit_time >= start,
            VisitorLog.region.isnot(None),
            VisitorLog.region != "",
        )
        .group_by(VisitorLog.region)
        .order_by(func.count(VisitorLog.id).desc())
        .all()
    )

    # 按城市分组统计（Top 20）
    city_rows = (
        db.query(
            VisitorLog.city,
            VisitorLog.region,
            func.count(VisitorLog.id).label("cnt"),
        )
        .filter(
            VisitorLog.visit_time >= start,
            VisitorLog.city.isnot(None),
            VisitorLog.city != "",
        )
        .group_by(VisitorLog.city, VisitorLog.region)
        .order_by(func.count(VisitorLog.id).desc())
        .limit(20)
        .all()
    )

    # 总访问量
    total_visits = db.query(func.count(VisitorLog.id)).scalar() or 0
    period_visits = sum(r.cnt for r in daily_rows)

    return {
        "code": 200,
        "data": {
            "total_visits": total_visits,
            "period_visits": period_visits,
            "daily": [{"day": str(r.day), "count": r.cnt} for r in daily_rows],
            "by_region": [{"region": r.region, "count": r.cnt} for r in region_rows],
            "by_city": [
                {"city": r.city, "region": r.region, "count": r.cnt}
                for r in city_rows
            ],
        },
    }


def _get_client_ip(request: Request) -> str:
    """从请求中获取客户端真实 IP（优先取反向代理转发头）"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host or "unknown"
    return "unknown"
