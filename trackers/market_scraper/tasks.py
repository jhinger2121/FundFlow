import logging
from .scrape_stock_info import Symbol
from celery import shared_task

from trackers.models import UnderlyingAsset, Option
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def unique_tickers():
    return UnderlyingAsset.objects.values_list('yahoo_ticker', flat=True).distinct()


class StockInformation:
    def __init__(self):
        self.stock_data = None

    def get_symbol_data(self, stock_obj):
        """Fetch data for a single stock symbol."""
        try:
            symbol = Symbol(stock_obj)
            stock_name = symbol.get_stock_name()

            dividend_info = symbol.get_dividends_info() or {}
            close_n_current_price = symbol.get_current_or_close_price()

            price = close_n_current_price.get('price')
            avg_price = close_n_current_price.get('avg_price')

            dividend = dividend_info.get("dividend")
            pay_period = dividend_info.get("pay_period")

            stock_yield = symbol.get_stock_yield(price, pay_period, dividend)

            return {
                "name": stock_name,
                "price": price,
                "avg_price": avg_price,
                "dividend": dividend,
                "pay_period": pay_period,
                "yield": stock_yield,
                "ex_date": dividend_info.get("ex_dividend_date")
            }

        except Exception as e:
            logger.error(f"Error fetching data for symbol {stock_obj}: {e}", exc_info=True)
            return None

    def extract_data(self):
        symbols = [UnderlyingAsset.objects.filter(yahoo_ticker='TSLL')[:1][0], UnderlyingAsset.objects.filter(yahoo_ticker='TSLA')[:1][0]]
        data = {}

        for stock_obj in symbols:
            logger.info(f"Processing {stock_obj}")
            stock_data = self.get_symbol_data(stock_obj.yahoo_ticker)
            if stock_data:
                data[stock_obj] = stock_data
                logger.info(
                    f"{stock_obj}: {stock_data['name']}, Price: {stock_data['price']}, "
                    f"Avg: {stock_data['avg_price']}, Dividend: {stock_data['dividend']}, "
                    f"Yield: {stock_data['yield']}%, Ex-Date: {stock_data['ex_date']}, "
                    f"Pay Period: {stock_data['pay_period']}"
                )

        return data

    def update_stock_info(self):
        logger.info("Updating stock information...")
        self.stock_data = self.extract_data()
        if self.stock_data:
            logger.info("Stock information updated successfully.")
        else:
            logger.warning("No stock information found.")

    def reset_data(self):
        logger.info("Resetting stock data...")
        self.stock_data = None
        logger.info("Stock data reset successfully.")


    def update_underline_models(self):
        if self.stock_data:
            logger.info("Updating stock prices...")
            for underline_models_obj, details in self.stock_data.items():
                # Update stock price
                print("!!!!!!!!!!!!! updating", underline_models_obj, details)
                underline_models_obj.update_info(details['price'], details['name'])
            logger.info("Stock prices updated successfully.")
        else:
            logger.warning("No data found to update prices.")

    def update_option_models(self):
        if self.stock_data:
            logger.info("Updating stock distribution...")
            for fund_object, details in self.stock_data.items():
                print('fund!!!!!!!!!!', fund_object)
                try:
                    options = Option.objects.filter(underlying_asset=fund_object)
                    for option in options:
                        option.update_current_price(details['price'])

                except Option.DoesNotExist:
                    print("Model does not exist.")
                # update_distribution(
                #     stock_obj, details['dividend'], details['ex_date'],
                #     details['yield'], details['pay_period'], details['name']
                # )
            logger.info("Stock distribution updated successfully.")
        else:
            logger.warning("No data found to update distribution.")


stock = StockInformation()
def get_data():
    stock.update_stock_info()

def reset_data():
    stock.reset_data()
    print(stock.stock_data)

def update_underline_models():
    stock.update_underline_models()

def update_option_models():
    stock.update_option_models()


@shared_task
def update_trade_prices(_=None):
    try:
        stock = StockInformation()
        stock.update_stock_info()
        stock.update_option_models()
        logger.info("Updated trade prices successfully.")
        return "Trade prices updated"
    except Exception as e:
        logger.error(f"Failed to update trade prices: {e}", exc_info=True)
        return "Update failed"

