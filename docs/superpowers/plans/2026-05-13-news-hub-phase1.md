# 资讯聚合平台 Phase 1 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建基础框架（Docker Compose + FastAPI + PostgreSQL + Vue 3），实现新闻展示和爬虫功能。

**Architecture:** 前后端分离，后端 FastAPI 提供 REST API，前端 Vue 3 SPA 通过 Axios 调用 API，爬虫使用 Playwright 统一框架，全部容器化通过 Docker Compose 编排。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + PostgreSQL 15 + Vue 3 + Vite + Nginx + Playwright + Docker Compose

---

## 文件结构总览

```
web_aisearch/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── Dockerfile.crawler
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── news.py
│   │   │   ├── topic.py
│   │   │   └── crawl.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── news.py
│   │   │   └── common.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── news.py
│   │   │   └── crawl.py
│   │   └── crawlers/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── manager.py
│   │       └── sources/
│   │           ├── __init__.py
│   │           └── geekpark.py
│   └── scripts/
│       └── init_db.sql
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.js
│       ├── App.vue
│       ├── router/
│       │   └── index.js
│       ├── api/
│       │   └── index.js
│       ├── views/
│       │   └── Home.vue
│       ├── components/
│       │   ├── NewsCard.vue
│       │   ├── NewsGrid.vue
│       │   ├── SearchBar.vue
│       │   ├── TabNav.vue
│       │   ├── TagFilter.vue
│       │   └── Pagination.vue
│       └── assets/
│           └── style.css
└── docs/
    └── specs/
```

---

### Task 1: 项目脚手架（Docker Compose + 配置文件）

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`

- [ ] **Step 1: 创建 .env.example**

```bash
touch D:/Work/ai_websearch/web_aisearch/.env.example
```

```
# PostgreSQL
POSTGRES_USER=newsuser
POSTGRES_PASSWORD=changeme123
POSTGRES_DB=news_hub
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# API
API_PORT=8000
API_HOST=0.0.0.0
ENVIRONMENT=development
LOG_LEVEL=info

# JWT (第二期使用)
SECRET_KEY=change-this-to-random-secret-key
```

- [ ] **Step 2: 创建 docker-compose.yml**

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:15-alpine
    container_name: news-postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-newsuser}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-changeme123}
      POSTGRES_DB: ${POSTGRES_DB:-news_hub}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./backend/scripts/init_db.sql:/docker-entrypoint-initdb.d/init_db.sql
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-newsuser} -d ${POSTGRES_DB:-news_hub}"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: news-api
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-newsuser}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-changeme123}
      POSTGRES_DB: ${POSTGRES_DB:-news_hub}
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      ENVIRONMENT: ${ENVIRONMENT:-development}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  crawler:
    build:
      context: ./backend
      dockerfile: Dockerfile.crawler
    container_name: news-crawler
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-newsuser}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-changeme123}
      POSTGRES_DB: ${POSTGRES_DB:-news_hub}
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: news-nginx
    ports:
      - "80:80"
    volumes:
      - ./frontend/nginx.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - api
    restart: unless-stopped

volumes:
  pgdata:
```

- [ ] **Step 3: 创建 requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy==2.0.35
psycopg2-binary==2.9.9
alembic==1.13.0
pydantic-settings==2.4.0
playwright==1.47.0
apscheduler==3.10.4
httpx==0.27.0
pytest==8.3.0
pytest-asyncio==0.24.0
```

- [ ] **Step 4: 创建 backend/app/__init__.py**

```python
# 空文件，标记为 Python 包
```

- [ ] **Step 5: 验证 Docker Compose 配置**

```bash
cd D:/Work/ai_websearch/web_aisearch && docker-compose config
```

Expected: 无错误输出，显示合并后的配置

- [ ] **Step 6: 提交**

```bash
git init
git add -A
git commit -m "chore: 项目脚手架 - Docker Compose + 配置文件"
```

---

### Task 2: 后端配置 + 数据库连接

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/main.py`

- [ ] **Step 1: 创建 config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL
    postgres_user: str = "newsuser"
    postgres_password: str = "changeme123"
    postgres_db: str = "news_hub"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    environment: str = "development"
    log_level: str = "info"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = {"env_prefix": ""}


settings = Settings()
```

- [ ] **Step 2: 创建 database.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 依赖：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 3: 创建 main.py**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base


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


@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "News Hub API is running"}
```

- [ ] **Step 4: 测试 API 启动**

```bash
cd D:/Work/ai_websearch/web_aisearch
# 先启动 postgres
docker-compose up -d postgres
# 启动 API
docker-compose up --build api
```

打开浏览器访问 http://localhost:8000/api/health，预期返回 `{"status": "ok"}`

- [ ] **Step 5: 验证 API 文档**

访问 http://localhost:8000/docs，预期显示 Swagger UI 页面

- [ ] **Step 6: 提交**

```bash
git add -A
git commit -m "feat: 后端配置 + 数据库连接 + FastAPI 入口"
```

---

