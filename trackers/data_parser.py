from abc import ABC, abstractmethod
from string import digits
from datetime import datetime
import csv
import logging, traceback
from .models import Fund, Option, Trade, UnderlyingAsset, Position
# from .parser.yieldmax import YieldMaxParser
# from .parser.defiance import DefianceParser
from django.db import transaction
# Set up logging
logger = logging.getLogger(__name__)

# Context class
class TransactionProcessor:
    def __init__(self, parser):
        self.parser = parser

    def process(self, file_path):
        return self.parser.parse_csv(file_path)
    
class ParserFactory:
    @staticmethod
    def get_parser(company_name):
        if company_name == "YieldMax":
            return YieldMaxParser()
        elif company_name == "Defiance":
            return DefianceParser()
        else:
            raise ValueError(f"No parser available for {company_name}")
