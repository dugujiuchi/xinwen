import time
from abc import ABC, abstractmethod
from random import uniform
from typing import Optional

from playwright.sync_api import Page, sync_playwright


class BaseCrawler(ABC):
    """爬虫基类，提供通用抓取能力。

    子类只需实现 extract() 方法定义解析逻辑。
    """

    name: str = ""
    source_name: str = ""
    base_url: str = ""
    page_timeout: int = 60000
    scroll_times: int = 0

    @abstractmethod
    def extract(self, page: Page) -> list[dict]:
        """提取新闻列表。

        子类实现此方法，返回格式：
        [{title, link, time(可选datetime), summary(可选)}]
        """
        ...

    def fetch(self) -> list[dict]:
        """通用抓取流程，子类不需要重写"""
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
            time.sleep(uniform(1.0, 2.0))
            page = browser.new_page()
            page.set_extra_http_headers({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            })

            try:
                page.goto(self.base_url, timeout=self.page_timeout)
                self._scroll(page)
                return self.extract(page)
            except Exception as e:
                print(f"[{self.name}] 抓取失败: {e}")
                return []
            finally:
                browser.close()

    def _scroll(self, page: Page):
        """滚动加载（子类可覆盖）"""
        for _ in range(self.scroll_times):
            page.mouse.wheel(0, 300)
            time.sleep(1.2)
