# 资讯聚合平台 (News Hub)

宁波资规大数据中心内部使用的资讯聚合平台，自动抓取多站点新闻、分类展示，支持栏目筛选、标签过滤和关键词搜索。面向 5-20 人小团队，部署在阿里云 ECS（2C2G）。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI 0.115 |
| ORM | SQLAlchemy 2.0 + Alembic |
| 数据库 | PostgreSQL 16 |
| 浏览器抓取 | Playwright（无头 Chromium） |
| 定时调度 | APScheduler（每 4 小时） |
| 前端 | Vue 3 (Composition API) + Vite 5 |
| 路由 | Vue Router 4 |
| HTTP 客户端 | Axios |
| 反向代理 | Nginx |
| 容器化 | Docker Compose（4 个服务） |

## 项目结构

```
web_aisearch/
├── docker-compose.yml              # 4 个服务编排
├── .env.example                    # 环境变量模板
├── README.md
├── ROADMAP.md                      # 长期规划
│
├── backend/                        # Python 后端
│   ├── Dockerfile                  # API 镜像
│   ├── Dockerfile.crawler          # 爬虫镜像（含 Chromium，约 1GB）
│   ├── requirements.txt
│   ├── run.py                      # 入口脚本
│   ├── alembic.ini
│   ├── alembic/                    # 数据库迁移脚本
│   ├── app/
│   │   ├── main.py                 # FastAPI 应用入口（路由注册 + lifespan）
│   │   ├── config.py               # pydantic-settings 配置（环境变量驱动）
│   │   ├── database.py             # SQLAlchemy 连接管理
│   │   ├── crawler_scheduler.py    # APScheduler 定时调度
│   │   ├── models/                 # 数据模型：News / Source / Topic / CrawlLog
│   │   ├── schemas/                # Pydantic 请求/响应 schema
│   │   ├── api/                    # 路由：news（公开）/ admin（管理端）/ auth（鉴权）
│   │   └── crawlers/               # 抓取引擎：工厂 + 管理器 + 3 种抓取器
│   ├── scripts/
│   │   ├── init_db.sql             # 数据库初始化
│   │   └── seed_sources.py         # 种子数据源（23 个预置源）
│   └── tests/
│
├── frontend/                       # Vue 3 前端
│   ├── Dockerfile                  # 多阶段构建（Node 构建 + Nginx 运行）
│   ├── nginx.conf                  # SPA 路由 + /api/ 反向代理
│   ├── vite.config.js
│   └── src/
│       ├── main.js
│       ├── App.vue
│       ├── router/index.js         # 路由：首页 / + 管理端 /admin/*
│       ├── api/index.js            # Axios 封装 + API 函数
│       ├── views/                  # 页面：Home / AdminLayout / SourceList / SourceForm / CrawlLogs
│       ├── components/             # 6 个 UI 组件（SearchBar / TabNav / TagFilter / NewsGrid / NewsCard / Pagination）
│       └── assets/style.css        # 全局样式（含移动端适配）
│
└── docs/                           # 设计文档与实施计划
```

## 快速开始

### 前提条件

