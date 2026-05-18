"""自动检测数据源类型和配置 — 用户只需提供 URL 即可智能分析"""
import logging
from urllib.parse import urljoin

import httpx

logger = logging.getLogger("crawler.auto_detect")

# 常见 JSON 列表路径候选
_JSON_LIST_PATHS = [
    "data.list", "data.items", "data.records", "data",
    "list", "items", "results", "result_vos", "articles",
    "data.data", "data.result", "data.news",
]

# 常见 JSON 字段名映射
_JSON_FIELD_ALIASES = {
    "title": ["title", "name", "subject", "headline"],
    "link": ["url", "link", "href", "urlToArticle", "shareUrl", "newsUrl"],
    "time": ["publishTime", "publishedAt", "created_at", "pubTime",
             "createTime", "publish_time", "published_timestamp", "date", "time",
             "publishedAt", "publishDate", "addTime"],
    "summary": ["abstract", "digest", "summary", "description", "content",
                "desc", "introduction", "brief"],
    "content": ["content", "body", "text", "article", "detail"],
    "tags": ["tagList", "tags", "keywords", "labels", "search_tag", "categories"],
}


def analyze_url(url: str) -> dict:
    """分析 URL，返回建议的 crawl_type、config 和预览数据。

    Returns:
        {"crawl_type": "api"|"selector"|"browser",
         "config": {...},
         "preview": [{"title": ..., "link": ..., ...}, ...]}
    """
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            resp = client.get(url, headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            })
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "").lower()

            if "json" in content_type:
                return _analyze_json(url, resp.text)
            elif "html" in content_type or resp.text.strip().startswith("<!") or resp.text.strip().startswith("<"):
                return _analyze_html(url, resp.text, resp.encoding or "utf-8")
            else:
                return _analyze_html(url, resp.text, resp.encoding or "utf-8")
    except httpx.HTTPError as e:
        logger.warning("URL 分析请求失败: %r", e)
        return {"crawl_type": "selector", "config": {"url": url}, "preview": [],
                "error": f"请求失败: {e}"}
    except Exception as e:
        logger.warning("URL 分析异常: %r", e)
        return {"crawl_type": "selector", "config": {"url": url}, "preview": [],
                "error": f"分析失败: {e}"}


def _analyze_json(url: str, text: str) -> dict:
    """分析 JSON 响应，自动检测 item_path 和字段映射。"""
    import json as json_mod

    try:
        data = json_mod.loads(text)
    except json_mod.JSONDecodeError as e:
        return {"crawl_type": "api", "config": {"url": url},
                "preview": [], "error": f"JSON 解析失败: {e}"}

    # 尝试各种列表路径
    best_path = ""
    best_items = []

    # 首先检查根节点本身是否为列表
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
        best_path = ""
        best_items = data
    else:
        for path in _JSON_LIST_PATHS:
            items = _navigate(data, path)
            if isinstance(items, list) and len(items) > 0 and isinstance(items[0], dict):
                best_path = path
                best_items = items
                break

    if not best_items:
        # 兜底：递归搜索第一个列表
        best_path, best_items = _find_first_list(data)

    if not best_items:
        return {"crawl_type": "api", "config": {"url": url},
                "preview": [], "error": "未能自动识别列表数据，请使用高级模式手动配置"}

    # 自动映射字段
    mapping, time_type = _auto_map_json_fields(best_items[0])

    config = {
        "url": url,
        "method": "GET",
        "response_type": "json",
        "item_path": best_path,
        "fetch_content": "content" in mapping,
        "mapping": mapping,
    }
    if time_type:
        config["mapping"]["time_type"] = time_type

    # 预览前 10 条
    preview = _preview_json_items(best_items[:10], mapping, time_type)

    return {"crawl_type": "api", "config": config, "preview": preview}


def _analyze_html(url: str, html: str, encoding: str) -> dict:
    """分析 HTML 页面，自动检测列表结构和字段映射。"""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return {"crawl_type": "selector", "config": {"url": url},
                "preview": [], "error": "缺少 BeautifulSoup 依赖"}

    soup = BeautifulSoup(html, "lxml")

    # 尝试常见列表容器选择器
    list_candidates = _find_list_candidates(soup)

    if not list_candidates:
        return {"crawl_type": "selector", "config": {"url": url, "encoding": encoding},
                "preview": [], "error": "未能自动识别列表结构，请使用高级模式手动配置"}

    # 选最佳的候选（条目最多且含链接的）
    best = max(list_candidates, key=lambda c: c["score"])

    config = {
        "url": url,
        "encoding": encoding,
        "list_selector": best["list_selector"],
        "fetch_content": False,
        "mapping": best["mapping"],
    }

    # 生成预览
    preview = _preview_html_items(soup, best["list_selector"], best["mapping"], url)

    return {"crawl_type": "selector", "config": config, "preview": preview}


