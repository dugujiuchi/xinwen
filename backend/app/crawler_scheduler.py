"""爬虫调度器 —— 独立进程运行，定时触发爬虫"""
import logging
import time

from apscheduler.schedulers.background import BackgroundScheduler

from app.crawlers.manager import CrawlerManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("crawler.scheduler")

manager = CrawlerManager()


def crawl_job():
    logger.info("开始定时爬取...")
    manager.run_all()
    logger.info("爬取完成")


crawl_job()

scheduler = BackgroundScheduler()
scheduler.add_job(crawl_job, "interval", hours=4)
scheduler.add_job(crawl_job, "cron", hour=9, minute=10)
scheduler.start()

logger.info("爬虫调度器已启动")
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    scheduler.shutdown()
