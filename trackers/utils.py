from decimal import Decimal

from django.utils.timezone import now
from django.db.models import Sum
from datetime import timedelta, datetime

from .models import Option, Company, FundProfitSummary, Fund, CompanyProfitSummary, BrokerAccount, BrokerAccountProfitSummary
from .parser.utils import get_week_range, get_month_range, get_year_range

def get_options_by_company_and_status(company_name, active=True):
    # Get the company instance based on the company_name
    company = Company.objects.get(name=company_name)
    
    # Query options filtered by company and active status
    options = Option.objects.filter(company=company)
    
    return options


def get_all_company_names():
    return Company.objects.values_list('name', flat=True).distinct()


def calculate_company_profit(company):
    today = now().date()

    start_of_week = today - timedelta(days=today.weekday())  # Monday
    start_of_month = today.replace(day=1)  # First day of the month
    start_of_year = today.replace(month=1, day=1)  # First day of the year

    # Calculate profit from trades
    weekly_profit = company.trades.filter(trade_date__gte=start_of_week).aggregate(total=Sum('profit'))['total'] or 0
    monthly_profit = company.trades.filter(trade_date__gte=start_of_month).aggregate(total=Sum('profit'))['total'] or 0
    annually_profit = company.trades.filter(trade_date__gte=start_of_year).aggregate(total=Sum('profit'))['total'] or 0
    total_profit = company.trades.aggregate(total=Sum('profit'))['total'] or 0  # All-time total profit

    # Update company model
    company.weekly_profit = weekly_profit
    company.monthly_profit = monthly_profit
    company.annually_profit = annually_profit
    company.total_profit = total_profit
    company.save()


def save_weekly_fund_profit():
    today = now().date()
    start_of_week = today - timedelta(days=today.weekday())  # Monday

    for fund in Fund.objects.all():
        weekly_profit = fund.trades.filter(trade_date__gte=start_of_week).aggregate(total=Sum('profit'))['total'] or 0

        FundProfitSummary.objects.create(
            fund=fund,
            start_date=start_of_week,
            end_date=today,
            weekly_profit=weekly_profit,
        )

    print("✅ Weekly fund profits saved!")

def save_monthly_fund_profit():
    today = now().date()
    start_of_month = today.replace(day=1)  # First day of the month

    for fund in Fund.objects.all():
        monthly_profit = fund.trades.filter(trade_date__gte=start_of_month).aggregate(total=Sum('profit'))['total'] or 0

        FundProfitSummary.objects.create(
            fund=fund,
            start_date=start_of_month,
            end_date=today,
            monthly_profit=monthly_profit,
        )

    print("✅ Monthly fund profits saved!")

def save_annual_fund_profit():
    today = now().date()
    start_of_year = today.replace(month=1, day=1)  # First day of the year

    for fund in Fund.objects.all():
        annually_profit = fund.trades.filter(trade_date__gte=start_of_year).aggregate(total=Sum('profit'))['total'] or 0

        FundProfitSummary.objects.create(
            fund=fund,
            start_date=start_of_year,
            end_date=today,
            annually_profit=annually_profit,
        )

    print("✅ Annual fund profits saved!")


def update_fund_model():
    today = now().date()
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    start_of_month = today.replace(day=1)  # First day of the month
    start_of_year = today.replace(month=1, day=1)  # First day of the year

    for fund in Fund.objects.all():
        fund.weekly_profit = fund.trades.filter(trade_date__gte=start_of_week).aggregate(total=Sum('total_price'))['total'] or 0
        fund.monthly_profit = fund.trades.filter(trade_date__gte=start_of_month).aggregate(total=Sum('total_price'))['total'] or 0
        fund.annually_profit = fund.trades.filter(trade_date__gte=start_of_year).aggregate(total=Sum('total_price'))['total'] or 0
        fund.total_profit = fund.trades.aggregate(total=Sum('profit'))['total'] or 0

        fund.save()

    print("✅ Fund model updated successfully!")


def get_weekly_folder():
    """Returns folder name in YYYY-WW format"""
    today = datetime.today()
    return f"{today.year}-W{today.strftime('%V')}"



# get or update the funds summaries
def update_fund_summary(fund, trade_date, total_price):
    total_price = Decimal(total_price)
    
    # --- Weekly ---
    week_start, week_end = get_week_range(trade_date)
    weekly_summary, _ = FundProfitSummary.objects.get_or_create(
        fund=fund,
        start_date=week_start,
        end_date=week_end,
    )
    weekly_summary.weekly_profit += total_price
    weekly_summary.save()

    # --- Monthly ---
    month_start, month_end = get_month_range(trade_date)
    monthly_summary, _ = FundProfitSummary.objects.get_or_create(
        fund=fund,
        start_date=month_start,
        end_date=month_end,
    )
    monthly_summary.monthly_profit += total_price
    monthly_summary.save()

    # --- Yearly ---
    year_start, year_end = get_year_range(trade_date)
    yearly_summary, _ = FundProfitSummary.objects.get_or_create(
        fund=fund,
        start_date=year_start,
        end_date=year_end,
    )
    yearly_summary.annually_profit += total_price
    yearly_summary.save()

    fund.total_profit += Decimal(total_price)
    fund.save()

# get or update the company summaries
def update_company_summary(company, trade_date, total_price):
    total_price = Decimal(total_price)

    # --- Weekly ---
    week_start, week_end = get_week_range(trade_date)
    weekly_summary, _ = CompanyProfitSummary.objects.get_or_create(
        company=company,
        start_date=week_start,
        end_date=week_end,
    )
    weekly_summary.weekly_profit += total_price
    weekly_summary.save()

    # --- Monthly ---
    month_start, month_end = get_month_range(trade_date)
    monthly_summary, _ = CompanyProfitSummary.objects.get_or_create(
        company=company,
        start_date=month_start,
        end_date=month_end,
    )
    monthly_summary.monthly_profit += total_price
    monthly_summary.save()

    # --- Yearly ---
    year_start, year_end = get_year_range(trade_date)
    yearly_summary, _ = CompanyProfitSummary.objects.get_or_create(
        company=company,
        start_date=year_start,
        end_date=year_end,
    )
    yearly_summary.annually_profit += total_price
    yearly_summary.save()

def update_Broker_summary(broker, trade_date, total_price):
    total_price = Decimal(total_price)

    # --- Weekly ---
    week_start, week_end = get_week_range(trade_date)
    weekly_summary, _ = BrokerAccountProfitSummary.objects.get_or_create(
        broker=broker,
        start_date=week_start,
        end_date=week_end,
    )
    weekly_summary.weekly_profit += total_price
    weekly_summary.save()

    # --- Monthly ---
    month_start, month_end = get_month_range(trade_date)
    monthly_summary, _ = BrokerAccountProfitSummary.objects.get_or_create(
        broker=broker,
        start_date=month_start,
        end_date=month_end,
    )
    monthly_summary.monthly_profit += total_price
    monthly_summary.save()

    # --- Yearly ---
    year_start, year_end = get_year_range(trade_date)
    yearly_summary, _ = BrokerAccountProfitSummary.objects.get_or_create(
        broker=broker,
        start_date=year_start,
        end_date=year_end,
    )
    yearly_summary.annually_profit += total_price
    yearly_summary.save()