# ------------------------------------------------------------------
# JSON 分析辅助
# ------------------------------------------------------------------

def _navigate(data, path: str):
    """按点号路径从嵌套 dict 中取值。"""
    if not path:
        return data
    current = data
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            current = current[int(part)] if int(part) < len(current) else None
        else:
            return None
        if current is None:
            return None
    return current


def _find_first_list(data, prefix: str = ""):
    """递归搜索第一个包含 dict 的列表。"""
    if isinstance(data, list):
        if len(data) > 0 and isinstance(data[0], dict):
            return prefix, data
        return "", []
    if isinstance(data, dict):
        for key, value in data.items():
            new_prefix = f"{prefix}.{key}" if prefix else key
            path, items = _find_first_list(value, new_prefix)
            if items:
                return path, items
    return "", []


def _auto_map_json_fields(sample: dict) -> tuple[dict, str]:
    """根据样本字段名自动映射。"""
    mapping: dict = {}
    time_type = ""

    # 收集所有可用字段名
    sample_keys = list(sample.keys())
    sample_keys_lower = [k.lower() for k in sample_keys]

    for target, aliases in _JSON_FIELD_ALIASES.items():
        if target == "content":
            continue  # content 优先从 fetch_content 深度抓取
        for alias in aliases:
            if alias in sample_keys:
                mapping[target] = alias
                break
            # 大小写不敏感匹配
            for i, kl in enumerate(sample_keys_lower):
                if kl == alias.lower():
                    mapping[target] = sample_keys[i]
                    break
            if target in mapping:
                break

    # 如果没匹配到 title/link，用启发式
    if "title" not in mapping:
        for k in sample_keys:
            if "title" in k.lower() or "name" in k.lower() or "标题" in k:
                mapping["title"] = k
                break
        # 兜底：选最长的字符串字段
        if "title" not in mapping:
            str_fields = [(k, v) for k, v in sample.items() if isinstance(v, str)]
            if str_fields:
                mapping["title"] = max(str_fields, key=lambda x: len(x[1]))[0]

    if "link" not in mapping:
        for k in sample_keys:
            if "url" in k.lower() or "link" in k.lower() or "href" in k.lower():
                mapping["link"] = k
                break
        # 兜底：选含 http 的字段值来反推
        if "link" not in mapping:
            for k, v in sample.items():
                if isinstance(v, str) and v.startswith("http"):
                    mapping["link"] = k
                    break

    if "time" not in mapping:
        for k in sample_keys:
            if "time" in k.lower() or "date" in k.lower() or "publish" in k.lower():
                mapping["time"] = k
                break

    # 检测时间类型
    time_key = mapping.get("time", "")
    time_val = sample.get(time_key) if time_key else None
    if isinstance(time_val, (int, float)):
        time_type = "timestamp"

    return mapping, time_type


def _preview_json_items(items: list, mapping: dict, time_type: str) -> list[dict]:
    """从 JSON 条目生成预览。"""
    from app.crawlers.base import BaseCrawler

    preview = []
    for item_data in items[:10]:
        if not isinstance(item_data, dict):
            continue
        result: dict = {}
        for field, key in mapping.items():
            if field in ("time_type",):
                continue
            if isinstance(key, str):
                val = _navigate(item_data, key)
                result[field] = val if val is not None else ""

        # 处理模板型 link（如 https://xxx.com/news/{id}）
        link = result.get("link", "")
        if "{" in link and "}" in link:
            # 尝试模板替换
            import re as re_mod
            def replacer(m):
                return str(item_data.get(m.group(1), ""))
            link = re_mod.sub(r"\{(\w+)\}", replacer, link)
            result["link"] = link

        if "time" in result:
            result["time_display"] = _format_time_display(result["time"])

        if result.get("title") and result.get("link"):
            preview.append(result)

    return preview


# ------------------------------------------------------------------
# HTML 分析辅助
# ------------------------------------------------------------------

# 常见列表容器模式
_LIST_PATTERNS = [
    # ul/ol 下直接 li
    ("ul li", "ul li"),
    ("ol li", "ol li"),
    # 常见 class 名
    (".news-list li", ".news-list li"),
    (".article-list li", ".article-list li"),
    (".list li", ".list li"),
    (".news_list li", ".news_list li"),
    (".list-group li", ".list-group li"),
    # div 列表
    ("article", "article"),
    (".news-item", ".news-item"),
    (".list-item", ".list-item"),
    (".article-item", ".article-item"),
    # 通用
    ("[class*='list'] > [class*='item']", "[class*='list'] > [class*='item']"),
    ("[class*='list'] li", "[class*='list'] li"),
    ("[class*='news'] li", "[class*='news'] li"),
    ("[class*='article']", "[class*='article']"),
]


