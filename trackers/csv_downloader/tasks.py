from celery import shared_task
from .factory import FactoryScraper

from trackers.models import Company
import logging

logger = logging.getLogger(__name__)

# @shared_task
# def download_daily_trades():
#     for company in ["Defiance", "YieldMax"]:
#         scraper = FactoryScraper.get_scraper(company)
#         scraper.download()

@shared_task
def download_daily_trades():
    try:
        for company in ["Defiance", "YieldMax"]:
            scraper = FactoryScraper.get_scraper(company)
            scraper.download()
        logger.info("Downloaded daily trades successfully.")
        return "Download complete"
    except Exception as e:
        logger.error(f"Failed to download trades: {e}", exc_info=True)
        return "Download failed"
