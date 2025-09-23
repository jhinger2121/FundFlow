"""
Relationship Summary
    1. Fund to Option: A fund groups multiple options. For example, TSLY may trade many options on TSLA at different strike prices or expirations.
    2. Option to Trade: Each option can have multiple trades (buys, sells, etc.).
    3. Option to Position: Each option has at most one open position at a time per fund, but positions are updated as trades occur.
    4. Trade to Position: Trades impact positions by:
        4.1. Adding to open positions (Buy trades).
        4.2Reducing or closing open positions (Sell/Buy to Close trades).

How Each Model Contributes to the Workflow
    1. Fund: Groups data for high-level reporting.
    Example: Calculate total profit/loss for the TSLY fund.

    2. Option: Tracks details about the financial instrument being traded.
    Example: Track performance for a specific call option (TSLA 241025C00232500).

    3. Trade: Stores raw trade data, which is the foundation for calculating profits, updating positions, and generating reports.
    Example: A Buy trade for 500 contracts at $0.74 updates the position for the associated option.

    4. Position: Ensures the system knows how many contracts are still open and provides the state needed for real-time and historical calculations.
    Example: After selling 300 of 500 contracts, the position tracks the remaining 200 contracts.
"""
import datetime
import decimal
import math
from decimal import Decimal, ROUND_HALF_UP
from django.utils.timezone import now
from django.db import models
from django.db.models import Sum
from django.utils.text import slugify
from datetime import timedelta, date, datetime
from django.contrib.auth.models import User
from django.db.models import UniqueConstraint

from .parser.utils import get_week_range, get_month_range, get_year_range

class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


    def save_weekly_snapshot(self):
        """Save weekly profit snapshot on Sundays."""
        today = date.today()
        if today.weekday() == 6:  # Sunday
            CompanyProfitSummary.objects.create(
                company=self,
                start_date=today - timedelta(days=6),  # Last Monday
                end_date=today,
                weekly_profit=self.weekly_profit,
                monthly_profit=self.monthly_profit,
                annually_profit=self.annually_profit,
            )
            # Reset weekly profit for the new week
            self.weekly_profit = 0
            self.save()

    def save_monthly_snapshot(self):
        """Save monthly profit snapshot at the end of the month."""
        today = date.today()
        last_day_of_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        if today == last_day_of_month:
            CompanyProfitSummary.objects.create(
                company=self,
                start_date=today.replace(day=1),  # First day of the month
                end_date=today,
                weekly_profit=self.weekly_profit,
                monthly_profit=self.monthly_profit,
                annually_profit=self.annually_profit,
            )
            # Reset monthly profit
            self.monthly_profit = 0
            self.save()

    def save_annual_snapshot(self):
        """Save annual profit snapshot on December 31st."""
        today = date.today()
        if today.month == 12 and today.day == 31:
            CompanyProfitSummary.objects.create(
                company=self,
                start_date=today.replace(month=1, day=1),  # First day of the year
                end_date=today,
                weekly_profit=self.weekly_profit,
                monthly_profit=self.monthly_profit,
                annually_profit=self.annually_profit,
            )
            # Reset annual profit
            self.annually_profit = 0
            self.save()
    
    def get_current_week_summary(self):
        today = datetime.today()
        start, end = get_week_range(today)
        return self.company_profit_summaries.filter(start_date=start, end_date=end).first()

    def get_current_month_summary(self):
        today = datetime.today()
        start, end = get_month_range(today)
        return self.company_profit_summaries.filter(start_date=start, end_date=end).first()

    def get_current_year_summary(self):
        today = datetime.today()
        start, end = get_year_range(today)
        return self.company_profit_summaries.filter(start_date=start, end_date=end).first()

class CompanyProfitSummary(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="company_profit_summaries")
    start_date = models.DateField()
    end_date = models.DateField()

    weekly_profit = models.DecimalField(max_digits=12, decimal_places=2, default=decimal.Decimal('0.00'))
    monthly_profit = models.DecimalField(max_digits=12, decimal_places=2, default=decimal.Decimal('0.00'))
    annually_profit =  models.DecimalField(max_digits=12, decimal_places=2, default=decimal.Decimal('0.00'))

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profit Summary for {self.company.name} on {self.start_date} -- {self.end_date}"

    
class UnderlyingAsset(models.Model):
    name = models.CharField(max_length=255)  # e.g., "DG", "FDX", etc.
    yahoo_ticker = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True, null=True)  # Optional description
    live_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    live_price_updated_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Auto-fill yahoo_ticker if it's blank
        if not self.yahoo_ticker and self.name:
            self.yahoo_ticker = self.name.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    def update_info(self, price, description):
        self.description = description
        self.live_price = price
        self.live_price_updated_at = datetime.now()
        self.save()