### Task 3: SQLAlchemy 模型

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/news.py`
- Create: `backend/app/models/topic.py`
- Create: `backend/app/models/crawl.py`
- Create: `backend/scripts/init_db.sql`

- [ ] **Step 1: 创建 models/__init__.py**

```python
from app.models.news import News
from app.models.topic import Topic, NewsTopic
from app.models.crawl import CrawlLog

__all__ = ["News", "Topic", "NewsTopic", "CrawlLog"]
```

- [ ] **Step 2: 创建 models/news.py**

```python
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
```

- [ ] **Step 3: 创建 models/topic.py**

```python
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float,
    ForeignKey, Table,
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
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="创建者")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class NewsTopic(Base):
    """新闻-主题关联表"""
    __tablename__ = "news_topics"

    news_id = Column(Integer, ForeignKey("news.id", ondelete="CASCADE"), primary_key=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True)
    relevance = Column(Float, default=1.0, comment="相关度评分（预留）")
```

- [ ] **Step 4: 创建 models/crawl.py**

```python
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
```

- [ ] **Step 5: 创建 init_db.sql**

```sql
-- 数据库初始化脚本（Docker entrypoint 自动执行）
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

`pg_trgm` 扩展后续用于 LIKE 搜索性能优化（三元组索引）。

- [ ] **Step 6: 验证模型创建**

启动容器并确认表已创建：

```bash
docker-compose up -d postgres
# 进入 API 容器看表是否创建
docker-compose run --rm api python -c "
from app.models import News, Topic, NewsTopic, CrawlLog
from app.database import engine, Base
Base.metadata.create_all(bind=engine)
print('所有表创建成功')
"
```

然后用 `docker-compose run --rm api python -c "from app.database import SessionLocal; db = SessionLocal(); print(db.execute('SELECT table_name FROM information_schema.tables WHERE table_schema=\\'public\\'').fetchall())"` 查看表清单。

Expected: 应包含 `news`, `topics`, `news_topics`, `crawl_logs` 四张表。

- [ ] **Step 7: 提交**

```bash
git add -A
git commit -m "feat: SQLAlchemy 数据模型 + 初始化 SQL"
```

---

### Task 4: Alembic 数据库迁移

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial.py`

- [ ] **Step 1: 初始化 Alembic**

```bash
cd D:/Work/ai_websearch/web_aisearch/backend
alembic init alembic
```

- [ ] **Step 2: 修改 alembic.ini**

```ini
[alembic]
script_location = alembic
# sqlalchemy.url 留空，由 env.py 动态设置
sqlalchemy.url =

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 3: 修改 alembic/env.py**

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.database import Base
from app.models import News, Topic, NewsTopic, CrawlLog  # noqa: 确保模型注册

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: 生成自动迁移**

```bash
cd D:/Work/ai_websearch/web_aisearch/backend
# 确保 postgres 在运行
docker-compose up -d postgres
# 生成迁移脚本
alembic revision --autogenerate -m "initial"
```

Expected: `alembic/versions/` 目录下生成 `0001_initial.py` 文件

- [ ] **Step 5: 执行迁移**

```bash
alembic upgrade head
```

Expected: `INFO  [alembic.runtime.migration] Running upgrade -> 0001_initial`

- [ ] **Step 6: 验证迁移结果**

```bash
docker-compose run --rm api python -c "
from app.database import SessionLocal
db = SessionLocal()
tables = db.execute(\"SELECT table_name FROM information_schema.tables WHERE table_schema='public'\").fetchall()
print('表列表:', tables)
"
```

Expected: 显示 news, topics, news_topics, crawl_logs 四张表

- [ ] **Step 7: 提交**

```bash
git add -A
git commit -m "feat: Alembic 数据库迁移 + 首次迁移脚本"
```

---

### Task 5: Pydantic Schema + 统一响应

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/common.py`
- Create: `backend/app/schemas/news.py`

- [ ] **Step 1: 创建 schemas/__init__.py**

```python
from app.schemas.news import NewsItem, NewsListResponse
from app.schemas.common import PaginationParams, ApiResponse

__all__ = ["NewsItem", "NewsListResponse", "PaginationParams", "ApiResponse"]
```

- [ ] **Step 2: 创建 common.py**

```python
from typing import Generic, TypeVar, Optional

from pydantic import BaseModel

T = TypeVar("T")


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = 1
    size: int = 20


class ApiResponse(BaseModel, Generic[T]):
    """统一响应格式"""
    code: int = 200
    message: str = "success"
    data: Optional[T] = None


class PaginatedData(BaseModel, Generic[T]):
    """分页数据包装"""
    items: list[T]
    total: int
    page: int
    size: int


class PaginatedResponse(ApiResponse[PaginatedData[T]], Generic[T]):
    """带分页的统一响应"""
    pass
```

- [ ] **Step 3: 创建 schemas/news.py**

```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NewsItem(BaseModel):
    """新闻响应体"""
    id: int
    title: str
    link: str
    source_name: str
    summary: Optional[str] = None
    pub_time: Optional[datetime] = None
    crawled_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class NewsQueryParams(BaseModel):
    """新闻查询参数"""
    page: int = 1
    size: int = 20
    search: Optional[str] = None
    source: Optional[str] = None
    topic_id: Optional[int] = None
