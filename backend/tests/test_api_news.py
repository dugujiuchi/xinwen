from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine, SessionLocal
from app.models.news import News


@pytest.fixture(autouse=True)
def setup_db():
    """每个测试前清空 news 表（前置清理，保证用例可重复执行）"""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        db.query(News).delete()
        db.commit()
    yield


client = TestClient(app)


def _create_test_news(title: str, source: str = "测试来源", pub_time: str = "2025-01-01"):
    with SessionLocal() as db:
        news = News(
            title=title,
            link=f"https://test.com/{abs(hash(title))}",
            source_name=source,
            pub_time=datetime.fromisoformat(pub_time),
        )
        db.add(news)
        db.commit()
    return news


def test_list_news_empty():
    resp = client.get("/api/news")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    assert data["data"]["total"] == 0
    assert data["data"]["items"] == []


def test_list_news_with_data():
    _create_test_news("测试新闻标题", "虎嗅", "2025-06-01")
    _create_test_news("AI 大模型突破", "极客公园", "2025-06-02")

    resp = client.get("/api/news")
    data = resp.json()
    assert data["data"]["total"] == 2


def test_search_news():
    _create_test_news("低空经济发展趋势", "虎嗅")
    _create_test_news("AI 大模型突破", "极客公园")

    resp = client.get("/api/news?search=低空经济")
    data = resp.json()
    assert data["data"]["total"] == 1
    assert data["data"]["items"][0]["title"] == "低空经济发展趋势"


def test_filter_by_source():
    _create_test_news("新闻1", "虎嗅")
    _create_test_news("新闻2", "极客公园")

    resp = client.get("/api/news?source=虎嗅")
    data = resp.json()
    assert data["data"]["total"] == 1


def test_pagination():
    for i in range(25):
        _create_test_news(f"新闻{i}", "虎嗅", f"2025-01-{min(i+1, 28):02d}")

    resp = client.get("/api/news?page=1&size=20")
    data = resp.json()
    assert len(data["data"]["items"]) == 20
    assert data["data"]["total"] == 25

    resp = client.get("/api/news?page=2&size=20")
    data = resp.json()
    assert len(data["data"]["items"]) == 5
