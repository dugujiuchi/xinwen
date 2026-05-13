# 资讯聚合平台（News Hub）设计文档

## 1. 概述

### 1.1 项目目标

构建一个面向小团队（5-20人）的新闻资讯聚合平台，支持：
- 从多个网站自动抓取新闻并汇聚展示
- 预置分类方向 + 用户自定义主题
- 全文搜索（预留中文分词扩展）
- Docker 容器化部署

### 1.2 背景

现有项目（`web_search/`）采用爬虫→JSON文件→前端直读的架构，存在以下问题：
- 前端直读 JSON，无服务端分页和搜索
- 爬虫代码重复，每个爬虫独立初始化浏览器
- 不支持用户自定义主题
- 部署依赖 Windows 环境，扩展性差

新项目将完全重构为前后端分离架构，使用 Docker 部署在阿里云。

---

## 2. 部署架构

### 2.1 服务器配置

- **规格**: 2C2G 40GB 磁盘，3Mbps 带宽
- **系统**: Ubuntu（阿里云 ECS）
- **容器**: Docker Compose

### 2.2 容器编排

```
阿里云 Ubuntu
┌─────────────────────────────────────────────┐
│  docker-compose.yml                          │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Nginx     │  │ FastAPI  │  │ Crawler    │  │
│  │ (Vue SPA) │◀─┤ (API)    │  │ (定时任务) │  │
│  │ :80       │  │ :8000    │  │            │  │
│  └──────────┘  └────┬─────┘  └────────────┘  │
│                     │                         │
│              ┌──────▼──────┐                  │
│              │ PostgreSQL  │                  │
│              │ (容器自建)   │                  │
│              └─────────────┘                  │
└─────────────────────────────────────────────┘
```

容器说明：

| 服务 | 镜像 | 说明 |
|------|------|------|
| `nginx` | nginx:alpine | Vue SPA 静态文件 + 反向代理到 API |
| `api` | python:3.11-slim | FastAPI 应用，Gunicorn + Uvicorn |
| `crawler` | python:3.11-slim | 爬虫 Worker，定时执行 |
| `postgres` | postgres:15-alpine | 数据库 |

### 2.4 Crawler 容器说明

爬虫容器因使用 Playwright 需要额外处理：

```dockerfile
# backend/Dockerfile.crawler
FROM python:3.11-slim

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
```

**调度方式**：在 Crawler 容器内使用 `apscheduler` 定时任务触发串行执行，也可通过 API 手动触发。

```
crawler 容器启动时:
  1. 注册定时任务（每4小时 + 每天9:10，沿用现有节奏）
  2. 启动时立即执行一次全量抓取
  3. 串行调用所有注册爬虫，每次只启动一个浏览器实例
```

### 2.3 资源约束说明（原）

2GB 内存限制下的注意事项：
- 爬虫使用 Playwright 需要启动 Chromium，峰值内存约 300-500MB
- 爬虫必须**串行执行**，一次只跑一个爬虫实例
- PG + API + Nginx 基线占用约 600-800MB
- 建议爬虫集中在凌晨/低峰时段运行

---

## 3. 数据库设计

### 3.1 表结构