```

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "feat: Pydantic schema + 统一响应格式"
```

---

### Task 6: 新闻列表 API

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/news.py`

- [ ] **Step 1: 创建 api/__init__.py**

```python
# 空文件
```

- [ ] **Step 2: 创建 api/news.py**

```python
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.news import News
from app.schemas.news import NewsItem, NewsQueryParams
from app.schemas.common import PaginatedResponse, PaginatedData

router = APIRouter(prefix="/api/news", tags=["news"])


def _build_search_query(db: Session, params: NewsQueryParams):
    """构建带搜索和过滤的查询"""
    query = db.query(News).filter(News.is_active.is_(True))

    # 关键词搜索（标题 + 来源）
    if params.search:
        keyword = f"%{params.search}%"
        query = query.filter(
            or_(
                News.title.ilike(keyword),
                News.source_name.ilike(keyword),
                News.summary.ilike(keyword),
            )
        )

    # 来源过滤
    if params.source:
        query = query.filter(News.source_name == params.source)

    return query


@router.get("", response_model=PaginatedResponse[NewsItem])
def list_news(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """获取新闻列表（分页、搜索、过滤）"""
    params = NewsQueryParams(page=page, size=size, search=search, source=source)
    query = _build_search_query(db, params)

    total = query.count()
    items = (
        query.order_by(News.pub_time.desc().nullslast())
        .offset((params.page - 1) * params.size)
        .limit(params.size)
        .all()
    )

    return PaginatedResponse[NewsItem](
        data=PaginatedData[NewsItem](
            items=[NewsItem.model_validate(item) for item in items],
            total=total,
            page=params.page,
            size=params.size,
        )
    )
```

- [ ] **Step 3: 注册路由到 main.py**

在 `backend/app/main.py` 中添加：

```python
from app.api.news import router as news_router

# 在 lifespan 之后，app 定义之后添加：
app.include_router(news_router)
```

- [ ] **Step 4: 编写测试**

Create: `backend/tests/test_api_news.py`

```python
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine, SessionLocal
from app.models.news import News


@pytest.fixture(autouse=True)
def setup_db():
    """每个测试前重建表"""
    Base.metadata.create_all(bind=engine)
    yield
    # 清理测试数据
    with SessionLocal() as db:
        db.query(News).delete()
        db.commit()


client = TestClient(app)


def _create_test_news(title: str, source: str = "测试来源", pub_time: str = "2025-01-01"):
    with SessionLocal() as db:
        news = News(
            title=title,
            link=f"https://test.com/{hash(title)}",
            source_name=source,
            pub_time=datetime.fromisoformat(pub_time),
        )
        db.add(news)
        db.commit()
    return news


def test_list_news_empty():
    resp = client.get("/api/news")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    assert data["data"]["total"] == 0
    assert data["data"]["items"] == []


def test_list_news_with_data():
    _create_test_news("测试新闻标题", "虎嗅", "2025-06-01")
    _create_test_news("AI 大模型突破", "极客公园", "2025-06-02")

    resp = client.get("/api/news")
    data = resp.json()
    assert data["data"]["total"] == 2


def test_search_news():
    _create_test_news("低空经济发展趋势", "虎嗅")
    _create_test_news("AI 大模型突破", "极客公园")

    resp = client.get("/api/news?search=低空经济")
    data = resp.json()
    assert data["data"]["total"] == 1
    assert data["data"]["items"][0]["title"] == "低空经济发展趋势"


def test_filter_by_source():
    _create_test_news("新闻1", "虎嗅")
    _create_test_news("新闻2", "极客公园")

    resp = client.get("/api/news?source=虎嗅")
    data = resp.json()
    assert data["data"]["total"] == 1


def test_pagination():
    for i in range(25):
        _create_test_news(f"新闻{i}", "虎嗅", f"2025-01-{min(i+1, 28):02d}")

    resp = client.get("/api/news?page=1&size=20")
    data = resp.json()
    assert len(data["data"]["items"]) == 20
    assert data["data"]["total"] == 25

    resp = client.get("/api/news?page=2&size=20")
    data = resp.json()
    assert len(data["data"]["items"]) == 5
```

- [ ] **Step 5: 运行测试**

```bash
cd D:/Work/ai_websearch/web_aisearch
docker-compose run --rm api pytest tests/test_api_news.py -v
```

Expected: 5 tests passed

- [ ] **Step 6: 提交**

```bash
git add -A
git commit -m "feat: 新闻列表 API + 分页搜索过滤 + 测试"
```

---

### Task 7: 爬虫基类

**Files:**
- Create: `backend/app/crawlers/__init__.py`
- Create: `backend/app/crawlers/base.py`

- [ ] **Step 1: 创建 crawlers/__init__.py**

```python
from app.crawlers.base import BaseCrawler
from app.crawlers.manager import CrawlerManager

__all__ = ["BaseCrawler", "CrawlerManager"]
```

- [ ] **Step 2: 创建 base.py**

```python
import time
from abc import ABC, abstractmethod
from random import uniform
from typing import Optional

from playwright.sync_api import Page, sync_playwright


class BaseCrawler(ABC):
    """爬虫基类，提供通用抓取能力
    子类只需实现 extract() 方法定义解析逻辑。
    """

    name: str = ""
    source_name: str = ""
    base_url: str = ""
    page_timeout: int = 60000
    scroll_times: int = 0

    @abstractmethod
    def extract(self, page: Page) -> list[dict]:
        """提取新闻列表
        子类实现此方法，返回 [{title, link, time, summary}] 格式的列表。
        """
        ...

    def fetch(self) -> list[dict]:
        """通用抓取流程，子类不需要重写"""
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
            time.sleep(uniform(1.0, 2.0))
            page = browser.new_page()
            page.set_extra_http_headers({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            })

            try:
                page.goto(self.base_url, timeout=self.page_timeout)
                self._scroll(page)
                return self.extract(page)
            except Exception as e:
                print(f"[{self.name}] 抓取失败: {e}")
                return []
            finally:
                browser.close()

    def _scroll(self, page: Page):
        """滚动加载（子类可覆盖）"""
        for _ in range(self.scroll_times):
            page.mouse.wheel(0, 300)
            time.sleep(1.2)
```

- [ ] **Step 3: 提交**

```bash
git add -A
git commit -m "feat: 爬虫基类 BaseCrawler"
```

---

### Task 8: 爬虫管理器

**Files:**
- Create: `backend/app/crawlers/manager.py`

- [ ] **Step 1: 创建 manager.py**

```python
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.crawl import CrawlLog
from app.models.news import News
from app.crawlers.base import BaseCrawler


class CrawlerManager:
    """爬虫管理器
    - 串行执行所有注册爬虫（内存限制）
    - 自动去重、写入数据库
    - 记录运行日志
    """

    def __init__(self):
        self._crawlers: list[BaseCrawler] = []

    def register(self, crawler: BaseCrawler):
        """注册一个爬虫"""
        self._crawlers.append(crawler)

    def register_all(self, crawlers: list[BaseCrawler]):
        """批量注册"""
        self._crawlers.extend(crawlers)

    @property
    def crawlers(self) -> list[BaseCrawler]:
        return list(self._crawlers)

    def run_all(self) -> list[dict]:
        """串行执行所有爬虫"""
        results = []
        for crawler in self._crawlers:
            result = self.run_one(crawler.name)
            results.append(result)
        return results

    def run_one(self, name: str) -> dict:
        """执行单个爬虫"""
        crawler = next((c for c in self._crawlers if c.name == name), None)
        if not crawler:
            return {"name": name, "status": "failed", "error": "未找到爬虫"}

        db = SessionLocal()
        log = CrawlLog(
            source_name=crawler.source_name,
            started_at=datetime.now(timezone.utc),
        )
        db.add(log)
        db.commit()

        try:
            print(f"[{crawler.name}] 开始抓取...")
            items = crawler.fetch()
            count = self._save_items(db, items, crawler.source_name)

            log.status = "success"
            log.items_count = count
            log.finished_at = datetime.now(timezone.utc)
            db.commit()

            print(f"[{crawler.name}] 完成，获取 {count} 条")
            return {"name": crawler.name, "status": "success", "count": count}
        except Exception as e:
            log.status = "failed"
            log.error_message = str(e)
            log.finished_at = datetime.now(timezone.utc)
            db.commit()
            print(f"[{crawler.name}] 失败: {e}")
            return {"name": crawler.name, "status": "failed", "error": str(e)}
        finally:
            db.close()

    def _save_items(self, db: Session, items: list[dict], source_name: str) -> int:
        """保存抓取结果到数据库（去重）"""
        count = 0
        for item in items:
            exists = db.query(News).filter(News.link == item["link"]).first()
            if exists:
                continue

            news = News(
                title=item["title"],
                link=item["link"],
                source_name=source_name,
                summary=item.get("summary", ""),
                pub_time=item.get("time"),
            )
            db.add(news)
            count += 1

        db.commit()
        return count
```

- [ ] **Step 2: 提交**

```bash
git add -A
git commit -m "feat: 爬虫管理器 CrawlerManager"
```

---

### Task 9: 迁移极客公园爬虫

**Files:**
- Create: `backend/app/crawlers/sources/__init__.py`
- Create: `backend/app/crawlers/sources/geekpark.py`

- [ ] **Step 1: 创建 sources/__init__.py**

```python
from app.crawlers.sources.geekpark import GeekParkCrawler

__all__ = ["GeekParkCrawler"]
```

- [ ] **Step 2: 创建 geekpark.py**

```python
import json
from datetime import datetime

from playwright.sync_api import Page

from app.crawlers.base import BaseCrawler


class GeekParkCrawler(BaseCrawler):
    """极客公园爬虫"""

    name = "geekpark"
    source_name = "极客公园"
    base_url = "https://www.geekpark.net/column/304"

    def extract(self, page: Page) -> list[dict]:
        initial_state = page.evaluate("""() => {
            return JSON.stringify(window.__INITIAL_STATE__);
        }""")
        data = json.loads(initial_state)
        items = []
        for post in data["column"]["column"]["posts"]:
            items.append({
                "title": post["title"],
                "link": f"https://www.geekpark.net/news/{post['id']}",
                "time": datetime.fromtimestamp(post["published_timestamp"]),
                "summary": post.get("abstract", ""),
            })
        return items
```

- [ ] **Step 3: 提交**

```bash
git add -A
git commit -m "feat: 迁移极客公园爬虫"
```

---

### Task 10: 爬虫触发 API + 日志

**Files:**
- Create: `backend/app/api/crawl.py`

- [ ] **Step 1: 创建 api/crawl.py**

```python
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.crawl import CrawlLog
from app.crawlers import CrawlerManager
from app.crawlers.sources import GeekParkCrawler

router = APIRouter(prefix="/api/crawl", tags=["crawl"])

# 初始化爬虫管理器（全局单例）
crawl_manager = CrawlerManager()
crawl_manager.register(GeekParkCrawler())


@router.post("/trigger")
def trigger_crawl():
    """手动触发全量爬虫"""
    results = crawl_manager.run_all()
    return {
        "code": 200,
        "message": "爬虫执行完成",
        "data": results,
    }


@router.get("/logs")
def get_crawl_logs(
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
):
    """获取爬虫运行日志"""
    total = db.query(CrawlLog).count()
    logs = (
        db.query(CrawlLog)
        .order_by(CrawlLog.started_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": [
                {
                    "id": log.id,
                    "source_name": log.source_name,
                    "started_at": log.started_at.isoformat() if log.started_at else None,
                    "finished_at": log.finished_at.isoformat() if log.finished_at else None,
                    "status": log.status,
                    "items_count": log.items_count,
                    "error_message": log.error_message,
                }
                for log in logs
            ],
            "total": total,
            "page": page,
            "size": size,
        },
    }
