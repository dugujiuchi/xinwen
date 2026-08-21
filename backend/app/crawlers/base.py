"""爬虫基类 —— 统一时间解析、数据导航、映射、深度抓取等共享逻辑"""
import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Any

from app.models.source import Source

logger = logging.getLogger("crawler")
CRAWL_TYPES = ("api", "selector", "browser")

# 常见追踪参数（归一化链接时剥离，保证去重 key 稳定）
TRACKING_PARAMS = {
    "request_id",
    "ops_request_misc",
    "biz_id",
    "trace_id",
    "spm",
    "scm",
    "ab_test_code_overlap",
    "ab_test_random_code",
}


class BaseCrawler(ABC):
    """爬虫抽象基类。所有 Fetcher 实现 fetch() 方法。"""

    # mapping 中用于配置而非字段映射的 key
    MAPPING_CONFIG_KEYS = {"time_type"}

    # 仅含日期的格式（无时分秒），解析后需补抓取时间
    _DATE_ONLY_FORMATS = {"%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"}

    @abstractmethod
    def fetch(self, source: Source) -> list[dict]:
        """从数据源抓取新闻列表。

        返回格式：
        [{title, link, time(datetime), summary(可选), content(可选), tags(可选)}]
        """
        ...

    # ------------------------------------------------------------------
    # 时间解析（全链路 naive 北京时间）
    # ------------------------------------------------------------------

    @staticmethod
    def parse_time_value(value: Any, time_type: str = "") -> datetime | None:
        """统一时间解析，全部返回 naive datetime（北京时间）。

        Args:
            value: 原始时间值（int/float/str）
            time_type: "timestamp" 时按时间戳处理

        Returns:
            naive datetime（北京时间），解析失败返回 None
        """
        if value is None:
            return None

        if isinstance(value, datetime):
            # 有 tz 则转为北京时间再 strip，无 tz 原样保留
            if value.tzinfo is not None:
                value = value.astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None)
            return value

        # 时间戳模式（Unix 时间 → UTC → 北京时间 naive）
        if time_type == "timestamp":
            try:
                ts = int(value)
                if ts > 1_000_000_000_0:
                    ts = ts / 1000
                utc_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                return utc_dt.astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None)
            except (ValueError, TypeError, OSError):
                return None

        if not isinstance(value, str):
            return None

        s = value.strip()
        if not s:
            return None

        # 北京时间当前时刻（naive，用于相对时间和日期补时）
        bj_now = datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None)

        # ISO 格式
        try:
            iso_str = s.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso_str)
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None)
            return dt
        except (ValueError, TypeError):
            pass

        # 常见日期格式（覆盖中文新闻网站主流格式）
        for fmt in [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y年%m月%d日",
            "%Y年%m月%d日 %H:%M",
            "%Y年%m月%d日 %H:%M:%S",
        ]:
            try:
                dt = datetime.strptime(s, fmt)
                # 仅日期格式：补抓取时间（时分秒），否则默认 00:00 无意义
                if fmt in BaseCrawler._DATE_ONLY_FORMATS:
                    dt = dt.replace(hour=bj_now.hour, minute=bj_now.minute, second=bj_now.second)
                return dt
            except (ValueError, TypeError):
                continue

        # 中文相对时间（基于北京时间计算，返回 naive）
        dt = BaseCrawler._parse_relative_time(s, bj_now)
        if dt:
            return dt

        return None

    @staticmethod
    def _parse_relative_time(text: str, bj_now: datetime) -> datetime | None:
        """解析中文相对时间表达式，返回 naive datetime（北京时间）。

        bj_now: 北京时间的当前时刻（naive）
        """
        bj_tz = timezone(timedelta(hours=8))

        def _clamp_year(dt_naive: datetime) -> datetime:
            """若构造出的日期在未来，则回退一年（处理跨年抓取）。"""
            aware = dt_naive.replace(tzinfo=bj_tz)
            now_aware = bj_now.replace(tzinfo=bj_tz)
            if aware > now_aware:
                dt_naive = dt_naive.replace(year=dt_naive.year - 1)
            return dt_naive

        # x分钟前
        m = re.search(r'(\d+)\s*分钟前', text)
        if m:
            return bj_now - timedelta(minutes=int(m.group(1)))

        # x小时前
        m = re.search(r'(\d+)\s*小时前', text)
        if m:
            return bj_now - timedelta(hours=int(m.group(1)))

        # x天前
        m = re.search(r'(\d+)\s*天前', text)
        if m:
            return bj_now - timedelta(days=int(m.group(1)))

        # x周前
        m = re.search(r'(\d+)\s*周前', text)
        if m:
            return bj_now - timedelta(weeks=int(m.group(1)))

        # x秒前
        m = re.search(r'(\d+)\s*秒前', text)
        if m:
            return bj_now - timedelta(seconds=int(m.group(1)))

        # 刚刚
        if '刚刚' in text:
            return bj_now

        # 今天 HH:MM
        m = re.search(r'今天\s*(\d{1,2}):(\d{2})', text)
        if m:
            return bj_now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)

        # 昨天 HH:MM
        m = re.search(r'昨天\s*(\d{1,2}):(\d{2})', text)
        if m:
            dt = bj_now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
            return dt - timedelta(days=1)

        # 前天 HH:MM
        m = re.search(r'前天\s*(\d{1,2}):(\d{2})', text)
        if m:
            dt = bj_now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
            return dt - timedelta(days=2)

        # MM-DD HH:MM 或 MM月DD日 HH:MM
        m = re.search(r'(\d{1,2})[月\-/](\d{1,2})日?\s*(\d{1,2}):(\d{2})', text)
        if m:
            try:
                dt = bj_now.replace(month=int(m.group(1)), day=int(m.group(2)),
                                    hour=int(m.group(3)), minute=int(m.group(4)),
                                    second=0, microsecond=0)
                return _clamp_year(dt)
            except ValueError:
                pass

        # MM-DD 或 MM月DD日（无时间，补抓取时间）
        m = re.search(r'(\d{1,2})[月\-/](\d{1,2})日?', text)
        if m:
            try:
                dt = bj_now.replace(month=int(m.group(1)), day=int(m.group(2)))
                return _clamp_year(dt)
            except ValueError:
                pass

        # HH:MM（今天的时间）
        m = re.search(r'^(\d{1,2}):(\d{2})$', text)
        if m:
            return bj_now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)

        return None

    def _parse_time(self, value: Any, mapping: dict) -> datetime | None:
        """解析时间字段，委托给基类的统一时间解析。"""
        return BaseCrawler.parse_time_value(value, mapping.get("time_type", ""))

    # ------------------------------------------------------------------
    # 数据导航与映射（API / JS State 模式共用）
    # ------------------------------------------------------------------

    @staticmethod
    def _navigate_path(data: Any, path: str) -> Any:
        """按点号分隔的路径从嵌套 dict/list 中取值。"""
        if not path:
            return data
        parts = path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    current = current[idx] if 0 <= idx < len(current) else None
                except (ValueError, IndexError):
                    return None
            else:
                return None
            if current is None:
                return None
        return current

    def _apply_mapping(self, item_data: dict, mapping: dict) -> dict:
        """根据 mapping 配置将原始字典映射为统一格式。

        支持两种映射方式：
        - 简单映射：{"title": "field_name"}
        - 模板映射：{"link": "https://example.com/news/{id}"}

        所有文本字段自动去除 HTML 标签。
        """
        result: dict[str, Any] = {}
        for field, config_value in mapping.items():
            if field in self.MAPPING_CONFIG_KEYS:
                continue
            if isinstance(config_value, str):
                if "{" in config_value and "}" in config_value:
                    result[field] = BaseCrawler._strip_html(
                        self._apply_template(config_value, item_data)
                    )
                else:
                    raw = self._navigate_path(item_data, config_value)
                    value = raw if raw is not None else ""
                    if isinstance(value, str):
                        value = BaseCrawler._strip_html(value)
                    result[field] = value
            else:
                result[field] = config_value
        return result

    @staticmethod
    def canonicalize_link(link: str) -> str:
        """归一化链接：剥离追踪参数（request_id / utm_* / spm 等），
        返回稳定的 URL 用于去重与展示。

        注意：只剥离已知追踪参数，保留功能性 query（如 ?aid=123），
        避免破坏以 query 携带资源 ID 的链接。
        """
        from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

        if not link or "?" not in link:
            return link
        parts = urlsplit(link)
        pairs = parse_qsl(parts.query, keep_blank_values=True)
        kept = [
            (k, v)
            for k, v in pairs
            if k not in TRACKING_PARAMS and not k.lower().startswith("utm_")
        ]
        if len(kept) == len(pairs):
            return link
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), ""))

    @staticmethod
    def _strip_html(text: str) -> str:
        """去除 HTML 标签（如 <em>、<br> 等），保留纯文本。"""
        if not text or not isinstance(text, str):
            return text
        return re.sub(r"<[^>]*>", "", text).strip()

    @staticmethod
    def _get_direct_text(element) -> str:
        """从 HTML 元素提取直接文本（不含子元素文本）。

        解决 <a>标题<span>时间</span></a> 中 get_text() 会混入时间的问题。
        优先只取直接文本节点，若无则回退到普通 get_text()。
        """
        try:
            direct = element.find_all(text=True, recursive=False)
            text = "".join(t.strip() for t in direct).strip()
            if text:
                return text
        except Exception:
            pass
        return element.get_text(strip=True)

    @staticmethod
    def _apply_template(template: str, item_data: dict) -> str:
        """将模板字符串中的 {key} 替换为 item_data 中的值。"""

        def replacer(match: re.Match) -> str:
            key = match.group(1)
            return str(item_data.get(key, ""))

        return re.sub(r"\{(\w+)\}", replacer, template)

    # ------------------------------------------------------------------
    # 深度抓取（httpx + BeautifulSoup）
    # ------------------------------------------------------------------

    def _fetch_content(self, url: str, content_selector: str, encoding: str = "utf-8") -> str:
        """从详情页通过 CSS 选择器提取正文。"""
        try:
            import httpx
            from bs4 import BeautifulSoup

            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                resp = client.get(url)
                resp.encoding = encoding
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")
                elements = soup.select(content_selector)
                if elements:
                    return "\n".join(el.get_text(strip=True) for el in elements)
        except Exception as e:
            logger.warning("深度抓取失败 %s: %r", url, e)
        return ""
