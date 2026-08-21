"""爬虫调度器 —— 独立进程运行，定时触发爬虫

调度策略：
- 每 4 小时执行一次（interval）
- 每天 09:10 额外执行一次（cron）
- 启动时通过 run_date 立即触发首次抓取（不阻塞调度器启动）
- misfire_grace_time=900s：错过 15 分钟内仍可追补
- coalesce=True：多个积压任务仅执行最新一个
- max_instances=2：允许一个新实例启动时将旧实例标记为超时（依赖 manager 层的超时保护）
"""
import logging
import time
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from app.crawlers.manager import CrawlerManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("crawler.scheduler")

manager = CrawlerManager()

# 单次抓取最长耗时（秒），超过此时间认为异常
JOB_TIMEOUT_SECONDS = 3.5 * 3600  # 3.5 小时，留 0.5 小时 buffer


def crawl_job():
    """定时爬取任务 —— 带总超时保护。"""
    logger.info("开始定时爬取...")
    try:
        manager.run_all(timeout_seconds=JOB_TIMEOUT_SECONDS)
    except Exception:
        logger.exception("爬取过程异常")
    logger.info("本轮爬取结束")


# 使用 BackgroundScheduler 标准配置
scheduler = BackgroundScheduler(
    timezone="Asia/Shanghai",
    job_defaults={
        "coalesce": True,          # 积压多个时仅执行最新
        "max_instances": 2,        # 允许新实例启动（超时保护依赖 manager 层）
        "misfire_grace_time": 900, # 错过 15 分钟内仍可触发
    },
)

# 每 4 小时定时执行
scheduler.add_job(
    crawl_job,
    "interval",
    hours=4,
    id="crawl_job_interval",
    next_run_time=datetime.now(timezone(timedelta(hours=8))),
)

# 每天 09:10 补充执行
scheduler.add_job(
    crawl_job,
    "cron",
    hour=9,
    minute=10,
    id="crawl_job_cron",
    timezone="Asia/Shanghai",
)

scheduler.start()

# 启动后立即触发首次抓取（不阻塞，通过 scheduler 统一管理）
scheduler.add_job(
    crawl_job,
    "date",
    run_date=datetime.now(timezone(timedelta(hours=8))) + timedelta(seconds=5),
    id="crawl_job_startup",
    misfire_grace_time=30,
)

logger.info("爬虫调度器已启动（interval=4h, cron=09:10, startup=立即）")
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    scheduler.shutdown()