```

- [ ] **Step 2: 注册到 main.py**

```python
from app.api.crawl import router as crawl_router

# 在 include_router(news_router) 后添加
app.include_router(crawl_router)
```

- [ ] **Step 3: 提交**

```bash
git add -A
git commit -m "feat: 爬虫触发 API + 日志查询"
```

---

### Task 11: Vue 3 项目初始化

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.js`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/router/index.js`
- Create: `frontend/src/api/index.js`

- [ ] **Step 1: 创建 package.json**

```json
{
  "name": "news-hub-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.5.0",
    "vue-router": "^4.4.0",
    "axios": "^1.7.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.1.0",
    "vite": "^5.4.0"
  }
}
```

- [ ] **Step 2: 创建 vite.config.js**

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 3: 创建 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>资讯聚合平台</title>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.js"></script>
</body>
</html>
```

- [ ] **Step 4: 创建 src/main.js**

```javascript
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './assets/style.css'

const app = createApp(App)
app.use(router)
app.mount('#app')
```

- [ ] **Step 5: 创建 src/App.vue**

```vue
<template>
  <div id="app-root">
    <header class="app-header">
      <div class="container">
        <h1 class="app-title">宁波资规大数据中心 · 资讯聚合</h1>
      </div>
    </header>
    <main class="container">
      <router-view />
    </main>
  </div>
</template>

<script setup>
// 根组件，暂无逻辑
</script>
```

