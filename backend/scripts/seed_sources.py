"""
数据源种子数据填充脚本。

Usage:
    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    from scripts.seed_sources import seed_sources

    db = SessionLocal()
    seed_sources(db)
    db.close()
"""

from sqlalchemy.orm import Session

from app.models.source import Source


def seed_sources(db: Session, override: bool = False) -> None:
    """向 sources 表写入 23 个预置数据源。

    - 首次启动（表为空）：插入全部 23 个源
    - override=True：更新已有源的 crawl_type/config（保留用户修改的 display_name/category/is_active/sort_order），新增不存在的源
    - override=False 且表非空：跳过
    """
    table_count = db.query(Source).count()

    if not override and table_count > 0:
        print("[seed_sources] sources 表已有数据，跳过种子填充")
        return

    sources: list[dict] = _build_sources()
    updated = 0
    added = 0
    for item in sources:
        existing = db.query(Source).filter(Source.name == item["name"]).first()
        if existing:
            if override:
                # 只更新抓取逻辑相关字段，保留用户自己改的 display_name/category/is_active/sort_order
                existing.crawl_type = item["crawl_type"]
                existing.config = item["config"]
                updated += 1
        else:
            db.add(Source(**item))
            added += 1
    db.commit()
    print(f"[seed_sources] 新增 {added} 个，更新配置 {updated} 个数据源")