```sql
-- 新闻主表
CREATE TABLE news (
    id              SERIAL PRIMARY KEY,
    title           TEXT NOT NULL,
    link            TEXT NOT NULL UNIQUE,
    source_name     VARCHAR(100) NOT NULL,     -- 来源名称
    source_type     VARCHAR(20) DEFAULT 'crawler',  -- crawler / user_submitted
    summary         TEXT,                      -- 摘要
    pub_time        TIMESTAMP,                 -- 原始发布时间
    crawled_at      TIMESTAMP DEFAULT NOW(),   -- 抓取时间
    is_active       BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_news_pub_time ON news (pub_time DESC);
CREATE INDEX idx_news_source ON news (source_name);

-- 主题/方向表（预置 + 自定义统一存储）
CREATE TABLE topics (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL UNIQUE,
    type            VARCHAR(20) DEFAULT 'preset',  -- preset | custom
    description     TEXT,                      -- 主题描述
    keywords        TEXT[],                    -- 关联搜索关键词数组
    created_by      INTEGER REFERENCES users(id),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 新闻-主题关联（多对多）
CREATE TABLE news_topics (
    news_id         INTEGER REFERENCES news(id) ON DELETE CASCADE,
    topic_id        INTEGER REFERENCES topics(id) ON DELETE CASCADE,
    relevance       REAL DEFAULT 1.0,          -- 相关度评分（预留）
    PRIMARY KEY (news_id, topic_id)
);

CREATE INDEX idx_news_topics_topic ON news_topics (topic_id);

-- 用户表
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(50) UNIQUE NOT NULL,
    display_name    VARCHAR(100),
    password_hash   VARCHAR(255) NOT NULL,
    is_admin        BOOLEAN DEFAULT FALSE,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 用户订阅的主题
CREATE TABLE user_subscriptions (
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    topic_id        INTEGER REFERENCES topics(id) ON DELETE CASCADE,
    subscribed_at   TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, topic_id)
);

-- 爬虫运行日志
CREATE TABLE crawl_logs (
    id              SERIAL PRIMARY KEY,
    source_name     VARCHAR(100) NOT NULL,
    started_at      TIMESTAMP NOT NULL,
    finished_at     TIMESTAMP,
    status          VARCHAR(20) DEFAULT 'running',  -- running / success / failed
    items_count     INTEGER DEFAULT 0,
    error_message   TEXT
);
```

### 3.2 主题与新闻的关联机制

预置方向和用户自定义主题通过**关键词匹配**自动关联新闻：

```
用户新建主题"低空经济"，设置关键词 = ["低空经济", "无人机", "eVTOL", "空域管理"]
    ↓
爬虫抓取新闻时：
  每篇新闻的 title + summary 遍历所有活跃主题的关键词
  匹配任一关键词 → 插入 news_topics 关联记录

用户创建新主题时：
  立即扫描已有新闻的 title + summary 做回填匹配
```

这种方式实现简单，无需 NLP 模型。未来可升级为向量相似度匹配。

### 3.3 搜索设计

**当前阶段**（V1）:
- 使用 PostgreSQL `ILIKE` 进行标题和来源的模糊匹配
- 基础 SQL: `WHERE title ILIKE '%keyword%' OR summary ILIKE '%keyword%'`
- 分页 + 排序使用 `LIMIT/OFFSET` + `ORDER BY pub_time DESC`

**未来扩展**（V2，中文分词）:
- 新增 `tsvector` 列存储分词结果
- 使用 Python `jieba` 分词库
- 搜索时通过 jieba 分词后使用 `@@ to_tsquery()` 匹配
- 全量搜索无需 LIKE 遍历

---

## 4. API 设计

### 4.1 RESTful API

```
GET  /api/news                    # 新闻列表（分页、搜索、过滤）
      ?page=1&size=20
      &search=关键词
      &source=虎嗅
      &topic_id=1
      &sort=pub_time_desc

GET  /api/news/:id                # 新闻详情

GET  /api/topics                  # 主题列表
      ?type=preset|custom
      &user_id=1

POST /api/topics                  # 创建自定义主题
      { name, keywords, description }

POST /api/crawl/trigger           # 手动触发爬虫

GET  /api/crawl/logs              # 爬虫运行日志

POST /api/auth/login              # 登录
POST /api/auth/logout             # 登出

GET  /api/users/me                # 当前用户信息
      /subscriptions              # 订阅列表
POST /api/users/me/subscriptions  # 添加订阅
      { topic_id }

GET  /api/admin/crawlers          # 管理：爬虫状态
GET  /api/admin/stats             # 管理：统计信息
```

### 4.2 统一响应格式

```json
{
    "code": 200,
    "message": "success",
    "data": { ... },
    "pagination": {
        "page": 1,
        "size": 20,
        "total": 150
    }
}
```

---

## 5. 爬虫框架设计

### 5.1 统一基类

```python
class BaseCrawler(ABC):
    """爬虫基类，提供通用能力"""

    name: str              # 爬虫名称（用于日志和识别）
    source_name: str       # 来源名称（存入数据库）
    base_url: str

    @abstractmethod
    def extract(self, page) -> list[dict]:
        """提取新闻列表，返回 [{title, link, time, summary}]"""
        pass

    def fetch(self) -> list[dict]:
        """通用抓取流程（初始化浏览器 → 访问 → 提取 → 清理）"""
        # Playwright 初始化（子类不用重复写）
        # 调用 self.extract(page)
        # 关闭浏览器
        pass
```

