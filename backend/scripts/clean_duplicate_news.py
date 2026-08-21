"""清理历史重复新闻，并归一化存量 link。

背景：部分数据源（如 CSDN 搜索 API）返回的 link 带有 request_id 等
每次请求都变化的追踪参数，导致 link 唯一约束去重失效，数据库里
累积了大量"同一篇文章、不同 link"的重复新闻。

本脚本：
1. 按归一化 link（剥离追踪参数）对所有新闻分组
2. 每组仅保留最早一条（id 最小），删除其余重复行
3. 把保留行的 link 更新为归一化形式，使后续抓取能正确去重

用法（容器内）:
    docker compose run --rm api python -m scripts.clean_duplicate_news

用法（本地）:
    cd backend && python -m scripts.clean_duplicate_news
"""
from app.crawlers.base import BaseCrawler
from app.database import SessionLocal
from app.models.news import News


def main() -> None:
    db = SessionLocal()
    try:
        rows = db.query(News).order_by(News.id.asc()).all()
        print(f"当前 news 总行数: {len(rows)}")

        seen: dict[str, News] = {}
        dup_rows: list[News] = []
        need_update: list[tuple[News, str]] = []

        for row in rows:
            key = BaseCrawler.canonicalize_link(row.link or "")
            if key in seen:
                dup_rows.append(row)
            else:
                seen[key] = row
                if key and key != row.link:
                    need_update.append((row, key))

        # 先提交删除，再更新 link（避免 UPDATE 先于 DELETE 触发唯一约束冲突）
        for row in dup_rows:
            db.delete(row)
        db.flush()

        for row, key in need_update:
            row.link = key
        db.flush()

        db.commit()
        print(f"删除重复新闻 {len(dup_rows)} 条")
        print(f"归一化 link {len(need_update)} 条")
        print(f"清理后剩余 {len(rows) - len(dup_rows)} 条")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