class BrokerAccount(models.Model):
    BROKER_CHOICES = [
        ("IBKR", "Interactive Brokers"),
        ("QTRD", "Questrade"),
        ("WS", "Wealthsimple"),
    ]
    slug = models.SlugField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="broker_accounts")
    broker_name = models.CharField(max_length=20, choices=BROKER_CHOICES)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "broker_name") 
    
    def __str__(self):
        return f"{self.user.username} - {self.get_broker_name_display()}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.broker_name)
        super().save(*args, **kwargs)

class BrokerAccountProfitSummary(models.Model):
    broker = models.ForeignKey(BrokerAccount, on_delete=models.CASCADE, related_name="brokeraccount_profit_summaries")
    start_date = models.DateField()
    end_date = models.DateField()

    weekly_profit = models.DecimalField(max_digits=12, decimal_places=2, default=decimal.Decimal('0.00'))
    monthly_profit = models.DecimalField(max_digits=12, decimal_places=2, default=decimal.Decimal('0.00'))
    annually_profit =  models.DecimalField(max_digits=12, decimal_places=2, default=decimal.Decimal('0.00'))
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"BrokerAccount Summary for {self.broker.broker_name} on {self.start_date} -- {self.end_date}"

class Fund(models.Model):
    name = models.CharField(max_length=25)  # e.g., "ULTY"
    slug = models.SlugField(blank=True)
    description = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    # Optional: if user is not null, this is a user's personal fund
    # user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name="personal_funds")
    broker_account = models.ForeignKey(BrokerAccount, null=True, blank=True, on_delete=models.CASCADE, related_name="broker")
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.CASCADE, related_name="funds")

    total_profit = models.DecimalField(max_digits=15, decimal_places=2, default=decimal.Decimal('0.00'))

    class Meta:
        constraints = [
            UniqueConstraint(fields=['name', 'broker_account'], name='unique_fund_name_per_broker'),
            UniqueConstraint(fields=['name', 'company'], name='unique_fund_name_per_company'),
        ]

    def __str__(self):
        if self.company:
            return f"{self.company.name} - {self.name}"
        elif self.broker_account:
            return f"{self.broker_account.get_broker_name_display()} - {self.name}"
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def get_current_week_summary(self):
        today = datetime.today()
        start, end = get_week_range(today)
        return self.fund_profit_summaries.filter(start_date=start, end_date=end).first() or decimal.Decimal(0.0)
    @property
    def get_current_month_summary(self):
        today = datetime.today()
        start, end = get_month_range(today)
        return self.fund_profit_summaries.filter(start_date=start, end_date=end).first()
    @property
    def get_current_year_summary(self):
        today = datetime.today()
        start, end = get_year_range(today)
        return self.fund_profit_summaries.filter(start_date=start, end_date=end).first()
    @property
    def active_positions_count(self):
        return self.positions.filter(active=True).count()

    @classmethod
    def get_user_profit_summaries(cls, broker):
        today = now().date()
        week_start, week_end = get_week_range(today)
        month_start, month_end = get_month_range(today)
        year_start, year_end = get_year_range(today)

        funds = cls.objects.filter(broker_account=broker).prefetch_related('fund_profit_summaries')
        
        total_weekly = Decimal('0.00')
        total_monthly = Decimal('0.00')
        total_yearly = Decimal('0.00')
        total_all_time_options = Decimal('0.00')
        total_holding_profit_loss = Decimal('0.00')
        combined_total_all_time = Decimal('0.00')
        
        for fund in funds:
            total_all_time_options += fund.total_profit

            weekly = fund.fund_profit_summaries.filter(start_date=week_start, end_date=week_end).first()
            monthly = fund.fund_profit_summaries.filter(start_date=month_start, end_date=month_end).first()
            yearly = fund.fund_profit_summaries.filter(start_date=year_start, end_date=year_end).first()

            total_weekly += weekly.weekly_profit if weekly else Decimal('0.00')
            total_monthly += monthly.monthly_profit if monthly else Decimal('0.00')
            total_yearly += yearly.annually_profit if yearly else Decimal('0.00')

            # Add holding profit/loss
            for holding in fund.holdings.all():
                total_holding_profit_loss += holding.total_gain_loss

        combined_total_all_time = total_all_time_options + total_holding_profit_loss
        return {
            "weekly": total_weekly,
            "monthly": total_monthly,
            "yearly": total_yearly,
            "total_all_time_options": total_all_time_options,
            "holding_profit_loss": total_holding_profit_loss,
            "combined_total_all_time": combined_total_all_time,
            "name": broker.broker_name
        }