### 5.2 爬虫管理器

```python
class CrawlerManager:
    """
    管理所有注册的爬虫。
    - 串行执行所有爬虫（内存限制）
    - 自动去重、写入数据库
    - 记录运行日志
    """
    def run_all(self): ...
    def run_one(self, name: str): ...
```

### 5.3 预置爬虫列表（第一期迁移）

| 模块 | 来源 | 现有代码位置 |
|------|------|-------------|
| `geekpark` | 极客公园 | `python/geekpark.py` |
| `huxiu` | 虎嗅科技 | `python/huxiu.py` |
| `modelscope` | 魔塔社区 | `python/modelScope.py` |
| `drone` | 无人机资讯 | `python/DroneNews.py` |
| `yaogan` | 遥感测绘 | `python/yaogan.py` |
| `techwalker` | 科技行者 | `python/techWalker.py` |
| `aigc_hot` | AIGC热点 | `python/ai_new_search.py` fetch_dynamic_aigc |
| `malagis` | 麻辣GIS | `python/other_new.py` |
| `chinahightech` | 中国高新技术产业导报 | `python/other_new.py` |
| `zhiding` | 至顶网 | `python/other_new.py` |
| `donews` | DoNews | `python/other_new.py` |
| `iziran` | 资源中国 | `python/other_new.py` |
| `tmtpost` | 数智前线 | `python/other_new.py` |
| `csdn` | CSDN | `python/technology_new.py` |
| `jiqizhixin` | 机器之心 | `python/technology_new.py` |

---

## 6. 前端设计

### 6.1 技术选型

- **框架**: Vue 3 (Composition API)
- **构建**: Vite
- **HTTP**: Axios
- **路由**: Vue Router 4
- **CSS**: 手写 SCSS（保持轻量，不引入 UI 组件库）

### 6.2 页面结构

```
首页（聚合展示）
├── 顶部导航栏
│   ├── Logo + 标题
│   └── 全局搜索框
├── 页签导航（一级分类）
│   ├── 科技前沿资讯（预设）
│   ├── 资规行业资讯（预设）
│   ├── 大模型学习资料（预设）
│   ├── 媒体新闻（预设）
│   └── + 我的订阅（自定义主题）
├── 分类标签（二级过滤，每个页签不同）
│   ├── 全部 | 智能体 | 大模型 | 图像 | ...
├── 新闻卡片网格（3列）
│   └── 每张卡片：来源标签 | 标题（含搜索高亮） | 时间 | 阅读链接
├── 分页
└── 底部

管理后台
├── 主题管理（新增/编辑预置方向）
├── 爬虫状态（最近运行记录）
└── 用户管理（管理员）
```

### 6.3 配色方案

- **主色**: `#1a4b8c`（深蓝 — 稳重专业）
- **浅色背景**: `#f5f7fa`（页面背景）
- **卡片**: `#ffffff`（白色卡片，浅阴影）
- **来源标签**: `#e8f0fe` 蓝底 + `#1a4b8c` 文字

### 6.4 组件树

```
App.vue
├── AppHeader.vue            # 顶栏：标题 + 用户信息
├── SearchBar.vue            # 搜索框（带防抖）
├── TabNav.vue               # 一级分类页签
├── TagFilter.vue            # 二级标签过滤
├── NewsGrid.vue             # 新闻卡片网格
│   └── NewsCard.vue         # 单张卡片
├── Pagination.vue           # 分页
├── TopicPanel.vue           # "我的订阅"面板
└── AdminPanel.vue           # 管理面板
```

---

## 7. 目录结构