def _find_list_candidates(soup) -> list[dict]:
    """在 HTML 中寻找列表候选。"""
    candidates = []

    for name, selector in _LIST_PATTERNS:
        # 容器选择器 — 定位重复元素
        items = soup.select(selector)
        if len(items) < 3:
            continue

        # 找到父容器，以便生成稳定的 list_selector
        # 取第一个 item 的父元素
        first_item = items[0]
        parent = first_item.parent
        if parent is None:
            continue

        # 生成容器级 list_selector：用 tag + class
        parent_tag = parent.name
        parent_class = ".".join(parent.get("class", []))
        item_tag = first_item.name
        item_class = ".".join(first_item.get("class", []))

        if parent_class:
            list_selector = f"{parent_tag}.{parent_class} > {item_tag}"
            if item_class:
                list_selector += f".{item_class}"
        else:
            list_selector = f"{parent_tag} > {item_tag}"

        # 分析每个 item 内有没有链接、标题、时间
        link_count = 0
        title_fields = []
        time_fields = []
        for item in items[:5]:
            links = item.select("a[href]")
            if links:
                link_count += 1
            # 尝试找标题和时间的子选择器
            if not title_fields:
                title_fields = _guess_field_selectors(item)
            if not time_fields:
                time_fields = _guess_time_selectors(item)

        if link_count == 0:
            continue

        # 构建 mapping
        mapping = {}
        if title_fields:
            best_title = title_fields[0]
            mapping["title"] = {"selector": best_title["selector"], "attr": best_title.get("attr", "text")}
        else:
            mapping["title"] = {"selector": "a", "attr": "text"}

        # link 大概率是第一个 a 标签
        mapping["link"] = {"selector": "a", "attr": "href"}

        if time_fields:
            best_time = time_fields[0]
            mapping["time"] = {"selector": best_time["selector"], "attr": best_time.get("attr", "text")}

        # 评分：优先链接覆盖率高、条目多的
        score = len(items) * (link_count / max(len(items[:5]), 1))

        candidates.append({
            "list_selector": list_selector,
            "mapping": mapping,
            "score": score,
        })

    return candidates


def _guess_field_selectors(item) -> list[dict]:
    """猜测 item 内的标题字段选择器。"""
    results = []
    # h1~h6 标签
    for h_tag in ["h3", "h2", "h1", "h4", "h5"]:
        el = item.select_one(h_tag)
        if el and el.get_text(strip=True):
            cls = ".".join(el.get("class", []))
            sel = f"{h_tag}.{cls}" if cls else h_tag
            results.append({"selector": sel, "attr": "text"})
            break

    # 带有 title 属性的 a 标签
    a_with_title = item.select_one("a[title]")
    if a_with_title and a_with_title.get("title", "").strip():
        results.append({"selector": "a[title]", "attr": "title"})

    return results


def _guess_time_selectors(item) -> list[dict]:
    """猜测 item 内的时间字段选择器。"""
    results = []
    time_classes = ["time", "date", "pub-time", "publish-time", "pubtime", "post-date"]
    for cls in time_classes:
        for tag in ["span", "time", "div", "em"]:
            el = item.select_one(f"{tag}.{cls}, {tag}[class*='{cls}']")
            if not el:
                el = item.select_one(f"[class*='{cls}']")
            if el and el.get_text(strip=True):
                c = ".".join(el.get("class", []))
                sel = f"{tag}.{c}" if c else tag
                results.append({"selector": sel, "attr": "text"})
                break
        if results:
            break
    return results


def _preview_html_items(soup, list_selector: str, mapping: dict, base_url: str) -> list[dict]:
    """从 HTML 提取预览数据。"""
    from app.crawlers.selector_crawler import _extract_item

    items = soup.select(list_selector)
    preview = []
    for elem in items[:10]:
        item = _extract_item(elem, mapping, base_url)
        if item.get("title") and item.get("link"):
            if "time" in item and item["time"]:
                item["time_display"] = _format_time_display(item["time"])
            preview.append(item)
            if len(preview) >= 10:
                break
    return preview


def _format_time_display(value) -> str:
    """格式化时间为可读字符串。"""
    from datetime import datetime
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, (int, float)):
        try:
            from datetime import timezone, timedelta
            ts = int(value)
            if ts > 1_000_000_000_0:
                ts = ts / 1000
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            dt = dt.astimezone(timezone(timedelta(hours=8)))
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
    return str(value)[:19] if isinstance(value, str) else str(value)
