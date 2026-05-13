import json
from datetime import datetime

from playwright.sync_api import Page

from app.crawlers.base import BaseCrawler


class GeekParkCrawler(BaseCrawler):
    """极客公园爬虫"""

    name = "geekpark"
    source_name = "极客公园"
    base_url = "https://www.geekpark.net/column/304"

    def extract(self, page: Page) -> list[dict]:
        initial_state = page.evaluate("""() => {
            return JSON.stringify(window.__INITIAL_STATE__);
        }""")
        data = json.loads(initial_state)
        items = []
        for post in data["column"]["column"]["posts"]:
            items.append({
                "title": post["title"],
                "link": f"https://www.geekpark.net/news/{post['id']}",
                "time": datetime.fromtimestamp(post["published_timestamp"]),
                "summary": post.get("abstract", ""),
            })
        return items
