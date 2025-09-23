import datetime
from decimal import Decimal
from trackers.models import Fund, Option, Trade, Position, UnderlyingAsset, BrokerAccount
from trackers.utils import update_fund_summary

class OptionSaver:
    def __init__(self, user):
        self.user = user

    def save(self, row, parsed):
        quantity = int(float(row["Quantity"]))
        price = Decimal(row["T. Price"])
        trade_date = datetime.datetime.strptime(row["Date/Time"], "%Y-%m-%d, %H:%M:%S")
        commission = abs(Decimal(row["Comm/Fee"]))
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
            defaults={
                "fund": fund,
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

        # profit summary for the fund
        update_fund_summary(fund, trade.date, trade.total_price)
        # total profit for the fund
        fund.total_profit += trade.total_price
        if trade_created:
            # Get or create Position
            position = Position.objects.process_trade(fund, option, trade)
            trade.position = position
            trade.save()