class FundProfitSummary(models.Model):
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name="fund_profit_summaries")
    start_date = models.DateField()
    end_date = models.DateField()

    weekly_profit = models.DecimalField(max_digits=12, decimal_places=2, default=decimal.Decimal('0.00'))
    monthly_profit = models.DecimalField(max_digits=12, decimal_places=2, default=decimal.Decimal('0.00'))
    annually_profit =  models.DecimalField(max_digits=12, decimal_places=2, default=decimal.Decimal('0.00'))
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profit Summary for {self.fund.name} on {self.start_date} -- {self.end_date}"
    
    def summaries(self):
        summaries = self.filter(fund=self.fund)
        
    

class Option(models.Model):
    ticker = models.CharField(max_length=255, unique=True)  # e.g., "TSLA 241025C00232500"
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name="options")
    type = models.CharField(
        max_length=3,
        choices=[("C", "Call"), ("P", "Put")],  # Option type: Call or Put
    )
    strike_price = models.DecimalField(max_digits=10, decimal_places=2)
    expiration_date = models.DateField()

    underlying_asset = models.ForeignKey(
        UnderlyingAsset, on_delete=models.CASCADE, related_name="options"
    )

    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_snapshot_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.ticker
    def update_current_price(self, price):
        self.price = price
        self.save()
    def regenerate_ticker(self):
        symbol = self.underlying_asset.name.upper()
        formatted_expiry = self.expiration_date.strftime("%y%m%d")
        type_code = self.type
        strike_formatted = f"{int(self.strike_price * 1000):08d}"
        self.ticker = f"{symbol}{formatted_expiry}{type_code}{strike_formatted}"
        self.save()

    @property
    def percent_out_of_money_at_snapshot(self):
        if self.price and self.strike_price:
            try:
                if self.type == "C":  # Call
                    percent = ((self.strike_price - self.price) / self.price) * 100
                else:  # Put
                    percent = ((self.price - self.strike_price) / self.price) * 100
                return math.floor(percent)
            except ZeroDivisionError:
                return None
        return None
    @property
    def percent_out_of_money_now(self):
        if self.underlying_asset and self.underlying_asset.live_price and self.strike_price:
            try:
                if self.type == "C":
                    return ((self.strike_price - self.underlying_asset.live_price) / self.underlying_asset.live_price) * 100
                else:
                    return ((self.underlying_asset.live_price - self.strike_price) / self.underlying_asset.live_price) * 100
            except ZeroDivisionError:
                return None
        return None

    @property
    def breakeven_price(self):
        trade = self.trades.first()
        if not trade:
            return None

        premium = trade.price  # price per share
        if self.type == "P":  # Put
            return self.strike_price - premium
        elif self.type == "C":  # Call
            return self.strike_price + premium
        return None
    
    @property
    def annual_yield(self):
        print(">> Calculating annual_yield for:", self.ticker)
        try:
            trades = self.trades.filter(trade_type__in=["S", "SS"]).order_by("date")
            if not trades.exists():
                print("No qualifying trades for yield.")
                return None

            first_trade = trades.first()
            days_held = (self.expiration_date - first_trade.date.date()).days

            if days_held <= 0:
                print("Invalid days_held:", days_held)
                return None

            total_credit = sum(t.total_price for t in trades)
            if total_credit <= 0:
                print("Invalid total_credit:", total_credit)
                return None

            # Use Decimal for all numeric literals
            annual_yield = (total_credit / Decimal("100")) * (Decimal("365") / Decimal(days_held)) * Decimal("100")
            return round(annual_yield, 2)

        except Exception as e:
            print("annual_yield error:", e)
            return None



