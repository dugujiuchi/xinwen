from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.api.news import router as news_router
from app.api.crawl import router as crawl_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时创建所有表"""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="News Hub API",
    description="资讯聚合平台后端 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(news_router)
app.include_router(crawl_router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "News Hub API is running"}
