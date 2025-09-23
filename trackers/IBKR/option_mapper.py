import csv
import datetime
from django.db import transaction

class OptionMapper:
    MONTHS = {
        'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4,
        'MAY': 5, 'JUN': 6, 'JUL': 7, 'AUG': 8,
        'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
    }

    def parse_option_string(self, option_str):
        parts = option_str.strip().split()
        if len(parts) != 4:
            raise ValueError(f"Unexpected format: {option_str}")

        symbol, date_str, strike_str, type_char = parts
        day = int(date_str[:2])
        month_str = date_str[2:5].upper()
        year = int(date_str[5:])
        month = self.MONTHS.get(month_str)
        if not month:
            raise ValueError(f"Invalid month: {month_str}")

        expiry = datetime.date(2000 + year, month, day)
        expiry_str = expiry.strftime("%y%m%d")
        strike = float(strike_str)
        strike_formatted = f"{int(strike * 1000):08d}"

        option_type = type_char.upper()
        if option_type not in ['C', 'P']:
            raise ValueError(f"Invalid option type: {option_type}")

        full_ticker = f"{symbol.upper()} {expiry_str}{option_type}{strike_formatted}"

        return {
            "ticker": full_ticker,
            "expiry": expiry,
            "option_type": option_type,
            "underlying_asset": symbol.upper(),
            "strike": strike,
        }

    def map_row_to_model(self, row):
        info = self.parse_option_string(row["symbol"])
        return {
            "symbol": info["underlying_asset"],
            "ticker": info["ticker"],
            "expiry": info["expiry"],
            "option_type": info["option_type"],
            "strike": info["strike"]
        }
    

# data need to save the row
### FUND models
    # name, description, user

### Option Models
#   ticker(there is funcation called generat ticker)
#   fund (model instance)
#   type (c, p)
#   strike_price
#   underlying_assest
# 
### Trade Models
#   position(model instance)
#   option(model instance)
#   trade_type(B, S, SS, BC)
#   quantity
#   price(per unit ex. .80cent)
#   date(use trade date here)
#   commission
# 
### Position Models
#   Option(model instance)
#   fund(model instance)
#   remaining_quantity
#   average_price
#   profit_loss (use trade.total_price)
#   trade_type(B, S, SS, BC)
#   date(trade date)
#   commission 