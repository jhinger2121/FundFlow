from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
import csv, os, logging, re

from django.conf import settings

from trackers.utils import get_weekly_folder

logger = logging.getLogger(__name__)


class FileManagerStrategy(ABC):
    @abstractmethod
    def get_file_path(self):
        pass

class YieldMaxFileManager(FileManagerStrategy):    
    def __init__(self):
        weekly_folder = get_weekly_folder()  # Get current weekly folder (YYYY-WW format)
        print("Weekly folder:", weekly_folder)

        self.path = settings.MEDIA_ROOT / 'excel_files' / 'YieldMax' / weekly_folder
        self.path.mkdir(parents=True, exist_ok=True)  # Ensure the folder exists

    def get_file_path(self):
        csv_files = list(self.path.glob("*.csv"))
        print('cav file got!!!!!!!!', csv_files)
        if not csv_files:
            return None  # No CSV files found in the weekly folder

        # Sort files based on extracted date from filename
        latest_file = max(csv_files, default=None) # key=self.extract_date_from_filename,  use this funcation for date wise to pick it up
        return latest_file
    
    def get_earliest_weekly_folder(self):
        """
        Find the earliest available weekly folder.
        If the current week is unavailable, find the earliest available week, even in past years.
        """
        all_folders = sorted(self.base_path.glob("202*-W*"))  # Match YYYY-WWW pattern
        all_folders = [folder.name for folder in all_folders]

        if not all_folders:
            logger.error("No weekly folders found. Using the default week.")
            return datetime.now().strftime("%Y-W%W")  # Default to the current week

        return all_folders[0]  # Earliest available week
    
    @staticmethod
    def extract_date_from_filename(file_path):
        """
        Extract date from filename in the format 'Defiance-IntraDay_YYYY_MM_DD.csv'
        and return as a datetime object for sorting.
        """
        match = re.search(r"(\d{4})_(\d{2})_(\d{2})", file_path.name)
        if match:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        return datetime.min  # Default to the earliest possible date if no match
    
    # def get_latest_week_folder(self):
    #     """Find the most recent weekly folder (YYYY-WW format)"""
    #     week_folders = [f for f in self.base_path.iterdir() if f.is_dir() and self.is_valid_week_format(f.name)]
    #     return max(week_folders, key=os.path.getctime, default=None)

    # @staticmethod
    # def is_valid_week_format(folder_name):
    #     """Check if folder follows 'YYYY-WW' format."""
    #     try:
    #         year, week = folder_name.split("-W")
    #         datetime.strptime(f"{year} {week} 1", "%Y %W %w")  # Validate format
    #         return True
    #     except ValueError:
    #         return False

class DefianceFileManager(FileManagerStrategy):
    def __init__(self):
        weekly_folder = get_weekly_folder()  # Get current weekly folder (YYYY-WW format)
        print("Weekly folder:", weekly_folder)

        self.path = settings.MEDIA_ROOT / 'excel_files' / 'Defiance' / weekly_folder
        self.path.mkdir(parents=True, exist_ok=True)  # Ensure the folder exists

    def get_file_path(self):
        csv_files = list(self.path.glob("Defiance-IntraDay_*.csv"))
        if not csv_files:
            return None  # No CSV files found in the weekly folder

        # Sort files based on extracted date from filename
        latest_file = max(csv_files, key=self.extract_date_from_filename, default=None)
        return latest_file
    
    def get_earliest_weekly_folder(self):
        """
        Find the earliest available weekly folder.
        If the current week is unavailable, find the earliest available week, even in past years.
        """
        all_folders = sorted(self.base_path.glob("202*-W*"))  # Match YYYY-WWW pattern
        all_folders = [folder.name for folder in all_folders]

        if not all_folders:
            logger.error("No weekly folders found. Using the default week.")
            return datetime.now().strftime("%Y-W%W")  # Default to the current week

        return all_folders[0]  # Earliest available week


    @staticmethod
    def extract_date_from_filename(file_path):
        """
        Extract date from filename in the format 'Defiance-IntraDay_YYYY_MM_DD.csv'
        and return as a datetime object for sorting.
        """
        match = re.search(r"(\d{4})_(\d{2})_(\d{2})", file_path.name)
        if match:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        return datetime.min  # Default to the earliest possible date if no match

class FileManagerFactory:
    @staticmethod
    def get_file_manager(company_name):
        if company_name == "YieldMax":
            return YieldMaxFileManager()
        elif company_name == "Defiance":
            return DefianceFileManager()
        else:
            raise ValueError(f"Unsupported company: {company_name}")
    # @staticmethod
    # def read_csv(self, company_name):
    #     """
    #     Open the file and yield rows for processing.
    #     """
    #     file_path = self.get_file_manager(company_name)
    #     try:
    #         with open(file_path, newline='', encoding="utf-8") as csvfile:
    #             reader = csv.DictReader(csvfile)
    #             return reader
    #             for row in reader:
    #                 yield row
    #     except Exception as e:
    #         logger.error(f"Failed to read CSV file at {file_path}: {e}")
    #         raise
