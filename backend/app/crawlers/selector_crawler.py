"""选择器类型爬虫 — 处理 crawl_type == 'selector' 的数据源（静态 HTML + CSS 选择器）"""
import logging
from urllib.parse import urljoin

import httpx

from app.crawlers.base import BaseCrawler
from app.models.source import Source

logger = logging.getLogger("crawler.selector")


class SelectorCrawler(BaseCrawler):
    """适用于 HTML 静态页面，通过 CSS 选择器从 DOM 中提取数据。"""

    def fetch(self, source: Source) -> list[dict]:
        """从选择器型数据源抓取新闻列表。"""
        config = source.config
        url = config["url"]
        encoding = config.get("encoding", "utf-8")
        list_selector = config.get("list_selector", "")
        mapping = config.get("mapping", {})
        fetch_content = config.get("fetch_content", False)
        content_selector = config.get("content_selector")

        try:
            from bs4 import BeautifulSoup

            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                resp = client.get(url)
                resp.encoding = encoding
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")

                items_elements = soup.select(list_selector) if list_selector else [soup]
                logger.info("list_selector 匹配 %d 个元素", len(items_elements))

                items = []
                for elem in items_elements:
                    item = _extract_item(elem, mapping, url)
                    if item.get("link") and item.get("title"):
                        time_str = item.get("time")
                        item["time"] = self._parse_time(time_str, mapping) if time_str else None

                        if fetch_content and content_selector and item.get("link"):
                            item["content"] = self._fetch_content(
                                item["link"], content_selector, encoding
                            )

                        items.append(item)

                return items
        except Exception as e:
            logger.warning("%s 抓取失败: %r", source.name, e)
            return []


def _extract_item(element, mapping: dict, base_url: str) -> dict:
    """从单个 HTML 元素中根据 mapping 提取各字段值（模块级函数）。"""
    result = {}
    for field, field_config in mapping.items():
        selector = field_config.get("selector", "")
        attr = field_config.get("attr", "text")

        matched = element.select_one(selector) if selector else element
        if matched is None:
            continue

        if attr == "text":
            value = BaseCrawler._get_direct_text(matched)
        else:
            value = matched.get(attr, "")

        if field == "link" and value and not value.startswith(
            ("http://", "https://", "javascript:")
        ):
            value = urljoin(base_url, value)

        result[field] = value

    return result
