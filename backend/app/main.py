from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import engine, Base, SessionLocal, get_db
from app.api.news import router as news_router
from app.api.admin import router as admin_router
from app.models.news import News
from app.models.source import Source
from scripts.seed_sources import seed_sources


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时建表、迁移字段、填充种子数据。"""
    Base.metadata.create_all(bind=engine)

    # 将 pub_time 从 TIMESTAMPTZ 转为 TIMESTAMP（全链路 naive 北京时间）
    _migrate_pub_time_to_naive()

    db = SessionLocal()
    try:
        seed_sources(db, override=True)
    finally:
        db.close()

    yield


def _migrate_pub_time_to_naive() -> None:
    """将 pub_time 列从 TIMESTAMPTZ 转为 TIMESTAMP WITHOUT TIME ZONE，
    同时把已有时区值按北京时间转换，避免偏移。"""
    with engine.connect() as conn:
        col_info = conn.execute(text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name='news' AND column_name='pub_time'"
        )).first()
        if col_info and 'time zone' in (col_info[0] or ''):
            conn.execute(text(
                "ALTER TABLE news ALTER COLUMN pub_time "
                "TYPE TIMESTAMP WITHOUT TIME ZONE "
                "USING pub_time AT TIME ZONE 'Asia/Shanghai'"
            ))
            conn.commit()


app = FastAPI(
    title="News Hub API",
    description="资讯聚合平台后端 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(news_router)
app.include_router(admin_router)


@app.get("/api/categories")
def get_categories(db: Session = Depends(get_db)):
    """返回所有栏目及每个栏目下的数据源列表（动态从 Source 表读取）"""
    sources = (
        db.query(Source)
        .filter(Source.is_active.is_(True))
        .order_by(Source.sort_order)
        .all()
    )
    categories = {}
    for s in sources:
        categories.setdefault(s.category, []).append({
            "id": s.id,
            "name": s.name,
            "display_name": s.display_name,
            "crawl_type": s.crawl_type,
        })
    return {"code": 200, "data": categories}


@app.get("/api/tags")
def get_tags(category: str = None, db: Session = Depends(get_db)):
    """返回标签列表（可按栏目筛选）"""
    query = db.query(News.tags).filter(News.tags.isnot(None), News.tags != "")
    if category:
        query = query.filter(News.category == category)
    rows = query.all()
    tag_set = set()
    for (tags_str,) in rows:
        for t in tags_str.split(","):
            t = t.strip()
            if t:
                tag_set.add(t)
    return {"code": 200, "data": sorted(tag_set)}


@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "News Hub API is running"}