```
D:\Work\ai_websearch\web_aisearch\
├── docker-compose.yml          # 容器编排
├── .env.example                # 环境变量模板
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/                # 数据库迁移
│   │   └── versions/
│   ├── app/
│   │   ├── main.py             # FastAPI 入口
│   │   ├── config.py           # 配置类（pydantic-settings）
│   │   ├── database.py         # 数据库连接
│   │   ├── models/             # SQLAlchemy 模型
│   │   │   ├── news.py
│   │   │   ├── topic.py
│   │   │   └── user.py
│   │   ├── schemas/            # Pydantic 请求/响应体
│   │   │   ├── news.py
│   │   │   ├── topic.py
│   │   │   └── user.py
│   │   ├── api/                # 路由
│   │   │   ├── __init__.py
│   │   │   ├── news.py
│   │   │   ├── topics.py
│   │   │   ├── crawl.py
│   │   │   ├── users.py
│   │   │   └── admin.py
│   │   └── crawlers/           # 爬虫框架
│   │       ├── __init__.py
│   │       ├── base.py         # BaseCrawler 基类
│   │       ├── manager.py      # CrawlerManager
│   │       └── sources/        # 各站点爬虫
│   │           ├── __init__.py
│   │           ├── geekpark.py
│   │           ├── huxiu.py
│   │           ├── drone.py
│   │           └── ... (逐期迁移)
│   └── scripts/
│       └── init_db.sql         # 数据库初始化脚本
│
├── frontend/
│   ├── Dockerfile              # 构建后放入 nginx
│   ├── nginx.conf              # nginx 配置
│   ├── vite.config.js
│   ├── index.html
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── router/index.js
│   │   ├── api/index.js        # axios 封装
│   │   ├── views/
│   │   │   ├── Home.vue
│   │   │   ├── Login.vue
│   │   │   └── Admin.vue
│   │   ├── components/
│   │   │   ├── NewsCard.vue
│   │   │   ├── NewsGrid.vue
│   │   │   ├── SearchBar.vue
│   │   │   ├── TabNav.vue
│   │   │   ├── TagFilter.vue
│   │   │   └── Pagination.vue
│   │   └── assets/
│   │       └── style.css
│   └── package.json
│
├── docs/
│   ├── specs/
│   │   └── 2026-05-13-news-hub-design.md
│   └── api.md
│
└── README.md
```

---

## 8. 实施路线图

### 第一期：基础框架 + 爬虫迁移

| 步骤 | 内容 | 预估 |
|------|------|------|
| 1 | 项目初始化：Docker Compose + FastAPI + PG 连通 | 1天 |
| 2 | 数据库模型 + Alembic 迁移 | 1天 |
| 3 | 爬虫基类 + 迁移 2-3 个关键爬虫 | 2天 |
| 4 | API 基础接口（新闻列表、搜索、分页） | 1天 |
| 5 | Vue 项目初始化 + 首页开发 | 2天 |
| 6 | 部署到阿里云测试 | 1天 |
| **总计** | | **8天** |

### 第二期：用户 + 主题系统

| 步骤 | 内容 | 预估 |
|------|------|------|
| 1 | 用户注册/登录 | 1天 |
| 2 | 预置+自定义主题管理 API | 1天 |
| 3 | 前端主题管理页 + 我的订阅 | 1天 |
| 4 | 爬虫关联主题逻辑 | 1天 |
| **总计** | | **4天** |

### 第三期：优化（可选）

| 步骤 | 内容 |
|------|------|
| 1 | jieba 中文分词搜索 |
| 2 | 爬虫运行状态监控面板 |
| 3 | 新闻去重强化（相似标题合并） |
| 4 | 管理员新闻审核 |

---

## 9. 技术决策理由

| 决策 | 选型 | 理由 |
|------|------|------|
| API 框架 | FastAPI | 性能好、自动生成 OpenAPI 文档、异步支持 |
| ORM | SQLAlchemy 2.0 | 成熟稳定、迁移工具完善 |
| 前端框架 | Vue 3 + Vite | 轻量、构建快、学习曲线平缓 |
| UI 组件库 | 无（手写 CSS） | 项目简单，不需要引入 Element Plus 等重库 |
| Web 服务器 | Nginx | 轻量、高性能静态文件服务、反向代理 |
| 爬虫 | Playwright | 现有代码已使用，适配 JS 渲染站点 |
| 数据库迁移 | Alembic | 与 SQLAlchemy 原生集成 |
| 配置管理 | pydantic-settings | FastAPI 生态，环境变量驱动 |

---

## 10. 安全性考虑

- 密码使用 bcrypt 哈希存储
- API 使用 JWT 认证（预留，第一期可不开启鉴权）
- 环境变量管理敏感配置（数据库密码、密钥）
- 容器间使用内部网络通信，不暴露数据库端口到公网
- 爬虫遵守 robots.txt（预留检测）
- 请求频率限制（预留）