- [Docker](https://docs.docker.com/get-docker/) 20.10+
- [Docker Compose](https://docs.docker.com/compose/install/) 2.0+

### Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/dugujiuchi/xinwen.git web_aisearch
cd web_aisearch

# 2. 复制环境变量（可选，不创建则使用默认值）
cp .env.example .env

# 3. 启动全部服务
docker compose up -d

# 4. 查看服务状态
docker compose ps
```

启动后访问：
- 前端首页：`http://localhost`
- 管理后台：`http://localhost/admin`（密码见 `.env` 中 `ADMIN_PASSWORD`，默认 `admin123`）
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

## 架构

```
                     ┌──────────────────┐
            :80 ────▶│      nginx       │──── /api/* 代理 ────▶
                     └──────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ 静态文件     │  │  api:8000    │  │  crawler     │
    │ (SPA)       │  │  (FastAPI)   │  │  (Playwright │
    │             │  │              │  │   + Scheduler)│
    └──────────────┘  └──────┬───────┘  └──────┬───────┘
                             │                 │
                             ▼                 ▼
                     ┌──────────────────────────────┐
                     │      postgres:5432 (PG16)     │
                     │      数据持久化 (volume)      │
                     └──────────────────────────────┘
```

- **nginx**：前端 SPA 静态文件 + `/api/` 反向代理到 FastAPI
- **api**：RESTful 接口 + 管理端 API + 应用启动时自动建表与种子数据填充
- **crawler**：Playwright 浏览器抓取 + APScheduler 定时调度（每 4 小时 + 启动时执行一次）
- **postgres**：数据持久化，volume 挂载 `pgdata`

## 核心功能

### 新闻浏览（首页）

- **动态栏目**：栏目和数据源从后端 `/api/categories` 动态获取，不再硬编码
- **标签筛选**：点击标签过滤当前栏目下的新闻
- **关键词搜索**：支持 400ms 防抖搜索
- **分页浏览**：每页 20 条
- **移动端适配**：断点 640px / 480px，Tab 横向滚动、卡片紧凑排列

### 管理后台（`/admin`）

- **鉴权**：通过 `.env` 中 `ADMIN_ENABLED` 开关，`ADMIN_PASSWORD` 简易密码鉴权（Header `X-Admin-Key`）
- **数据源管理**：新增/编辑/删除数据源，支持 JSON 配置编辑器 + 模板参考面板
- **测试抓取**：对单个数据源执行测试抓取，预览前 10 条结果，不写入数据库
- **爬取日志**：查看历史抓取记录（状态/条目数/耗时/错误信息）
- **触发全量抓取**：手动触发对所有活跃源的抓取

### 抓取引擎

三套通用抓取器，通过数据源 `config` JSON 配置驱动，无需为每个站点写代码：

| 抓取类型 | crawl_type | 适用场景 | 依赖 |
|----------|-----------|---------|------|
| API 抓取 | `api` | 有 JSON 接口的站点 | httpx |
| 选择器抓取 | `selector` | 传统 HTML 页面，CSS 选择器提取 | httpx + BeautifulSoup4 + lxml |
| 浏览器抓取 | `browser` | JS 动态渲染页面 | Playwright |

每种类型支持可选的深度抓取（`fetch_content`），开启后自动进入详情页提取正文。

去重说明：入库前会对 `link` 做归一化（自动剥离 `request_id`、`utm_*` 等每次请求都变化的追踪参数，保留 `?aid=123` 这类功能性参数），再按 `link` 唯一约束去重。历史数据可用 `python -m scripts.clean_duplicate_news` 一键清理（删除重复行并归一化存量 link）。Browser 类型还支持 `wait_ms` 配置，用于等待 SPA 渐进渲染完成后再提取。

## API 接口

### 公开接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/news` | 新闻列表，支持 `page`/`size`/`search`/`category`/`tags` |
| GET | `/api/categories` | 返回所有栏目及每个栏目下的数据源列表 |
| GET | `/api/tags` | 返回标签列表，可按 `category` 筛选 |

### 管理端接口（需 `X-Admin-Key` 请求头）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admin/sources` | 数据源列表（分页 + 搜索） |
| POST | `/api/admin/sources` | 新增数据源 |
| PUT | `/api/admin/sources/{id}` | 编辑数据源 |
| DELETE | `/api/admin/sources/{id}` | 删除数据源 |
| POST | `/api/admin/sources/{id}/test` | 测试抓取（预览前 10 条） |
| POST | `/api/admin/sources/{id}/crawl` | 对单个源执行正式抓取并入库 |
| POST | `/api/admin/crawl/trigger` | 触发全量爬取 |
| GET | `/api/admin/crawl/logs` | 爬取日志（分页） |
| POST | `/api/admin/sources/test-config` | 未保存配置的测试抓取 |

响应格式统一为 `{ code, message, data }`，分页接口使用 `{ items, total, page, size }` 结构。

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
| ADMIN_ENABLED | 是否启用管理端鉴权 | true |
| ADMIN_PASSWORD | 管理端密码 | admin123 |
| TZ | 时区 | Asia/Shanghai |

## 服务器部署与更新

### 首次部署

```bash
# SSH 到服务器
git clone https://github.com/dugujiuchi/xinwen.git /opt/xinwen/web_aisearch
cd /opt/xinwen/web_aisearch

# 根据需要创建 .env 自定义配置
cp .env.example .env
vi .env

# 启动
docker compose up -d
```

注意：阿里云安全组需开放端口 80（前端）和 5433（数据库远程访问）。

### 更新代码

```bash
cd /opt/xinwen/web_aisearch
git pull
docker compose up -d --build
```

### 远程数据库访问

服务端 PostgreSQL 端口映射为 `5433:5432`。Navicat 等客户端连接参数：

| 参数 | 值 |
|------|-----|
| Host | 服务器 IP |
| Port | 5433 |
| User | 见服务器 `.env` 或默认 `newsuser` |
| Password | 见服务器 `.env` 或默认 `changeme123` |
| Database | news_hub |

## 爬虫扩展

不再需要编写爬虫类。在管理后台 `/admin/sources/new` 中新增数据源，根据目标站点选择对应的 `crawl_type` 并填写 JSON 配置即可。配置模板参考见管理端表单页右侧面板。

### 配置示例

**API 类型**（如极客公园、魔搭社区）：
```json
{
  "url": "https://api.example.com/articles",
  "method": "GET",
  "response_type": "json",
  "item_path": "data.list",
  "fetch_content": true,
  "mapping": {
    "title": "title",
    "link": "url",
    "time": "publishTime",
    "summary": "abstract",
    "content": "content",
    "tags": "tagList"
  }
}
```

**Selector 类型**（如自然资源部、CSDN）：
```json
{
  "url": "https://example.com/news",
  "encoding": "utf-8",
  "list_selector": ".news-list li",
  "fetch_content": false,
  "mapping": {
    "title": { "selector": "h3 a", "attr": "text" },
    "link": { "selector": "h3 a", "attr": "href" },
    "time": { "selector": "span.date", "attr": "text" },
    "summary": { "selector": "p.desc", "attr": "text" }
  }
}
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
# 容器内
docker compose run --rm api pytest tests/ -v

# 本地
cd backend && pytest tests/ -v
```