- [ ] **Step 6: 创建 src/router/index.js**

```javascript
import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'

const routes = [
  { path: '/', name: 'home', component: Home },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
```

- [ ] **Step 7: 创建 src/api/index.js**

```javascript
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// 响应拦截器：提取 data 字段
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API 请求失败:', error)
    return Promise.reject(error)
  }
)

export function fetchNews(params = {}) {
  return api.get('/news', { params })
}

export function fetchHealth() {
  return api.get('/health')
}

export default api
```

- [ ] **Step 8: 验证前端编译**

```bash
cd D:/Work/ai_websearch/web_aisearch/frontend
npm install
npm run build
```

Expected: `dist/` 目录生成，无报错

- [ ] **Step 9: 提交**

```bash
git add -A
git commit -m "feat: Vue 3 项目初始化 + Router + Axios"
```

---

### Task 12: 首页渲染 + 组件

**Files:**
- Create: `frontend/src/assets/style.css`
- Create: `frontend/src/components/NewsCard.vue`
- Create: `frontend/src/components/NewsGrid.vue`
- Create: `frontend/src/components/SearchBar.vue`
- Create: `frontend/src/components/TabNav.vue`
- Create: `frontend/src/components/TagFilter.vue`
- Create: `frontend/src/components/Pagination.vue`
- Create: `frontend/src/views/Home.vue`

- [ ] **Step 1: 创建 style.css**

