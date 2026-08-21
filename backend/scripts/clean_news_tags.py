"""清理搜索引擎原始标签（垃圾标签）。

背景：CSDN 搜索类数据源曾配置 mapping.tags="search_tag"，导致新闻携带
CSDN 博客作者的原始标签（如 @keyframes、CSS属性、HTTP 等），与资讯策展
无关且大量涌入前端标签栏。

本脚本：对所有 config.mapping.tags == "search_tag" 的数据源，将其新闻
的 tags 重置为数据源显示名（与其他来源的标签口径一致）。

用法（容器）:
    docker exec news-api python -m scripts.clean_news_tags            # 预演
    docker exec news-api python -m scripts.clean_news_tags --apply    # 执行

用法（本地）:
    cd backend && python -m scripts.clean_news_tags --apply
"""
import argparse

from app.database import SessionLocal
from app.models.news import News
from app.models.source import Source

MARKER = "search_tag"

# 历史上配置过 mapping.tags="search_tag" 的源显示名（种子已移除该配置，
# 靠名单兜底识别，保证脚本在任何部署时序下都能清理到存量数据）
LEGACY_SOURCE_NAMES = ("CSDN搜索(Clip)", "CSDN搜索(图像检测)")


def find_targets(db):
    """找出当前仍配置 search_tag 的源 + 历史遗留源（按显示名匹配）。"""
    sources = db.query(Source).all()
    by_name = {s.display_name: s for s in sources}
    targets = [
        s
        for s in sources
        if (s.config or {}).get("mapping", {}).get("tags") == MARKER
    ]
    for name in LEGACY_SOURCE_NAMES:
        s = by_name.get(name)
        if s is not None and s not in targets:
            targets.append(s)
    return targets


def main() -> None:
    parser = argparse.ArgumentParser(description="重置搜索引擎原始标签为数据源显示名")
    parser.add_argument("--apply", action="store_true", help="实际执行（默认仅预演）")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        targets = find_targets(db)
        if not targets:
            print("未找到 mapping.tags='search_tag' 的数据源，无需处理")
            return

        names = [s.display_name for s in targets]
        total = db.query(News).filter(News.source_name.in_(names)).count()
        print(f"目标数据源: {names}")
        print(f"涉及新闻行: {total}")

        if not args.apply:
            print("预演模式：加 --apply 实际执行")
            return

        updated = 0
        for s in targets:
            updated += (
                db.query(News)
                .filter(News.source_name == s.display_name, News.tags != s.display_name)
                .update({"tags": s.display_name}, synchronize_session=False)
            )
        db.commit()
        print(f"已重置 {updated} 行新闻的 tags 为数据源显示名")
    finally:
        db.close()


if __name__ == "__main__":
    main()
