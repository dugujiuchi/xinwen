"""浏览器类型爬虫 — 处理 crawl_type == 'browser' 的数据源（JS 渲染页面 + Playwright）"""
import json
import logging
import time
import threading
from random import uniform
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

from app.crawlers.base import BaseCrawler
from app.models.source import Source

logger = logging.getLogger("crawler.browser")

_playwright = None
_browser = None
_lock = threading.Lock()


def _get_browser():
    """获取复用的浏览器实例（模块级单例，减少进程创建）。"""
    global _playwright, _browser
    if _browser is None:
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
    return _browser


class BrowserCrawler(BaseCrawler):
    """适用于需要 JS 渲染的动态页面。

    支持两种提取模式：
    - "dom"（默认）：渲染后获取 HTML，用 CSS 选择器提取
    - "js_state"：从 window.__INITIAL_STATE__ 等 JS 全局变量提取

    Playwright 浏览器实例在模块级别复用，避免反复创建/销毁 Chrome 进程导致僵尸进程。
    """

    page_timeout: int = 60000

    def fetch(self, source: Source) -> list[dict]:
        """从浏览器渲染型数据源抓取新闻列表。"""
        config = source.config
        url = config["url"]
        scroll_times = config.get("scroll_times", 0)
        wait_selector = config.get("wait_selector")
        list_selector = config.get("list_selector", "")
        extract_mode = config.get("extract_mode", "dom")
        mapping = config.get("mapping", {})
        fetch_content = config.get("fetch_content", False)
        content_selector = config.get("content_selector")

        with _lock:
            browser = _get_browser()
            try:
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
                page = context.new_page()
                time.sleep(uniform(1.0, 2.0))
                page.goto(url, timeout=self.page_timeout)

                if wait_selector:
                    try:
                        page.wait_for_selector(wait_selector, timeout=15000)
                    except Exception:
                        logger.warning("wait_selector 超时: %s", wait_selector)

                _scroll(page, scroll_times)

                if extract_mode == "js_state":
                    items = self._extract_js_state(page, config)
                else:
                    items = self._extract_dom(page, mapping, list_selector, url)
                    if not items:
                        title = page.title()
                        body_len = len(page.content())
                        logger.warning(
                            "DOM 提取为 0 条 | 页面标题: %s | HTML大小: %d bytes",
                            title, body_len,
                        )

                if fetch_content and content_selector:
                    for item in items:
                        if item.get("link"):
                            item["content"] = self._fetch_content_browser(
                                context, item["link"], content_selector
                            )

                return items
            except Exception as e:
                logger.warning("%s 抓取失败: %r", source.name, e)
                return []
            finally:
                try:
                    context.close()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # DOM 模式提取
    # ------------------------------------------------------------------

    def _extract_dom(self, page, mapping: dict, list_selector: str, base_url: str) -> list[dict]:
        """获取渲染后的 HTML，使用 BeautifulSoup + CSS 选择器提取数据。"""
        from bs4 import BeautifulSoup

        html = page.content()
        soup = BeautifulSoup(html, "lxml")

        items_elements = soup.select(list_selector) if list_selector else [soup]
        logger.info("list_selector 匹配 %d 个元素", len(items_elements))
        items = []

        for elem in items_elements:
            item = {}
            for field, field_config in mapping.items():
                if not isinstance(field_config, dict):
                    continue
                selector = field_config.get("selector", "")
                attr = field_config.get("attr", "text")

                matched = elem.select_one(selector) if selector else elem
                if not matched:
                    continue

                if attr == "text":
                    value = BaseCrawler._get_direct_text(matched)
                else:
                    value = matched.get(attr, "")

                if field == "link" and value and not value.startswith(
                    ("http://", "https://")
                ):
                    value = urljoin(base_url, value)

                item[field] = value

            if item.get("link") and item.get("title"):
                item["time"] = BaseCrawler.parse_time_value(item.get("time"))
                items.append(item)

        return items

    # ------------------------------------------------------------------
    # JS State 模式提取
    # ------------------------------------------------------------------

    def _extract_js_state(self, page, config: dict) -> list[dict]:
        """从页面 JS 全局变量中提取数据。"""
        state_key = config.get("state_key", "")
        state_path = config.get("state_path", "")
        mapping = config.get("mapping", {})

        if not state_key:
            logger.warning("js_state 模式缺少 state_key")
            return []

        try:
            state_json = page.evaluate(f"JSON.stringify(window.{state_key})")
            state_data = json.loads(state_json)

            if state_path:
                items_data = self._navigate_path(state_data, state_path)
            else:
                items_data = state_data

            if not isinstance(items_data, list):
                items_data = [items_data]

            items = []
            for item_data in items_data:
                if not isinstance(item_data, dict):
                    continue
                item = self._apply_mapping(item_data, mapping)

                if item.get("link") and item.get("title"):
                    item["time"] = self._parse_time(item.get("time"), mapping)
                    items.append(item)

            return items
        except Exception as e:
            logger.warning("JS state 提取失败: %r", e)
            return []

    # ------------------------------------------------------------------
    # 深度抓取（Browser 模式，使用 Playwright）
    # ------------------------------------------------------------------

    def _fetch_content_browser(self, context, url: str, content_selector: str) -> str:
        """使用 Playwright 打开详情页提取正文。"""
        try:
            from bs4 import BeautifulSoup

            page = context.new_page()
            page.goto(url, timeout=self.page_timeout)
            page.wait_for_load_state("networkidle")

            html = page.content()
            page.close()

            soup = BeautifulSoup(html, "lxml")
            elements = soup.select(content_selector)
            if elements:
                return "\n".join(el.get_text(strip=True) for el in elements)
        except Exception as e:
            logger.warning("深度抓取失败 %s: %r", url, e)
        return ""


def _scroll(page, scroll_times: int):
    """滚动加载（模块级函数）。"""
    for _ in range(scroll_times):
        page.mouse.wheel(0, 300)
        time.sleep(1.2)