```css
/* === 全局样式 === */
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background-color: #f5f7fa;
  color: #333;
  line-height: 1.6;
}

.container { max-width: 1200px; margin: 0 auto; padding: 0 16px; }

/* === 顶部导航 === */
.app-header {
  background: #1a4b8c;
  color: #fff;
  padding: 16px 0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.app-title { font-size: 1.4rem; font-weight: 700; }

/* === 搜索框 === */
.search-bar {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
  outline: none;
  transition: border-color 0.2s;
}
.search-bar:focus { border-color: #1a4b8c; }

/* === 页签 === */
.tab-nav { display: flex; gap: 4px; margin: 20px 0; border-bottom: 2px solid #e0e0e0; }
.tab-item {
  padding: 10px 20px;
  cursor: pointer;
  border: none;
  background: none;
  font-size: 0.95rem;
  color: #666;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.2s;
}
.tab-item:hover { color: #1a4b8c; }
.tab-item.active { color: #1a4b8c; border-bottom-color: #1a4b8c; font-weight: 600; }
.tab-item.badge-tab::after {
  content: "NEW";
  font-size: 0.6rem;
  background: #e74c3c;
  color: #fff;
  padding: 1px 5px;
  border-radius: 4px;
  margin-left: 4px;
  vertical-align: super;
}

/* === 标签过滤 === */
.tag-filter { display: flex; gap: 8px; margin: 12px 0; flex-wrap: wrap; }
.tag-item {
  padding: 4px 14px;
  border-radius: 16px;
  border: 1px solid #d0d0d0;
  background: #fff;
  cursor: pointer;
  font-size: 0.85rem;
  color: #555;
  transition: all 0.2s;
}
.tag-item:hover { border-color: #1a4b8c; color: #1a4b8c; }
.tag-item.active { background: #1a4b8c; color: #fff; border-color: #1a4b8c; }

/* === 新闻卡片网格 === */
.news-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
@media (max-width: 768px) { .news-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 480px) { .news-grid { grid-template-columns: 1fr; } }

/* === 新闻卡片 === */
.news-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  transition: box-shadow 0.2s;
  display: flex;
  flex-direction: column;
}
.news-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.12); }
.news-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.source-tag {
  background: #e8f0fe;
  color: #1a4b8c;
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 500;
}
.today-badge {
  background: #e74c3c;
  color: #fff;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 0.7rem;
}
.time-text { font-size: 0.8rem; color: #999; margin-left: auto; }
.news-card-title {
  font-size: 1rem;
  font-weight: 500;
  line-height: 1.5;
  flex-grow: 1;
  margin-bottom: 12px;
}
.news-card-title a { color: #333; text-decoration: none; }
.news-card-title a:hover { color: #1a4b8c; }
.news-card-footer { display: flex; justify-content: flex-end; }
.read-link {
  padding: 6px 14px;
  border: 1px solid #1a4b8c;
  border-radius: 6px;
  color: #1a4b8c;
  text-decoration: none;
  font-size: 0.85rem;
  transition: all 0.2s;
}
.read-link:hover { background: #1a4b8c; color: #fff; }

/* === 搜索高亮 === */
.highlight { background: #fff3cd; padding: 0 2px; border-radius: 2px; }

/* === 分页 === */
.pagination { display: flex; justify-content: center; gap: 4px; margin: 32px 0; }
.page-btn {
  padding: 8px 14px;
  border: 1px solid #d0d0d0;
  background: #fff;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  color: #555;
  transition: all 0.2s;
}
.page-btn:hover { border-color: #1a4b8c; color: #1a4b8c; }
.page-btn.active { background: #1a4b8c; color: #fff; border-color: #1a4b8c; }

/* === 加载 & 空状态 === */
.loading, .empty-state { text-align: center; padding: 60px 0; color: #999; }
.spinner {
  border: 3px solid #e0e0e0;
  border-top-color: #1a4b8c;
  border-radius: 50%;
  width: 36px;
  height: 36px;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 12px;
}
@keyframes spin { to { transform: rotate(360deg); } }
```

- [ ] **Step 2: 创建 NewsCard.vue**

```vue
<template>
  <div class="news-card">
    <div class="news-card-header">
      <span class="source-tag">{{ news.source_name }}</span>
      <span v-if="isToday" class="today-badge">今日</span>
      <span class="time-text">{{ formatTime(news.pub_time) }}</span>
    </div>
    <h3 class="news-card-title">
      <a :href="news.link" target="_blank" rel="noopener noreferrer"
         v-html="highlightTitle(news.title)"></a>
    </h3>
    <div class="news-card-footer">
      <a :href="news.link" target="_blank" rel="noopener noreferrer" class="read-link">
        阅读全文
      </a>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  news: { type: Object, required: true },
  keyword: { type: String, default: '' },
})

function formatTime(timeStr) {
  if (!timeStr) return ''
  const d = new Date(timeStr)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${m}-${day} ${h}:${min}`
}

function isToday() {
  if (!props.news.pub_time) return false
  const d = new Date(props.news.pub_time)
  const now = new Date()
  return d.getMonth() === now.getMonth() && d.getDate() === now.getDate()
}

