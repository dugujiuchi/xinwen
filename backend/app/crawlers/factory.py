"""爬虫工厂 — 根据 crawl_type 创建对应的 Fetcher"""
from app.crawlers.api_crawler import APICrawler
from app.crawlers.base import BaseCrawler
from app.crawlers.browser_crawler import BrowserCrawler
from app.crawlers.selector_crawler import SelectorCrawler


class CrawlerFactory:
    """根据数据源的 crawl_type 返回对应的抓取器实例。"""

    _crawlers: dict[str, BaseCrawler] = {
        "api": APICrawler(),
        "selector": SelectorCrawler(),
        "browser": BrowserCrawler(),
    }

    @classmethod
    def get_crawler(cls, crawl_type: str) -> BaseCrawler:
        """根据 crawl_type 获取对应的 Fetcher 实例。

        Args:
            crawl_type: 抓取方式，取值 "api" / "selector" / "browser"

        Returns:
            BaseCrawler 子类实例

        Raises:
            ValueError: 不支持的 crawl_type
        """
        crawler = cls._crawlers.get(crawl_type)
        if not crawler:
            raise ValueError(f"不支持的抓取类型: {crawl_type}")
        return crawler
