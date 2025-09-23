from abc import ABC, abstractmethod
import pandas as pd
from datetime import datetime, date
from decimal import Decimal
from trackers.models import Fund, Option, Trade, Position, UnderlyingAsset, BrokerAccount, Holding
from trackers.utils import update_fund_summary
# read file and saving to DB is same process for all brokers(WS, IBKR...)
class base_parser(ABC):
    def __init__(self, file_path, user):
        self.file_path = file_path
        self.user = user

    def save_to_db(self, row, parsed):
        quantity = int(float(row["Quantity"]))
        price = Decimal(row["TradePrice"])
        if isinstance(row["DateTime"], pd.Timestamp):
            trade_date = row["DateTime"].to_pydatetime()
        else:
            trade_date = datetime.strptime(str(row["DateTime"]), "%Y-%m-%d %H:%M:%S")

        commission = abs(Decimal(row["CommFee"]))
        proceeds = float(row["Proceeds"])
        total_price = abs(proceeds)

        trade_type = "S" if quantity < 0 else "B"

        # Broker
        broker, broker_created = BrokerAccount.objects.get_or_create(user=self.user, broker_name="IBKR")
        # Fund
        fund, fund_created = Fund.objects.get_or_create(name=parsed["underlying_asset"], broker_account=broker)
        
        underlying_asset, assest_created = UnderlyingAsset.objects.get_or_create(name=parsed["underlying_asset"])

        # Get or create Option
        option, option_created = Option.objects.get_or_create(
            ticker=parsed["ticker"],
            fund = fund,
            defaults={
                "type": parsed["option_type"],
                "strike_price": Decimal(parsed["strike"]),
                "expiration_date": parsed["expiry"],
                "underlying_asset": underlying_asset
            }
        )

        # Save Trade
        trade, trade_created = Trade.objects.get_or_create(
            option=option,
            trade_type=trade_type,
            quantity=abs(quantity),
            price=price,
            date=trade_date,
            commission=commission,
        )
        if trade_created:
            # profit summary for the fund
            update_fund_summary(fund, trade.date, trade.total_price)
            # total profit for the fund
            fund.total_profit += trade.total_price
        
            # Get or create Position
            position = Position.objects.process_trade(fund, option, trade)
            trade.position = position
            trade.save()

    def read_file(self):
        # Step 1: Find the Trades header line + start index
        with open(self.file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        start_idx = None
        for i, line in enumerate(lines):
            if line.startswith("Trades,Header"):   # IBKR marks header this way
                start_idx = i
                break

        if start_idx is None:
            raise ValueError("Could not find 'Trades' section in file")

        # Step 2: Re-read only from that point forward
        trades_df = pd.read_csv(
            self.file_path,
            skiprows=start_idx,   # skip everything before Trades
            engine="python"
        )

        # Step 3: Clean up — drop any trailing summary rows
        trades_df = trades_df[trades_df["Trades"] == "Trades"].copy()

        # Step 4: Rename columns (they should now match expected count)
        trades_df.columns = [
            "Section", "Type", "OrderType", "AssetCategory", "Currency", "Symbol",
            "DateTime", "Quantity", "TradePrice", "ClosePrice", "Proceeds",
            "CommFee", "Basis", "RealizedPL", "MTMPL", "Code"
        ]

        # Convert numeric + datetime
        numeric_cols = ["Quantity", "TradePrice", "ClosePrice", "Proceeds",
                        "CommFee", "Basis", "RealizedPL", "MTMPL"]
        for col in numeric_cols:
            trades_df[col] = pd.to_numeric(trades_df[col], errors="coerce")

        trades_df["DateTime"] = pd.to_datetime(trades_df["DateTime"], errors="coerce")

        return trades_df

    @abstractmethod
    def parse_cvs(self):
        pass

    @abstractmethod
    def parse_and_save(self):
        pass

class IBKR_parser(base_parser):
    MONTHS = {
        'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4,
        'MAY': 5, 'JUN': 6, 'JUL': 7, 'AUG': 8,
        'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
    }
    def parse_cvs(self):
        pass
    def parse_and_save(self):
        trades = self.read_file()
        for _, row in trades.iterrows():   # iterate rows
            _row = row.to_dict()
            print(row.to_dict(), _row["Symbol"])
            if _row["Type"] == "Data":
                if _row["AssetCategory"] == 'Equity and Index Options' and len(_row["Symbol"]) > 12:
                    # save to options
                    parsed_data = self.parse_option_string(_row["Symbol"])
                    self.save_to_db(_row, parsed_data)
                elif _row["AssetCategory"] == 'Stocks':
                    # Save to Holdings only
                    self.save_holdings(_row)
            else:
                pass
    def save_holdings(self, row):
        broker, broker_created = BrokerAccount.objects.get_or_create(user=self.user, broker_name="IBKR")
        fund, fund_created = Fund.objects.get_or_create(name=row["Symbol"], broker_account=broker)
        underlying_asset, assest_created = UnderlyingAsset.objects.get_or_create(name=row["Symbol"])

        quantity = int(float(row["Quantity"]))
        price = Decimal(row["TradePrice"])

        # Try to find existing holding
        holding, created = Holding.objects.get_or_create(
            broker_account=broker,
            fund=fund, asset=underlying_asset,
            defaults={'quantity': 0, 'average_price': 0, 'total_cost': 0}
        )

        if quantity < 0:
            holding.sell(abs(quantity), price)
        else:
            holding.update_holding(quantity, price)

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

        expiry = date(2000 + year, month, day)
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

class WS_parser(base_parser):
    def parse_cvs(self):
        pass
    def parse_and_save(self):
        pass


class ParserFactory:
    @staticmethod
    def get_parser(broker_name, filepath, user):
        if broker_name == "WS":
            return WS_parser(filepath, user)
        elif broker_name == "IBKR":
            return IBKR_parser(filepath, user)
        else:
            print(f"NO broker exists with the given name {broker_name}")
            return None