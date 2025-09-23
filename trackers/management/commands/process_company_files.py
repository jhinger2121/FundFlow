import logging
import traceback
from django.core.management.base import BaseCommand
from trackers.file_manager import FileManagerFactory
from trackers.parser.base_parser import BaseParser
from trackers.parser.yieldmax import YieldMaxParser
from trackers.parser.defiance import DefianceParser
from trackers.data_parser import ParserFactory

logger = logging.getLogger(__name__)

from datetime import date, datetime, timedelta
from django.db.models import Sum
from trackers.models import Company, Fund, CompanyProfitSummary, FundProfitSummary


# "Defiance",
COMPANIES = ["Defiance"]

class Command(BaseCommand):
    help = "Process all company files one by one, starting from the earliest files first"

    def handle(self, *args, **kwargs):
        for company_name in COMPANIES:
            self.stdout.write(self.style.SUCCESS(f"Processing files for {company_name}..."))

            try:
                file_manager = FileManagerFactory.get_file_manager(company_name)
                weekly_folders = sorted(file_manager.path.parent.glob("202*-W*"))

                if not weekly_folders:
                    self.stdout.write(self.style.WARNING(f"No weekly folders found for {company_name}. Skipping..."))
                    continue

                for weekly_folder in weekly_folders:
                    self.stdout.write(self.style.NOTICE(f"Processing weekly folder: {weekly_folder.name}"))

                    file_manager.path = weekly_folder
                    files = sorted(file_manager.path.glob("*.csv"), key=file_manager.extract_date_from_filename)

                    if not files:
                        self.stdout.write(self.style.WARNING(f"No files found in {weekly_folder.name}. Skipping..."))
                        continue

                    parser = ParserFactory().get_parser(company_name)
                    
                    for file_path in files:
                        self.stdout.write(self.style.NOTICE(f"Processing file: {file_path.name}"))
                        parser.parse_csv(file_path)
                        self.stdout.write(self.style.SUCCESS(f"Successfully processed {file_path.name}"))

            except Exception as e:
                logger.error(f"Failed to process files for {company_name}: {e}")
                logger.error(traceback.format_exc())

