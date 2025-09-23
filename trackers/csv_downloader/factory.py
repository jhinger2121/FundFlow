import logging
from .yieldmax_scraper import YieldMaxScraper
from .defiance_scraper import DefianceScraper

logger = logging.getLogger(__name__)

class FactoryScraper:
    @staticmethod
    def get_scraper(company):
        scrapers = {
            "YieldMax": YieldMaxScraper,
            "Defiance": DefianceScraper
        }
        scraper_class = scrapers.get(company)
        if scraper_class:
            return scraper_class()
        else:
            logger.warning(f"Scraper for {company} not found.")
            raise ValueError(f"Scraper for {company} not found.")