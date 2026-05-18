# 资讯聚合平台 (News Hub)

宁波资规大数据中心内部使用的新闻资讯聚合平台，自动抓取多个网站新闻、汇聚展示，支持分类浏览、关键词搜索和分页过滤。面向 5-20 人小团队，部署在阿里云 ECS（2C2G）。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI 0.115 |
| ORM | SQLAlchemy 2.0 + Alembic |
| 数据库 | PostgreSQL 15 |
| 爬虫引擎 | Playwright（无头 Chromium） |
| 定时任务 | APScheduler |
| 前端 | Vue 3 (Composition API) + Vite 5 |
| 路由 | Vue Router 4 |
| HTTP 客户端 | Axios |
| 反向代理 | Nginx |
| 容器化 | Docker Compose |

## 项目结构

```
web_aisearch/
├── docker-compose.yml          # 4 容器编排
├── .env.example                # 环境变量模板
│
├── backend/                    # Python 后端
│   ├── Dockerfile              # API 镜像
│   ├── Dockerfile.crawler      # 爬虫镜像（含 Chromium）
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/                # 数据库迁移脚本
│   ├── app/
│   │   ├── main.py             # FastAPI 入口
│   │   ├── config.py           # pydantic-settings 配置
│   │   ├── database.py         # SQLAlchemy 连接管理
│   │   ├── models/             # 数据模型（news / topic / crawl_log）
│   │   ├── schemas/            # Pydantic 请求/响应体
│   │   ├── api/                # RESTful 路由（news / crawl）
│   │   └── crawlers/           # 爬虫框架（基类 + 管理器 + 具体爬虫）
│   ├── scripts/init_db.sql     # 数据库初始化
│   └── tests/
│
├── frontend/                   # Vue 3 前端
│   ├── Dockerfile              # 多阶段构建（Node → Nginx）
│   ├── nginx.conf
│   ├── vite.config.js
│   └── src/
│       ├── main.js
│       ├── App.vue
│       ├── router/index.js
│       ├── api/index.js        # Axios 封装
│       ├── views/Home.vue      # 首页
│       ├── components/         # 6 个 UI 组件
│       └── assets/style.css
│
└── docs/                       # 设计文档与实施计划
```

## 快速开始

### 前置条件

- [Docker](https://docs.docker.com/get-docker/) 20.10+
- [Docker Compose](https://docs.docker.com/compose/install/) 2.0+

### Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone <repo-url>
cd web_aisearch

# 2. 复制环境变量
cp .env.example .env

# 3. 启动全部服务
docker-compose up -d

# 4. 查看运行状态
docker-compose ps
```

启动后访问：
- 前端页面：`http://localhost`
- API 文档（Swagger）：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/api/health`

### 本地开发

**后端**（需要 Python 3.11+ 和本地 PostgreSQL）：

```bash
cd backend
pip install -r requirements.txt

# 修改 .env 中 POSTGRES_HOST 为 localhost
uvicorn app.main:app --reload --port 8000
```

**前端**：

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器默认运行在 `http://localhost:5173`，API 请求自动代理到 `localhost:8000`。

## 部署架构

```
                    ┌─────────────┐
           :80 ─────│   nginx     │──── /api/* 反向代理 ────┐
                    └─────────────┘                         │
                                                           ▼
                                                  ┌─────────────────┐
                   :8000 ────────────────────────│   api (FastAPI)  │
                                                  └────────┬────────┘
                                                           │
                                                           ▼
                                                  ┌─────────────────┐
                   :5432 ────────────────────────│   postgres (PG)  │
                                                  └────────┬────────┘
                                                           ▲
                                                  ┌────────┴────────┐
                                                  │  crawler        │
                                                  │ (Playwright +   │
                                                  │  APScheduler)   │
                                                  └─────────────────┘
```

- **nginx**：前端 SPA 静态文件 + 反向代理 `/api/` 到后端
- **api**：FastAPI 服务，提供 RESTful 接口，启动时自动建表
- **postgres**：数据持久化，volume 挂载 `pgdata`
- **crawler**：Playwright 爬虫容器，APScheduler 定时执行（启动执行一次 + 每 4 小时 + 每天 9:10）

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/news` | 新闻列表（支持 `page` / `size` / `search` / `source`） |
| POST | `/api/crawl/trigger` | 手动触发爬虫 |
| GET | `/api/crawl/logs` | 爬取日志（分页） |

响应格式统一为 `{ code, message, data }`，分页数据使用 `{ items, total, page, size }` 包裹。

## 爬虫扩展

在 `backend/app/crawlers/sources/` 下新建文件，继承 `BaseCrawler` 并实现 `extract(page)` 方法，然后在 `manager.py` 中注册即可。

```python
from app.crawlers.base import BaseCrawler

class MyCrawler(BaseCrawler):
    name = "my_source"
    source_name = "我的来源"
    base_url = "https://example.com/news"

    async def extract(self, page):
        # 解析页面，返回 dict 列表
        # 每条数据需包含：title, link, summary, pub_time, source_name
        return items
```

## 数据库迁移

```bash
cd backend

# 生成迁移脚本
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head
```

## 运行测试

```bash
# 后端
docker-compose run --rm api pytest tests/ -v

# 或本地
cd backend && pytest tests/ -v
```

## 二期规划

- [ ] 用户系统（注册 / 登录 / JWT 认证）
- [ ] 主题管理 API + 前端页面
- [ ] "我的订阅"功能
- [ ] 爬虫自动关联主题（关键词匹配）
- [ ] jieba 中文分词搜索
- [ ] 管理后台（爬虫状态监控 / 用户管理）

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| POSTGRES_USER | 数据库用户 | newsuser |
| POSTGRES_PASSWORD | 数据库密码 | changeme123 |
| POSTGRES_DB | 数据库名 | news_hub |
| POSTGRES_HOST | 数据库主机 | postgres |
| POSTGRES_PORT | 数据库端口 | 5432 |
| ENVIRONMENT | 运行环境 | development |
| LOG_LEVEL | 日志级别 | info |