function highlightTitle(title) {
  if (!props.keyword || !title) return title
  const regex = new RegExp(`(${escapeRegExp(props.keyword)})`, 'gi')
  return title.replace(regex, '<span class="highlight">$1</span>')
}

function escapeRegExp(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
</script>
```

- [ ] **Step 3: 创建 NewsGrid.vue**

```vue
<template>
  <div v-if="loading" class="loading">
    <div class="spinner"></div>
    <p>加载中...</p>
  </div>
  <div v-else-if="items.length === 0" class="empty-state">
    <p>暂无相关资讯</p>
  </div>
  <div v-else class="news-grid">
    <NewsCard v-for="item in items" :key="item.id" :news="item" :keyword="keyword" />
  </div>
</template>

<script setup>
import NewsCard from './NewsCard.vue'

defineProps({
  items: { type: Array, default: () => [] },
  keyword: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})
</script>
```

- [ ] **Step 4: 创建 SearchBar.vue**

```vue
<template>
  <input
    type="text"
    class="search-bar"
    :value="modelValue"
    @input="onInput"
    placeholder="搜索资讯标题、来源或内容..."
  />
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({ modelValue: { type: String, default: '' } })
const emit = defineEmits(['update:modelValue'])

let timer = null
function onInput(e) {
  clearTimeout(timer)
  const val = e.target.value
  timer = setTimeout(() => {
    emit('update:modelValue', val)
  }, 300)
}
</script>
```

- [ ] **Step 5: 创建 TabNav.vue**

```vue
<template>
  <nav class="tab-nav">
    <button
      v-for="tab in tabs"
      :key="tab.key"
      :class="['tab-item', { active: modelValue === tab.key }]"
      @click="$emit('update:modelValue', tab.key)"
    >
      {{ tab.label }}
    </button>
  </nav>
</template>

<script setup>
defineProps({
  tabs: { type: Array, required: true },
  modelValue: { type: String, required: true },
})
defineEmits(['update:modelValue'])
</script>
```

- [ ] **Step 6: 创建 TagFilter.vue**

```vue
<template>
  <div class="tag-filter">
    <button
      v-for="tag in tags"
      :key="tag.key"
      :class="['tag-item', { active: modelValue === tag.key }]"
      @click="$emit('update:modelValue', tag.key)"
    >
      {{ tag.label }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  tags: { type: Array, required: true },
  modelValue: { type: String, default: '' },
})
defineEmits(['update:modelValue'])
</script>
```

- [ ] **Step 7: 创建 Pagination.vue**

```vue
<template>
  <div v-if="totalPages > 1" class="pagination">
    <button
      v-for="p in visiblePages"
      :key="p"
      :class="['page-btn', { active: p === modelValue }]"
      @click="$emit('update:modelValue', p)"
    >
      {{ p }}
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Number, default: 1 },
  total: { type: Number, default: 0 },
  size: { type: Number, default: 20 },
})
defineEmits(['update:modelValue'])

const totalPages = computed(() => Math.ceil(props.total / props.size) || 1)
const visiblePages = computed(() => {
  const pages = []
  const start = Math.max(1, props.modelValue - 2)
  const end = Math.min(totalPages.value, props.modelValue + 2)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})
</script>
```

- [ ] **Step 8: 创建 Home.vue**

```vue
<template>
  <div>
    <SearchBar v-model="searchKeyword" />

    <TabNav :tabs="tabs" v-model="currentTab" />

    <TagFilter
      v-if="currentTags.length > 0"
      :tags="currentTags"
      v-model="currentTag"
    />

    <NewsGrid :items="newsItems" :keyword="searchKeyword" :loading="loading" />

    <Pagination
      v-model="currentPage"
      :total="total"
      :size="pageSize"
    />
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { fetchNews } from '../api/index.js'
import SearchBar from '../components/SearchBar.vue'
import TabNav from '../components/TabNav.vue'
import TagFilter from '../components/TagFilter.vue'
import NewsGrid from '../components/NewsGrid.vue'
import Pagination from '../components/Pagination.vue'

const tabs = [
  { key: 'ai', label: '科技前沿资讯' },
  { key: 'industry', label: '资规行业资讯' },
  { key: 'tech', label: '大模型学习资料' },
  { key: 'media', label: '媒体新闻' },
]

const tagMap = {
  ai: [
    { key: '', label: '全部' },
    { key: '智能体', label: '智能体' },
    { key: '大模型', label: '大模型' },
    { key: '图像', label: '图像' },
    { key: '无人机', label: '无人机' },
  ],
  industry: [
    { key: '', label: '全部' },
  ],
  tech: [
    { key: '', label: '全部' },
    { key: 'Clip', label: 'Clip' },
    { key: '图像', label: '图像检测' },
  ],
  media: [
    { key: '', label: '全部' },
    { key: '麻辣GIS', label: '麻辣GIS' },
    { key: 'DoNews', label: 'DoNews' },
    { key: '资源中国', label: '资源中国' },
  ],
}

