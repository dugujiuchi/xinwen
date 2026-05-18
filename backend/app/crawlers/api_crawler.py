"""API 类型爬虫 — 处理 crawl_type == 'api' 的数据源（JSON/XML 响应）"""
import logging
from xml.etree import ElementTree as ET
from typing import Any

import httpx

from app.crawlers.base import BaseCrawler
from app.models.source import Source

logger = logging.getLogger("crawler.api")


class APICrawler(BaseCrawler):
    """适用于提供标准 API 接口的数据源（JSON/XML 响应）。"""

    def fetch(self, source: Source) -> list[dict]:
        """从 API 数据源抓取新闻列表。"""
        config = source.config
        url = config["url"]
        method = config.get("method", "GET").upper()
        headers = config.get("headers", {})
        params = config.get("params", {})
        body = config.get("body")
        response_type = config.get("response_type", "json")
        item_path = config.get("item_path", "")
        mapping = config.get("mapping", {})
        fetch_content = config.get("fetch_content", True)
        content_selector = config.get("content_selector")

        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                if method == "GET":
                    resp = client.get(url, headers=headers, params=params)
                elif method == "POST":
                    resp = client.post(url, headers=headers, content=body)
                else:
                    raise ValueError(f"不支持的请求方法: {method}")

                resp.raise_for_status()

                if response_type == "xml":
                    raw_data = _parse_xml(resp.text)
                else:
                    raw_data = resp.json()

                items_data = self._navigate_path(raw_data, item_path) if item_path else raw_data
                if not isinstance(items_data, list):
                    items_data = [items_data]

                items = []
                for item_data in items_data:
                    if not isinstance(item_data, dict):
                        continue
                    item = self._apply_mapping(item_data, mapping)
                    if item.get("link") and item.get("title"):
                        item["time"] = self._parse_time(item.get("time"), mapping)

                        need_content = (
                            fetch_content
                            and content_selector
                            and not item.get("content")
                        )
                        if need_content and item.get("link"):
                            item["content"] = self._fetch_content(item["link"], content_selector)

                        items.append(item)

                return items
        except Exception as e:
            logger.warning("%s 抓取失败: %r", source.name, e)
            return []


def _parse_xml(text: str) -> dict:
    """将 XML 文本解析为嵌套 dict。"""
    root = ET.fromstring(text)
    return _xml_to_dict(root)


def _xml_to_dict(element: ET.Element) -> Any:
    """将 XML Element 递归转为 dict（模块级函数，仅 APICrawler 使用）。"""
    result: dict[str, Any] = {}
    for child in element:
        if len(child) > 0:
            value = _xml_to_dict(child)
        else:
            value = child.text or ""
        if child.tag in result:
            existing = result[child.tag]
            if not isinstance(existing, list):
                result[child.tag] = [existing]
            result[child.tag].append(value)
        else:
            result[child.tag] = value
    if not result:
        return element.text or ""
    return result
