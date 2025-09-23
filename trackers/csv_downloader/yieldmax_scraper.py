import os
import time
import logging
import requests
from datetime import datetime
from django.conf import settings

from trackers.utils import get_weekly_folder

logger = logging.getLogger(__name__)

class YieldMaxScraper:
    def __init__(self):
        self.company_name = "YieldMax"
        self.weekly_folder = get_weekly_folder()
        self.csv_download_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT28cQMYy4k0UD9DbpVVeg2EDIDNCurCeqenrDZfX849izXsk0sBGC1yfDKOeIkre0Ec9hRQ0i1Q_jn/pub?gid=0&single=true&output=csv"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.base_path = settings.MEDIA_ROOT / 'excel_files' / 'YieldMax' / self.weekly_folder

        # Ensure the directory exists
        os.makedirs(self.base_path, exist_ok=True)

        # Define full file path
        self.file_path = self.base_path / f"{self.company_name}_IntraDay_{datetime.today().strftime('%Y_%m_%d')}.csv"

    def download(self):
        try:
            logger.info(f"Starting download from {self.csv_download_url} for {self.company_name}")

            response = requests.get(self.csv_download_url, headers=self.headers, allow_redirects=True)
            time.sleep(3)
            if response.status_code == 200:
                with open(self.file_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"File successfully saved: {self.file_path}")
            else:
                logger.error(f"Failed to download {self.company_name} file. Status Code: {response.status_code}")

        except Exception as e:
            logger.exception(f"Error occurred while downloading {self.company_name} file: {e}")