class Trade(models.Model):
    TRADE_TYPES = [
        ("B", "Buy"),
        ("S", "Sell"),
        ("SS", "Short Sell"),
        ("BC", "Buy to Close"),
    ]
    position = models.ForeignKey('Position', on_delete=models.CASCADE, related_name='trades', blank=True, null=True)
    option = models.ForeignKey(Option, on_delete=models.CASCADE, related_name="trades")
    trade_type = models.CharField(max_length=2, choices=TRADE_TYPES)
    quantity = models.IntegerField()  # Positive for buys, negative for sells
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Per unit price
    total_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True)
    date = models.DateTimeField(blank=True, null=True)
    active = models.BooleanField(default=True)

    commission = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * (self.price * 100)
        if self.trade_type in ["B", "BC"]:  # Buy or Short Sell
            self.total_price = -self.total_price
        self.total_price -= self.commission
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.trade_type} {self.quantity} of {self.option.ticker}"

    @property
    def annual_yield(self):
        if self.trade_type not in ["S", "SS"]:  # Only for Sell or Short Sell
            return None

        # Calculate duration (including trade day)
        trade_day = self.date.date()
        expiry_day = self.option.expiration_date
        days_to_expiry = (expiry_day - trade_day).days  # include trade day

        # Ensure minimum 1 day duration
        if days_to_expiry <= 0:
            return None

        # Optional: add weekend buffer (if it's a short duration trade)
        if days_to_expiry < 7:
            days_to_expiry += 2  # simulate weekend
        else:
            days_to_expiry += 3

        # Premium and capital at risk
        premium_received = self.price * 100 * self.quantity
        capital_at_risk = self.option.strike_price * 100 * self.quantity

        if capital_at_risk == 0:
            return None

        # Annual yield formula
        days_decimal = Decimal("365") / Decimal(days_to_expiry)
        annual_yield = (premium_received / capital_at_risk) * days_decimal * Decimal("100")

        return annual_yield.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

class PositionManager(models.Manager):
    # @transaction.atomic
    def process_trade(self, fund, option, trade):
        """
        Process a trade and update or create a position accordingly.

        Args:
            trade (Trade): The trade instance to process.
        """
        # Fetch the existing position for the given option and fund
        position = self.filter(option=option, fund=fund, active=True).first()
        if trade.trade_type == "BC":
            # Get all active short positions sorted by oldest first (FIFO approach)
            positions = self.filter(option=option, fund=fund, active=True).order_by('date')

            if not positions:
                raise ValueError(f"No existing short position to close for {option}.")

            remaining_quantity_to_close = trade.quantity  # Track how much is left to close

            for position in positions:
                if remaining_quantity_to_close <= 0:
                    break  # We have closed all needed contracts

                # Determine how much we can close from this position
                closing_quantity = min(remaining_quantity_to_close, abs(position.remaining_quantity))

                # Calculate profit/loss
                proportional_total_price = Decimal((closing_quantity / trade.quantity)) * trade.total_price
                position.profit_loss += proportional_total_price

                # Trade.Position
                trade.position = position

                # Update remaining quantity
                position.remaining_quantity -= closing_quantity
                remaining_quantity_to_close -= closing_quantity

                # addint commission of trade 
                position.commission += trade.commission * abs(trade.quantity)

                # If position is fully closed, mark it inactive
                if position.remaining_quantity <= 0:
                    position.active = False

                position.save()

            # If after processing all positions, we still have contracts left to close, raise an error
            if remaining_quantity_to_close > 0:
                raise ValueError(f"Cannot close {trade.quantity}, only {trade.quantity - remaining_quantity_to_close} contracts available.")

            print(f"Successfully closed {trade.quantity} of {option}")
            
        elif trade.trade_type in ["S", "SS"]:
            # closing the position
            if position and not (position.trade_type in ["S", "SS"]):
                # Get all active short positions sorted by oldest first (FIFO approach)
                positions = self.filter(option=option, fund=fund, active=True).order_by('date')

                if not positions:
                    raise ValueError(f"No existing short position to close for {option}.")

                remaining_quantity_to_close = trade.quantity  # Track how much is left to close

                for position in positions:
                    if remaining_quantity_to_close <= 0:
                        break  # We have closed all needed contracts

                    # Determine how much we can close from this position
                    closing_quantity = min(remaining_quantity_to_close, abs(position.remaining_quantity))

                    # Calculate profit/loss
                    proportional_total_price = Decimal((closing_quantity / trade.quantity)) * trade.total_price
                    position.profit_loss += proportional_total_price

                    # Trade.Position
                    trade.position = position

                    # Update remaining quantity
                    position.remaining_quantity -= closing_quantity
                    remaining_quantity_to_close -= closing_quantity

                    # addint commission of trade 
                    position.commission += trade.commission * abs(trade.quantity)

                    # If position is fully closed, mark it inactive
                    if position.remaining_quantity == 0:
                        position.active = False

                    position.save()

                # If after processing all positions, we still have contracts left to close, raise an error
                if remaining_quantity_to_close > 0:
                    raise ValueError(f"Cannot close {trade.quantity}, only {trade.quantity - remaining_quantity_to_close} contracts available.")

                print(f"Successfully closed {trade.quantity} of {option}")
            else:
                # Create a new short position
                position = Position.objects.create(
                    option=option,
                    fund=fund,
                    remaining_quantity=abs(trade.quantity),  # Negative for short positions
                    average_price=trade.price,
                    profit_loss=trade.total_price,
                    trade_type=trade.trade_type,
                    date=trade.date,
                    commission=trade.commission * abs(trade.quantity),
                )
                        
        elif trade.trade_type == "B":
            # closing the position
            if position and not trade.trade_type == position.trade_type:
                # Get all active short positions sorted by oldest first (FIFO approach)
                positions = self.filter(option=option, fund=fund, active=True).order_by('date')

                if not positions:
                    raise ValueError(f"No existing short position to close for {option}.")

                remaining_quantity_to_close = trade.quantity  # Track how much is left to close

                for position in positions:
                    if remaining_quantity_to_close <= 0:
                        break  # We have closed all needed contracts

                    # Determine how much we can close from this position
                    closing_quantity = min(remaining_quantity_to_close, abs(position.remaining_quantity))

                    # Calculate profit/loss
                    proportional_total_price = Decimal((closing_quantity / trade.quantity)) * trade.total_price
                    position.profit_loss += proportional_total_price

                    # Trade.Position
                    trade.position = position

                    # Update remaining quantity
                    position.remaining_quantity -= closing_quantity
                    remaining_quantity_to_close -= closing_quantity

                    # addint commission of trade 
                    position.commission += trade.commission / abs(trade.quantity)

                    # If position is fully closed, mark it inactive
                    if position.remaining_quantity == 0:
                        position.active = False

                    position.save()

                # If after processing all positions, we still have contracts left to close, raise an error
                if remaining_quantity_to_close > 0:
                    raise ValueError(f"Cannot close {trade.quantity}, only {trade.quantity - remaining_quantity_to_close} contracts available.")

                print(f"Successfully closed {trade.quantity} of {option}")

            else:
                # Create a new short position
                position = Position.objects.create(
                    option=option,
                    fund=fund,
                    remaining_quantity=abs(trade.quantity),  # Negative for short positions
                    average_price=trade.price,
                    profit_loss=trade.total_price,
                    trade_type=trade.trade_type,
                    date=trade.date,
                    commission=trade.commission * abs(trade.quantity),
                )
        else:
            raise ValueError(f"Unsupported trade type: {trade.trade_type}")
        
        
        # Create a history entry after the position is saved
        PositionHistory.objects.create(
            position=position,
            date=trade.date,
            remaining_quantity=position.remaining_quantity,
            average_price=position.average_price,
            profit_loss=position.profit_loss,
        )
        return position