def _build_sources() -> list[dict]:
    """构造 23 个数据源的 dict 列表。

    mapping 选择器规则（重要）：
    - Browser/Selector 类的 list_selector 定位到每条新闻的容器元素
    - mapping 中的 selector 是**相对于容器元素**的选择器
    - 这与 Playwright 的 item.query_selector("a") 语义一致
    """
    return [
        # ============================================================
        # ai (科技前沿资讯) — 8 个源
        # ============================================================
        {
            "name": "geekpark",
            "display_name": "极客公园",
            "category": "ai",
            "crawl_type": "browser",
            "sort_order": 1,
            "config": {
                "url": "https://www.geekpark.net/column/304",
                "extract_mode": "js_state",
                "state_key": "__INITIAL_STATE__",
                "state_path": "column.column.posts",
                "mapping": {
                    "title": "title",
                    "link": "https://www.geekpark.net/news/{id}",
                    "time": "published_timestamp",
                    "time_type": "timestamp",
                    "summary": "abstract",
                },
                "fetch_content": False,
            },
        },
        {
            "name": "huxiu_tech",
            "display_name": "虎嗅科技",
            "category": "ai",
            "crawl_type": "browser",
            "sort_order": 2,
            "config": {
                "url": "https://www.huxiu.com/channel/105.html",
                "scroll_times": 3,
                "wait_selector": "div.article-item-wrap",
                "list_selector": "div.article-item-wrap",
                "mapping": {
                    "title": {"selector": ".channel-title", "attr": "text"},
                    "link": {"selector": "a", "attr": "href"},
                    "time": {"selector": ".bottom-line__time", "attr": "text"},
                },
                "fetch_content": False,
            },
        },
        {
            "name": "modelscope_community",
            "display_name": "魔搭社区",
            "category": "ai",
            "crawl_type": "browser",
            "sort_order": 3,
            "config": {
                "url": "https://community.modelscope.cn/",
                "scroll_times": 2,
                "wait_selector": ".page-main-rspan",
                "list_selector": ".page-main-rspan li",
                "mapping": {
                    "title": {"selector": ".blogmain-item-introduce a", "attr": "text"},
                    "link": {"selector": ".blogmain-item-introduce a", "attr": "href"},
                    "time": {"selector": ".author-panel-org-name", "attr": "text"},
                },
                "fetch_content": False,
            },
        },
        {
            "name": "techwalker",
            "display_name": "科技行者",
            "category": "ai",
            "crawl_type": "browser",
            "sort_order": 4,
            "config": {
                "url": "https://www.techwalker.com/list-0-0-327861-1-1.htm",
                "wait_selector": ".clbLeft .article_list ul",
                "list_selector": "li[data-v-513187da]",
                "mapping": {
                    "title": {"selector": ".des h2[data-v-513187da] a", "attr": "title"},
                    "link": {"selector": ".des h2[data-v-513187da] a", "attr": "href"},
                    "time": {"selector": ".time span[data-v-513187da]", "attr": "text"},
                },
                "fetch_content": False,
            },
        },
        {
            "name": "aigc_hot",
            "display_name": "AIGC热点",
            "category": "ai",
            "crawl_type": "browser",
            "sort_order": 5,
            "config": {
                "url": "https://www.aigc.cn/hotnews/",
                "scroll_times": 3,
                "wait_selector": "div.overflow-auto.hot-body",
                "list_selector": "div.card.hot-card",
                "mapping": {
                    "title": {"selector": ".d-flex a", "attr": "text"},
                    "link": {"selector": ".d-flex a", "attr": "href"},
                    "time": {"selector": ".ml-auto", "attr": "text"},
                },
                "fetch_content": False,
            },
        },

        {
            "name": "csgpc_remote",
            "display_name": "遥感测绘",
            "category": "ai",
            "crawl_type": "browser",
            "sort_order": 15,
            "config": {
                "url": "https://www.csgpc.org/list/113.html",
                "scroll_times": 3,
                "list_selector": ".ListArticBox ul",
                "mapping": {
                    "title": {"selector": ".title a", "attr": "text"},
                    "link": {"selector": ".title a", "attr": "href"},
                    "time": {"selector": ".moreinfo dd", "attr": "text"},
                },
                "fetch_content": False,
            },
        },
        {
            "name": "cnaiplus_drone",
            "display_name": "无人机资讯",
            "category": "ai",
            "crawl_type": "browser",
            "sort_order": 17,
            "config": {
                "url": "https://www.cnaiplus.com/a/drone/",
                "scroll_times": 3,
                "list_selector": ".news-list li",
                "mapping": {
                    "title": {"selector": ".n-text a", "attr": "title"},
                    "link": {"selector": ".n-text a", "attr": "href"},
                    "time": {"selector": ".time", "attr": "text"},
                },
                "fetch_content": False,
            },
        },
        # ============================================================
        # industry (资规行业资讯) — 9 个源
        # ============================================================
        {
            "name": "mnr_ywbb",
            "display_name": "自然资源部",
            "category": "industry",
            "crawl_type": "browser",
            "sort_order": 10,
            "config": {
                "url": "https://www.mnr.gov.cn/dt/ywbb/",
                "wait_selector": ".kyy_textR",
                "list_selector": ".ky_open_list li",
                "mapping": {
                    "title": {"selector": "a", "attr": "text"},
                    "link": {"selector": "a", "attr": "href"},
                    "time": {"selector": "span", "attr": "text"},
                },
                "fetch_content": False,
            },
        },
        {
            "name": "zj_zrzyting",
            "display_name": "浙江省自然资源厅",
            "category": "industry",
            "crawl_type": "browser",
            "sort_order": 11,
            "config": {
                "url": "https://zrzyt.zj.gov.cn/col/col1289955/index.html",
                "wait_selector": ".page-content",
                "list_selector": ".cf",
                "mapping": {
                    "title": {"selector": "a.fl", "attr": "text"},
                    "link": {"selector": "a.fl", "attr": "href"},
                    "time": {"selector": "span.fr", "attr": "text"},
                },
                "fetch_content": False,
            },
        },
        {
            "name": "ningbo_zgj",
            "display_name": "宁波市自然资源和规划局",
            "category": "industry",
            "crawl_type": "selector",
            "sort_order": 12,
            "config": {
                "url": "https://zgj.ningbo.gov.cn/col/col1229036864/index.html",
                "encoding": "utf-8",
                "list_selector": ".zwgk li",
                "fetch_content": False,
                "mapping": {
                    "title": {"selector": "a", "attr": "text"},
                    "link": {"selector": "a", "attr": "href"},
                    "time": {"selector": "span", "attr": "text"},
                },
            },
        },
        {
            "name": "shenzhen_pnr",
            "display_name": "深圳市规划和自然资源局",
            "category": "industry",
            "crawl_type": "browser",
            "sort_order": 13,
            "config": {
                "url": "https://pnr.sz.gov.cn/xxgk/gzdt/index.html",
                "wait_selector": ".col-lg-9",
                "list_selector": ".list-group li",
                "mapping": {
                    "title": {"selector": "a", "attr": "text"},
                    "link": {"selector": "a", "attr": "href"},
                    "time": {"selector": "span", "attr": "text"},
                },
                "fetch_content": False,
            },
        },
        {
            "name": "chongqing_ghzrzyj",
            "display_name": "重庆市规划和自然资源局",
            "category": "industry",
            "crawl_type": "browser",
            "sort_order": 14,
            "config": {
                "url": "https://ghzrzyj.cq.gov.cn/zwgk_186/zcjd/wap.html",
                "wait_selector": ".sec-content",
                "list_selector": ".gl-list li",
                "mapping": {
                    "title": {"selector": "a", "attr": "text"},
                    "link": {"selector": "a", "attr": "href"},
                    "time": {"selector": "p", "attr": "text"},
                },
                "fetch_content": False,
            },
        },


        # ============================================================
        # tech (大模型学习资料) — 4 个源
        # ============================================================
        {
            "name": "csdn_clip",
            "display_name": "CSDN搜索(Clip)",
            "category": "tech",
            "crawl_type": "api",
            "sort_order": 21,
            "config": {
                "url": "https://so.csdn.net/api/v3/search?q=clip&t=blog&p=1&s=0&tm=0&lv=-1&ft=0&l=&u=&ct=-1&pnt=-1&ry=-1&ss=-1&dct=-1&vco=-1&cc=-1&sc=-1&akt=-1&art=-1&ca=-1&prs=&pre=&ecc=-1&ebc=-1&ia=1&dId=&cl=-1&scl=-1&tcl=-1&platform=pc&ab_test_code_overlap=&ab_test_random_code=&trace_id=",
                "method": "GET",
                "response_type": "json",
                "item_path": "result_vos",
                "fetch_content": False,
                "mapping": {
                    "title": "title",
                    "link": "url",
                    "time": "created_at",
                    "summary": "digest",
                    "tags": "search_tag",
                },
            },
        },
        {
            "name": "csdn_image_detect",
            "display_name": "CSDN搜索(图像检测)",
            "category": "tech",
            "crawl_type": "api",
            "sort_order": 22,
            "config": {
                "url": "https://so.csdn.net/api/v3/search?q=图像检测&t=blog&p=1&s=0&tm=0&lv=-1&ft=0&l=&u=&ct=-1&pnt=-1&ry=-1&ss=-1&dct=-1&vco=-1&cc=-1&sc=-1&akt=-1&art=-1&ca=-1&prs=&pre=&ecc=-1&ebc=-1&urw=&ia=1&dId=&cl=-1&scl=-1&tcl=-1&platform=pc&ab_test_code_overlap=&ab_test_random_code=&trace_id=",
                "method": "GET",
                "response_type": "json",
                "item_path": "result_vos",
                "fetch_content": False,
                "mapping": {
                    "title": "title",
                    "link": "url",
                    "time": "created_at",
                    "summary": "digest",
                    "tags": "search_tag",
                },
            },
        },
        {
            "name": "jiqizhixin",
            "display_name": "机器之心",
            "category": "tech",
            "crawl_type": "api",
            "sort_order": 23,
            "config": {
                "url": "https://www.jiqizhixin.com/api/v4/articles.json?keyword=clip&page=1&per=20",
                "method": "GET",
                "response_type": "json",
                "item_path": "articles",
                "fetch_content": False,
                "mapping": {
                    "title": "title",
                    "link": "https://www.jiqizhixin.com/articles/{slug}",
                    "time": "publishedAt",
                    "summary": "content",
                    "tags": "tagList",
                },
            },
        },
        {
            "name": "modelscope_academy",
            "display_name": "ModelScope学院",
            "category": "tech",
            "crawl_type": "browser",
            "sort_order": 24,
            # 注意：modelscope.cn 是 CSS-in-JS 哈希 class，选择器只能用
            # URL 前缀 + img[alt] 等语义锚点；wait_ms 等 SPA 渲染完成再提取
            "config": {
                "url": "https://modelscope.cn/learn?page=1&query=前沿技术&sort=hot",
                "wait_selector": "a[href^='/learn/']",
                "wait_ms": 4000,
                "scroll_times": 1,
                "list_selector": "a[href^='/learn/']",
                "mapping": {
                    "title": {"selector": "img[alt]", "attr": "alt"},
                    "link": {"selector": "", "attr": "href"},
                },
                "fetch_content": False,
            },
        },
        # ============================================================
        # media (媒体新闻) — 2 个源
        # ============================================================
        {
            "name": "malagis",
            "display_name": "麻辣GIS",
            "category": "media",
            "crawl_type": "selector",
            "sort_order": 31,
            "config": {
                "url": "https://malagis.com/",
                "encoding": "utf-8",
                "list_selector": "article.post",
                "mapping": {
                    "title": {"selector": "h1 a", "attr": "text"},
                    "link": {"selector": "h1 a", "attr": "href"},
                    "time": {"selector": ".postinfo a", "attr": "text"},
                },
                "fetch_content": False,
            },
        },
        {
            "name": "china_hightech",
            "display_name": "中国高新技术产业导报",
            "category": "media",
            "crawl_type": "selector",
            "sort_order": 32,
            "config": {
                "url": "http://www.chinahightech.com/yaowen/node_479.html",
                "encoding": "utf-8",
                "list_selector": ".list-main .no-img",
                "mapping": {
                    "title": {"selector": "a", "attr": "text"},
                    "link": {"selector": "a", "attr": "href"},
                    "time": {"selector": "span", "attr": "text"},
                },
                "fetch_content": False,
            },
        },
        {
            "name": "zhiding",
            "display_name": "至顶网",
            "category": "media",
            "crawl_type": "selector",
            "sort_order": 6,
            "config": {
                "url": "https://www.zhiding.cn/",
                "encoding": "gb2312",
                "list_selector": ".k_information_con .information_content",
                "mapping": {
                    "title": {"selector": ".right_title a", "attr": "text"},
                    "link": {"selector": ".right_title a", "attr": "href"},
                    "time": {"selector": ".time", "attr": "text"},
                },
                "fetch_content": False,
            },
        },
        {
            "name": "shuzhi_qianxian",
            "display_name": "数智前线",
            "category": "media",
            "crawl_type": "selector",
            "sort_order": 7,
            "config": {
                "url": "https://www.tmtpost.com/user/6019196",
                "encoding": "utf-8",
                "list_selector": ".leftColumn .loadingContent .item",
                "mapping": {
                    "title": {"selector": ".r_top a", "attr": "text"},
                    "link": {"selector": ".r_top a", "attr": "href"},
                    "time": {"selector": ".newTime._time", "attr": "text"},
                },
                "fetch_content": False,
            },
        },
        {
            "name": "donews",
            "display_name": "DoNews",
            "category": "media",
            "crawl_type": "browser",
            "sort_order": 8,
            "config": {
                "url": "https://www.donews.com/newsflash/index",
                "wait_selector": "#newloadmore",
                "list_selector": ".flash-left-item",
                "mapping": {
                    "title": {"selector": ".flash-item-title", "attr": "text"},
                    "link": {"selector": "a", "attr": "href"},
                    "time": {"selector": ".flash-item-date", "attr": "text"},
                },
                "fetch_content": False,
            },
        },
        {
            "name": "ziyuan_china",
            "display_name": "资源中国",
            "category": "media",
            "crawl_type": "api",
            "sort_order": 16,
            "config": {
                "url": "https://api.iziran.net/api/getArticles?cid=29167&rowNumber=0&lastFileID=0&pageNumber=1&pageSize=20&imgTop=0&orderby=",
                "method": "GET",
                "response_type": "json",
                "item_path": "list",
                "fetch_content": False,
                "mapping": {
                    "title": "title",
                    "link": "https://www.iziran.net/news.html?aid={fileID}",
                    "time": "publishTime",
                },
            },
        },

        {
            "name": "china_smart_city",
            "display_name": "中国智慧城市网",
            "category": "media",
            "crawl_type": "selector",
            "sort_order": 18,
            "config": {
                "url": "http://cnscn.com.cn/news/list.php?catid=1013",
                "encoding": "utf-8",
                "list_selector": ".catlist ul li",
                "mapping": {
                    "title": {"selector": "a", "attr": "text"},
                    "link": {"selector": "a", "attr": "href"},
                    "time": {"selector": "span", "attr": "text"},
                },
                "fetch_content": False,
            },
        },
    ]


if __name__ == "__main__":
    """独立运行时直接填充种子数据。"""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        seed_sources(db)
    finally:
        db.close()