const currentTab = ref('ai')
const currentTag = ref('')
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = 20
const total = ref(0)
const newsItems = ref([])
const loading = ref(false)

const currentTags = computed(() => tagMap[currentTab.value] || [])

async function loadNews() {
  loading.value = true
  try {
    const search = currentTag.value || searchKeyword.value
    const resp = await fetchNews({
      page: currentPage.value,
      size: pageSize,
      search: search || undefined,
    })
    newsItems.value = resp.data.items
    total.value = resp.data.total
  } catch (e) {
    newsItems.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

watch([currentTab, currentPage], loadNews)

let timer = null
watch(searchKeyword, () => {
  clearTimeout(timer)
  timer = setTimeout(() => {
    currentPage.value = 1
    loadNews()
  }, 400)
})

watch(currentTag, () => {
  currentPage.value = 1
  loadNews()
})

loadNews()
</script>
```

- [ ] **Step 9: 验证前端构建**

```bash
cd D:/Work/ai_websearch/web_aisearch/frontend
npm run build
```

Expected: 无报错，`dist/` 目录生成

- [ ] **Step 10: 提交**

```bash
git add -A
git commit -m "feat: 前端首页 + 新闻卡片 + 搜索/分页组件"
```

---

### Task 13: Dockerfiles + Nginx 配置

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/Dockerfile.crawler`
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`

- [ ] **Step 1: 创建 backend/Dockerfile（API）**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: 创建 backend/Dockerfile.crawler**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装 Chromium 及其依赖（Playwright 需要）
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*

ENV PLAYWRIGHT_CHROMIUM_PATH=/usr/bin/chromium

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 使用 apscheduler 定时触发爬虫
CMD ["python", "-c", "
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from app.crawlers.manager import CrawlerManager
from app.crawlers.sources import GeekParkCrawler

manager = CrawlerManager()
manager.register(GeekParkCrawler())

def crawl_job():
    print(f'[{datetime.now()}] 开始定时爬取...')
    manager.run_all()
    print(f'[{datetime.now()}] 爬取完成')

# 启动时立即执行一次
crawl_job()

# 定时任务：每4小时
scheduler = BackgroundScheduler()
scheduler.add_job(crawl_job, 'interval', hours=4)
scheduler.add_job(crawl_job, 'cron', hour=9, minute=10)
scheduler.start()

print('爬虫调度器已启动')
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    scheduler.shutdown()
"]
```

- [ ] **Step 3: 创建 frontend/nginx.conf**

```nginx
server {
    listen 80;
    server_name _;

    # Vue SPA 静态文件
    root /usr/share/nginx/html;
    index index.html;

    # SPA 路由：所有非 API 请求返回 index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理到后端
    location /api/ {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

- [ ] **Step 4: 创建 frontend/Dockerfile**

```dockerfile
# 构建阶段
FROM node:20-alpine AS build

WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# 运行阶段
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 5: 验证 docker-compose 全量构建**

```bash
cd D:/Work/ai_websearch/web_aisearch
docker-compose build
```

Expected: 4 个镜像全部构建成功

- [ ] **Step 6: 提交**

```bash
git add -A
git commit -m "feat: Dockerfiles + Nginx 配置"
```

---

### Task 14: 集成测试 + 部署验证

- [ ] **Step 1: 全量启动**

```bash
cd D:/Work/ai_websearch/web_aisearch
docker-compose up -d
```

Expected: 4 个容器全部运行

- [ ] **Step 2: 验证健康检查**

```bash
curl http://localhost/api/health
```

Expected: `{"status":"ok","message":"News Hub API is running"}`

- [ ] **Step 3: 验证前端可访问**

打开浏览器访问 http://localhost，预期看到新闻聚合页面。

- [ ] **Step 4: 验证爬虫触发**

```bash
curl -X POST http://localhost/api/crawl/trigger
```

Expected: 返回爬虫执行结果，包含 geekpark 的抓取数量

- [ ] **Step 5: 验证新闻列表**

```bash
curl "http://localhost/api/news?page=1&size=10"
```

Expected: 返回 geekpark 抓取的新闻列表

- [ ] **Step 6: 验证搜索**

```bash
curl "http://localhost/api/news?search=AI"
```

Expected: 返回标题/来源中包含 AI 的新闻

- [ ] **Step 7: 提交**

```bash
git add -A
git commit -m "chore: 集成测试 + 部署验证"
```

---

## Phase 1 完成标志

- [x] Docker Compose 启动后 4 个容器正常运行
- [x] `GET /api/health` 返回正常
- [x] `GET /api/news` 返回极客公园抓取的新闻列表
- [x] 搜索 `?search=xxx` 能正确过滤
- [x] 分页 `?page=1&size=20` 正常工作
- [x] `POST /api/crawl/trigger` 触发爬虫并写入数据库
- [x] 前端 http://localhost 能正常展示新闻
- [x] 前端搜索框能调用后端搜索
- [x] CORS 配置正确，前后端通信正常
