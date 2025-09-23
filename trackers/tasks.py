import logging
import pandas as pd
from decimal import Decimal

import yfinance as yf
from datetime import date, datetime, timedelta
from celery import shared_task
from celery import chain

from django.db import models
from .models import Position, FundProfitSummary, Fund, Company, Option, UnderlyingAsset
from .file_manager import FileManagerFactory
from .data_parser import ParserFactory, TransactionProcessor
from .csv_downloader.tasks import download_daily_trades
from .market_scraper.tasks import update_trade_prices
logger = logging.getLogger(__name__)

@shared_task
def process_company_file(company_name='YieldMax'):
    try:
        # Get the appropriate file manager(YieldMax, Defiance,..etc)
        file_manager = FileManagerFactory.get_file_manager(company_name)
        file_path = file_manager.get_file_path()
        print(file_path, "SUccessfylly got link")
        
        parserFactory = ParserFactory()
        parser = parserFactory.get_parser(company_name)
        
        processor = TransactionProcessor(parser)
        processor.process(file_path)

        return f"Successfully processed {company_name}'s file."
    except Exception as e:
        return f"Failed to process {company_name}'s file: {e}"
    
@shared_task
def queue_file_processing(_=None):
    try:
        # Companies: YieldMax, Defiance
        companies = ["Defiance", "YieldMax"]  # Add all company names here
        for company in companies:
            process_company_file.delay(company)
        logger.info("Queued file processing tasks successfully.")
        return "Queued company file processing"
    except Exception as e:
        logger.error(f"Failed to queue file processing: {e}", exc_info=True)
        return "Queue failed"

@shared_task
def download_and_process_chain():
    chain(
        # download_daily_trades.s(),
        # queue_file_processing.s(),
        update_trade_prices.s()
    )()


from datetime import datetime, timedelta
from decimal import Decimal
import yfinance as yf

@shared_task
def update_option_and_underlying_price(option_id, underlying_id, trade_date_str):
    try:
        print("Inside the price update task")
        option = Option.objects.get(id=option_id)
        underlying = UnderlyingAsset.objects.get(id=underlying_id)
        symbol = underlying.name.upper()

        # Safe parsing, even if timezone present
        trade_datetime = datetime.fromisoformat(trade_date_str).replace(tzinfo=None)

        # Define 10-min window around trade time
        start_time = trade_datetime - timedelta(minutes=5)
        end_time = trade_datetime + timedelta(minutes=5)

        print("Start:", start_time, "End:", end_time)

        data = yf.download(
            symbol,
            start=start_time,
            end=end_time,
            interval="1m",
            auto_adjust=False,
            progress=False,
            prepost=True,  # include premarket if relevant
        )

        if data.empty:
            return f"No intraday data found for {symbol} at {trade_date_str}"
        
        data.index = pd.to_datetime(data.index)
        data.index = data.index.tz_convert("US/Eastern").tz_localize(None)


        timestamp = trade_datetime.replace(second=0, microsecond=0)

        # Find nearest available timestamp in data
        if timestamp in data.index:
            chosen_time = timestamp
        else:
            chosen_time = min(data.index, key=lambda x: abs(x - timestamp))

        # Check how far off it is
        delta = abs(chosen_time - timestamp)
        if delta > timedelta(minutes=1):
            print(f"⚠️ Closest time found is {delta} away from requested time {timestamp}")

        # Get close price
        close_series = data.loc[chosen_time]
        if isinstance(close_series, pd.Series) and 'Close' in close_series:
            close_price = close_series['Close']
            price_on_trade_time = Decimal(str(float(close_price)))

            option.price = price_on_trade_time
            option.save()

            return f"{symbol}: Closest price at {chosen_time} (delta: {delta}) was {price_on_trade_time}"


    except Exception as e:
        return f"Error updating prices: {e}"