class Position(models.Model):
    TRADE_TYPES = [
        ("B", "Buy"),
        ("S", "Sell"),
        ("SS", "Short Sell"),
        ("BC", "Buy to Close"),
    ]

    option = models.ForeignKey(Option, on_delete=models.CASCADE, related_name="positions")
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name="positions")

    remaining_quantity = models.IntegerField()  # Tracks remaining open quantity
    average_price = models.DecimalField(max_digits=10, decimal_places=2)  # Weighted average
    profit_loss = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    trade_type = models.CharField(max_length=2, choices=TRADE_TYPES)
    date = models.DateField()
    active = models.BooleanField(default=True)
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    objects = PositionManager()
    def close_quantity(self, quantity, closing_price):
        if quantity > self.remaining_quantity:
            raise ValueError("Cannot close more than the remaining quantity.")
        # Calculate profit/loss for the closing quantity
        pnl = (closing_price - self.average_price) * quantity
        self.profit_loss += pnl
        self.remaining_quantity -= quantity
        self.save()
        return pnl

    def __str__(self):
        return f"{self.remaining_quantity} of {self.option.ticker} in {self.fund.name}"

    @property
    def annual_yield(self):
        trades = list(
            self.option.trades.filter(option__fund=self.fund).order_by("date")[:2]
        )

        if not trades:
            return None

        # Calculate duration (including trade day)
        trade_day = trades[0].date.date()
        expiry_day = self.option.expiration_date
        days_to_expiry = (expiry_day - trade_day).days  # include trade day

        # Ensure minimum 1 day duration
        if days_to_expiry <= 0:
            return None

        # Optional: add weekend buffer (if it's a short duration trade)
        if days_to_expiry < 7:
            days_to_expiry += 2  # simulate weekend
        else:
            days_to_expiry += 3

        # === If only 1 trade (open position) ===
        if len(trades) == 1:
            return trades[0].annual_yield

        # === If 2 trades (closed position) ===
        trade1, trade2 = trades

        net_premium = trade1.total_price + trade2.total_price  # sell - buy
        if net_premium <= 0:
            return None

        quantity = abs(trade1.quantity)  # or trade2, they should match
        capital_at_risk = self.option.strike_price * Decimal("100") * quantity
        if capital_at_risk <= 0:
            return None

        yield_percent = (net_premium / capital_at_risk) * (Decimal("365") / days_to_expiry) * Decimal("100")
        return yield_percent.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def total_return(self):
        return (self.profit_loss / (self.average_price * self.remaining_quantity)) if self.remaining_quantity else None


