import yfinance as yf
import pandas as pd
from datetime import datetime, timezone, timedelta
import logging, time

from requests import Session
from requests_cache import CacheMixin, SQLiteCache
from requests_ratelimiter import LimiterMixin, MemoryQueueBucket
from pyrate_limiter import Duration, RequestRate, Limiter

class CachedLimiterSession(CacheMixin, LimiterMixin, Session):
    pass

session = CachedLimiterSession(
    limiter=Limiter(RequestRate(2, Duration.SECOND*15)),  # max 2 requests per 5 seconds
    bucket_class=MemoryQueueBucket,
    backend=SQLiteCache("yfinance.cache"),
)


class Symbol:
    def __init__(self, symbol):
        self.session = session
        self.symbol = symbol
        self.symbol_data = None
        self.stock_information = None

    def fetch_symbol_data(self):
        if not self.symbol_data:
            logging.info("Fetching data from server for symbol: %s", self.symbol)
            time.sleep(3)
            self.symbol_data = yf.Ticker(self.symbol)
        return self.symbol_data

    def get_ticker_information(self):
        if not self.stock_information:
            self.fetch_symbol_data()
            self.stock_information = self.symbol_data.info
            logging.info("Stock information: %s", self.stock_information)
        return self.stock_information
    
    def get_stock_name(self):
        info = self.get_ticker_information()
        return info.get('longName') or info.get('shortName', '')
    
    def stock_summary(self):
        info = self.get_ticker_information()
        return info.get('longBusinessSummary', '')
    
    def get_history(self, period="1mo"):
        symbol_data = self.fetch_symbol_data()
        hist = symbol_data.history(period=period)
        logging.info("Historical data for %s: %s", self.symbol, hist)
        return hist

    def get_dividends_info(self):
        self.fetch_symbol_data()
        actions = self.symbol_data.dividends
        print("actions:", actions)
        
        if actions.empty:
            return None
        
        # Calculate time differences between all dividends
        diffs = actions.index.to_series().diff().dropna().dt.days

        if diffs.empty:
            return None

        # Get the most common interval in days
        common_interval = diffs.mode()[0]

        # Determine the pay period based on the most common interval
        if common_interval <= 10:
            pay_period = "weekly"
        elif common_interval <= 35:
            pay_period = "monthly"
        elif common_interval <= 95:
            pay_period = "quarterly"
        else:
            pay_period = "irregular"

        # Get the latest dividend info
        last_dividend_date = actions.index[-1]
        last_dividend = actions.iloc[-1]
        
        return {
            "ex_dividend_date": last_dividend_date,
            "dividend": last_dividend,
            "pay_period": pay_period
        }

    
    def get_price(self):
        info = self.get_ticker_information()
        return info.get('currentPrice') or info.get('previousClose')

    def get_stock_yield(self, price, pay_period, dividend):
        if not (price and dividend and pay_period):
            return 0
        
        s_yield = self.get_stock_dividend_yield()
        if s_yield:
            return s_yield

        annual_dividend = dividend * (12 if pay_period == "monthly" else 4)
        return round((annual_dividend / price) * 100, 2)
    
    def get_all_stock_info(self):
        return self.symbol_data
    
    #last ex-dividend date
    def get_ex_dividend_date(self):
        ex_div_date = self._get_info_value('exDividendDate')
        if ex_div_date:
            return pd.to_datetime(ex_div_date, format="%Y-%m-%d")
        return None
    
    def _get_info_value(self, key):
        info = self.get_ticker_information()
        return info.get(key)
    
    def lastDividendValue(self):
        return self.is_value_exist('lastDividendValue')
    
    def get_stock_dividend_yield(self):
        info = self.get_ticker_information()
        return info.get('dividendYield')
    
    def get_current_or_close_price(self):
        self.fetch_symbol_data()
        now = datetime.now(timezone.utc)
        hist = self.symbol_data.history(period="1d", interval="1m")  # Minute-level granularity

        if hist.empty:
            return {"price": None, "avg_price": None, "source": "no_data"}

        hist = hist.tz_convert("US/Eastern")  # Assuming market in NY time
        last_price = hist["Close"].iloc[-1]
        avg_price = hist["Close"].mean()

        market_close_time = now.replace(hour=20, minute=0, second=0, microsecond=0)  # 4 PM Eastern in UTC

        if now >= market_close_time:
            source = "close"
            price = hist["Close"].asof(market_close_time)
        else:
            source = "live"
            price = last_price

        return {
            "price": round(price, 2),
            "avg_price": round(avg_price, 2),
            "source": source
        }


    def get_dividend_dates(self):
        """
        Returns the ex-dividend date (if upcoming) and the most recent dividend pay date.
        """
        self.fetch_symbol_data()

        # Ex-dividend date (from .calendar)
        try:
            calendar = self.symbol_data.calendar
            ex_div_date = calendar.loc['Ex-Dividend Date'][0] if 'Ex-Dividend Date' in calendar.index else None
        except Exception as e:
            logging.error(f"Failed to fetch ex-dividend date for {self.symbol}: {e}", exc_info=True)
            ex_div_date = None

        # Most recent pay date (from .dividends)
        try:
            dividends = self.symbol_data.dividends
            if not dividends.empty:
                last_pay_date = dividends.index[-1]
                last_dividend = dividends.iloc[-1]
            else:
                last_pay_date = None
                last_dividend = None
        except Exception as e:
            logging.error(f"Failed to fetch dividend history for {self.symbol}: {e}", exc_info=True)
            last_pay_date = None
            last_dividend = None

        return {
            "ex_dividend_date": ex_div_date,
            "last_pay_date": last_pay_date,
            "last_dividend": last_dividend
        }