class PositionHistory(models.Model):
    position = models.ForeignKey(Position, on_delete=models.CASCADE, related_name="history")
    date = models.DateField()
    remaining_quantity = models.IntegerField()
    average_price = models.DecimalField(max_digits=10, decimal_places=2)
    profit_loss = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.remaining_quantity} of {self.position}"

class Holding(models.Model):
    broker_account = models.ForeignKey(
        BrokerAccount,
        on_delete=models.CASCADE,
        related_name='broker_holdings'
    )
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name='holdings')
    asset = models.ForeignKey(UnderlyingAsset, on_delete=models.CASCADE, related_name='asset_holdings')

    quantity = models.DecimalField(max_digits=10, decimal_places=4)
    average_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=15, decimal_places=2)

    realized_profit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def update_holding(self, new_quantity, new_price):
        total_old_value = self.quantity * self.average_price
        total_new_value = new_quantity * new_price
        combined_quantity = self.quantity + new_quantity

        if combined_quantity == 0:
            self.average_price = Decimal('0.00')
            self.total_cost = Decimal('0.00')
        else:
            self.average_price = (total_old_value + total_new_value) / combined_quantity
            self.total_cost = self.average_price * combined_quantity

        self.quantity = combined_quantity
        self.save()

        HoldingSnapshot.create_snapshot(self)

    def sell(self, quantity_sold, sell_price_per_unit):
        if quantity_sold > self.quantity:
            raise ValueError("Cannot sell more than available quantity.")

        cost_basis = self.average_price * quantity_sold
        proceeds = sell_price_per_unit * quantity_sold
        realized = proceeds - cost_basis

        self.quantity -= quantity_sold
        self.total_cost = self.average_price * self.quantity
        self.realized_profit += realized
        self.save()

        # Optional: update total fund profit
        self.fund.total_profit += realized
        self.fund.save()

        HoldingSnapshot.create_snapshot(self)

        return realized

    @property
    def unrealized_profit(self):
        if not self.asset.live_price or self.quantity == 0:
            return Decimal('0.00')
        current_value = self.asset.live_price * self.quantity
        return current_value - self.total_cost

    @property
    def total_gain_loss(self):
        return self.realized_profit + self.unrealized_profit

    def __str__(self):
        return f"{self.quantity} in {self.fund.name}"
    
    
class HoldingSnapshot(models.Model):
    holding = models.ForeignKey(Holding, on_delete=models.CASCADE, related_name="snapshots")
    quantity = models.DecimalField(max_digits=10, decimal_places=4)
    total_cost = models.DecimalField(max_digits=15, decimal_places=2)
    realized_profit = models.DecimalField(max_digits=15, decimal_places=2)
    unrealized_profit = models.DecimalField(max_digits=15, decimal_places=2)
    total_gain_loss = models.DecimalField(max_digits=15, decimal_places=2)

    price_at_snapshot = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    snapshot_time = models.DateTimeField(auto_now_add=True)

    @classmethod
    def create_snapshot(cls, holding):
        current_price = holding.asset.live_price or Decimal('0.00')
        cls.objects.create(
            holding=holding,
            quantity=holding.quantity,
            total_cost=holding.total_cost,
            realized_profit=holding.realized_profit,
            unrealized_profit=holding.unrealized_profit,
            total_gain_loss=holding.total_gain_loss,
            price_at_snapshot=current_price,
        )

    def __str__(self):
        return f"Snapshot of {self.holding.asset.ticker} @ {self.snapshot_time.date()}"
