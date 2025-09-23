import os
from collections import defaultdict
from decimal import Decimal
from datetime import datetime

from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Prefetch, Q
from django.db import models, IntegrityError
from django.utils.timezone import now
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.text import slugify
from django.conf import settings

from .forms import OptionsTradeForm, FundForm, OptionsTradeForm, CloseTradeForm, HoldingForm, ManualHoldingForm, BrokerAccountForm

from trackers.tasks import queue_file_processing, process_company_file, update_option_and_underlying_price
from trackers.csv_downloader.tasks import download_daily_trades
from trackers.models import Fund, UnderlyingAsset, Option, Trade, Position, Company, FundProfitSummary, CompanyProfitSummary, Holding, BrokerAccount
from .utils import get_options_by_company_and_status, get_all_company_names, update_fund_summary, update_company_summary, update_Broker_summary
from .parser.utils import get_month_range, get_week_range, get_year_range

from .market_scraper.tasks import get_data, update_option_models, update_underline_models
from .IBKR.import_service import OptionImportService
from .IBKR.parser import ParserFactory

def get_best_and_worst_fund_per_company(start, end, profit_field='monthly_profit'):
    summaries = FundProfitSummary.objects.filter(
        start_date=start, end_date=end
    ).select_related('fund', 'fund__company')

    result = defaultdict(lambda: {"best": None, "worst": None})

    for summary in summaries:
        company = summary.fund.company
        profit = getattr(summary.fund, profit_field)

        best = result[company]["best"]
        worst = result[company]["worst"]

        if not best or profit > getattr(best, profit_field):
            result[company]["best"] = summary.fund

        if not worst or profit < getattr(worst, profit_field):
            result[company]["worst"] = summary.fund

    return result  # Dict[Company] = {"best": Fund, "worst": Fund}


def dashboard_view(request):
    # process_company_file('Defiance')
    # get_data()
    # update_underline_models()
    # update_option_models()
    today = datetime.today()

    companies_data = []
    week_start, week_end = get_week_range(today)
    month_start, month_end = get_month_range(today)

    for company in Company.objects.all():
        funds = company.funds.all()

        # Weekly best and worst fund
        # best_weekly_fund = funds.order_by('-weekly_profit').first()
        # worst_weekly_fund = funds.order_by('weekly_profit').first()

        # # Monthly best and worst fund
        # best_monthly_fund = funds.order_by('-monthly_profit').first()
        # worst_monthly_fund = funds.order_by('monthly_profit').first()

        # companies_data.append({
        #     'company': company,
        #     'best_weekly_fund': {
        #         'fund': best_weekly_fund,
        #         'summary': best_weekly_fund.get_current_week_summary() if best_weekly_fund else None,
        #     },
        #     'worst_weekly_fund': {
        #         'fund': worst_weekly_fund,
        #         'summary': worst_weekly_fund.get_current_week_summary() if worst_weekly_fund else None,
        #     },
        #     'best_monthly_fund': {
        #         'fund': best_monthly_fund,
        #         'summary': best_monthly_fund.get_current_month_summary() if best_monthly_fund else None,
        #     },
        #     'worst_monthly_fund': {
        #         'fund': worst_monthly_fund,
        #         'summary': worst_monthly_fund.get_current_month_summary() if worst_monthly_fund else None,
        #     },
        # })

    week_start, week_end = get_week_range(today)
    month_start, month_end = get_month_range(today)
    year_start, year_end = get_year_range(today)

    # week_data = get_best_and_worst_fund_per_company(week_start, week_end, 'weekly_profit')
    # month_data = get_best_and_worst_fund_per_company(month_start, month_end, 'monthly_profit')
    # year_data = get_best_and_worst_fund_per_company(year_start, year_end, 'annually_profit')

    companies_data = []

    for company in Company.objects.all():
        companies_data.append({
            "company": company,
            # "best_week": week_data.get(company, {}).get("best"),
            # "worst_week": week_data.get(company, {}).get("worst"),
            # "best_month": month_data.get(company, {}).get("best"),
            # "worst_month": month_data.get(company, {}).get("worst"),
            # "best_year": year_data.get(company, {}).get("best"),
            # "worst_year": year_data.get(company, {}).get("worst"),
        })
    context = {
        "companies_data": companies_data
    }
    return render(request, 'trackers/dashboard.html', context)

def fund_detail(request, id, slug):
    fund = get_object_or_404(Fund, id=id, slug=slug)

    show_all = request.GET.get("all", "false").lower() == "true"

    if show_all:
        trades = Trade.objects.filter(option__fund=fund).select_related("option")
    else:
        trades = Trade.objects.filter(
            option__fund=fund,
            active=True,
            option__expiration_date__gte=now().date()
        ).select_related("option")

    context = {
        "fund": fund,
        "trades": trades,
        "show_all": show_all,
    }
    return render(request, "trackers/fund_detail.html", context)

def company_detail(request, id, slug):

    company = get_object_or_404(Company, id=id, slug=slug)
      # Using annotate to get the count of active positions for each fund
    funds = Fund.objects.filter(company=company).annotate(
        active_positions_count=Count('positions', filter=models.Q(positions__active='True'))
    )

    fund_summaries = FundProfitSummary.objects.filter(fund__in=funds)

    # Sorting funds by total_profit in descending order (highest profits first)
    sorted_funds = sorted(funds, key=lambda f: f.total_profit, reverse=True)

    # Get top 3 earning funds and bottom 3 earning funds
    top_3_funds = sorted_funds[:3]
    bottom_3_funds = sorted_funds[-3:]  # Last 3 funds

    context = {
        "company": company,
        "funds": funds,
        "fund_summaries": fund_summaries,
        "top_3_funds": top_3_funds,
        "bottom_3_funds": bottom_3_funds,
    }
    return render(request, 'trackers/company_detail.html', context)

@login_required
def user_fund_detail(request, broker_name, id, slug):
    user = request.user
    broker = get_object_or_404(BrokerAccount, broker_name=broker_name, user=user)
    fund = get_object_or_404(Fund, id=id, slug=slug, broker_account=broker)

    holding = Holding.objects.filter(fund=fund)
    show_all = request.GET.get("all", "false").lower() == "true"


    funds = FundProfitSummary.objects.filter(fund=fund)

    if show_all:
        positions = Position.objects.filter(fund=fund, fund__broker_account=broker).select_related("option")
    else:
        positions = Position.objects.filter(
            fund=fund,
            fund__broker_account=broker,
            remaining_quantity__gt=0,
            option__expiration_date__gte=now().date()
        ).select_related("option")

    context = {
        "fund": fund,
        "positions": positions,
        "show_all": show_all,
        "holding": holding,
        "funds": funds,
    }
    return render(request, "trackers/user_fund_detail.html", context)


@login_required
def submit_options_trade(request):
    if request.method == 'POST':
        form = OptionsTradeForm(request.POST, user=request.user)
        if form.is_valid():
            # Step 1: Extract data from form
            broker = form.cleaned_data['broker']
            fund = form.cleaned_data['fund']
            symbol = form.cleaned_data['symbol'].upper()
            trade_date = form.cleaned_data['trade_date']
            expiry_date = form.cleaned_data['expiry_date']
            strike_price = form.cleaned_data['strike_price']
            premium = form.cleaned_data['premium']
            quantity = form.cleaned_data['quantity']
            option_type = form.cleaned_data['option_type']
            action = form.cleaned_data['action']
            commission = form.cleaned_data['commission']

            # Step 2: Try to get underlying asset (basic assumption: 1:1 mapping with symbol)
            try:
                underlying, _ = UnderlyingAsset.objects.get_or_create(name=symbol)
            except UnderlyingAsset.DoesNotExist:
                messages.error(request, f"Underlying asset '{symbol}' not found.")
                return render(request, 'trackers/submit_trade.html', {'form': form})

            # Step 3: Build option ticker string
            formatted_expiry = expiry_date.strftime("%y%m%d")  # e.g., 241025
            type_code = 'C' if option_type == 'CALL' else 'P'
            strike_formatted = f"{int(strike_price * 1000):08d}"  # e.g., 00232500
            ticker = f"{symbol}{formatted_expiry}{type_code}{strike_formatted}"

            # Step 4: Check if option exists or create it
            option, created = Option.objects.get_or_create(
                ticker=ticker,
                defaults={
                    'fund': fund,
                    'type': type_code,
                    'strike_price': strike_price,
                    'expiration_date': expiry_date,
                    'underlying_asset': underlying
                }
            )

            # Step 5: Create the Trade
            trade = Trade.objects.create(
                option=option,
                trade_type=action,
                quantity=quantity,
                price=premium,
                date=trade_date,
                commission=commission,
            )

            position = Position.objects.create(
                option=option,
                fund=fund,
                remaining_quantity=abs(trade.quantity),
                average_price=trade.price,
                profit_loss=trade.total_price,
                trade_type=trade.trade_type,
                date=trade.date,
                commission=trade.commission,
            )
            trade.position = position
            trade.save() 
            # # Step 6: Process the trade through the PositionManager
            # try:
            #     Position.objects.process_trade(fund, option, trade)
            # except ValueError as e:
            #     messages.error(request, str(e))
            #     return render(request, 'trackers/submit_trade.html', {'form': form})
            
            # update fund summary
            update_fund_summary(fund, trade.date, trade.total_price)

            # update Broker Account summary
            update_Broker_summary(broker, trade.date, trade.total_price)

            # update_option_and_underlying_price.delay(
            #     option_id=option.id,
            #     underlying_id=underlying.id,
            #     trade_date_str=str(trade.date)  # format YYYY-MM-DD
            # )

            print("SAVED TRADE:", trade.trade_type, trade.total_price)
            messages.success(request, 'Trade submitted successfully.')
            return redirect('fund_detail', id=fund.id, slug=fund.slug)  # Adjust to your URL name
    else:
        form = OptionsTradeForm(user=request.user)

    return render(request, 'trackers/submit_trade.html', {'form': form})


@login_required
def add_fund(request):
    if request.method == "POST":
        form = FundForm(request.POST, user=request.user)  # pass user here
        if form.is_valid():
            fund = form.save(commit=False)
            fund.slug = slugify(fund.name)
            fund.name = fund.name.upper()
            fund.save()
            messages.success(request, "Fund created successfully!")
            return redirect("fund_detail", id=fund.id, slug=fund.slug)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = FundForm(user=request.user)  # also pass user here

    return render(request, "trackers/add_fund.html", {"form": form})

@login_required
def add_broker(request):
    if request.method == "POST":
        form = BrokerAccountForm(request.POST)
        if form.is_valid():
            broker = form.save(commit=False)
            broker.user = request.user
            broker.slug = slugify(broker.broker_name.upper())
            try:
                broker.save()
                messages.success(request, "Broker created successfully!")
                return redirect('/')
                # return redirect("fund_detail", id=broker.id, slug=broker.slug)
            except IntegrityError:
                # Gracefully handle DB uniqueness error
                form.add_error("broker_name", "You already added this broker.")
                messages.error(request, "This broker already exists in your account.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = BrokerAccountForm()

    return render(request, "trackers/add_broker.html", {"form": form})

@login_required
def user_dashboard(request):
    user = request.user
    broker_accounts = BrokerAccount.objects.filter(user=user)

    funds = Fund.objects.filter(broker_account__in=broker_accounts)
    positions = Position.objects.filter(fund__broker_account__in=broker_accounts).select_related("fund", "option")
    holdings = Holding.objects.filter(fund__broker_account__in=broker_accounts).select_related('fund', 'asset')
    
    all_user_weekly = 0
    all_user_monthly = 0
    all_user_yearly = 0
    total_all_time_options = 0
    conbined_total = 0
    holding_total = 0
    accounts = []
    for broker in broker_accounts:
        summary = Fund.get_user_profit_summaries(broker)
        all_user_weekly += summary["weekly"]

        all_user_monthly += summary["monthly"]
        # all_user_monthly["broker"][broker.broker_name] = summary["monthly"]

        all_user_yearly += summary["yearly"]
        # all_user_yearly["broker"][broker.broker_name] = summary["yearly"]

        total_all_time_options += summary["total_all_time_options"]
        # total_all_time_options["broker"][broker.broker_name] = summary["total_all_time_options"]

        conbined_total += summary["combined_total_all_time"]
        # conbined_total["broker"][broker.broker_name] = summary["combined_total_all_time"]
        
        holding_total += summary["holding_profit_loss"]
        # holding_total["broker"][broker.broker_name] = summary["holding_profit_loss"]
        accounts.append({
            "broker": broker,
            "summary": summary
        })
    context = {
        "accounts": accounts,
        "positions": positions,
        "funds": funds,
        "user_total_weekly_profit": all_user_weekly,
        "user_total_monthly_profit": all_user_monthly,
        "user_total_yearly_profit": all_user_yearly,
        "user_total_all_time_profit": total_all_time_options,

        "combined_total_all_time": conbined_total,

        "holding_total_all_time": holding_total,
        'holdings': holdings,
        "brokers": BrokerAccount.objects.filter(user=user)
    }
    return render(request, "trackers/user_dashboard.html", context)


@login_required
def broker_detail(request, broker_slug, broker_id):
    user = request.user
    broker = get_object_or_404(BrokerAccount, id=broker_id, user=user)
    funds = Fund.objects.filter(broker_account=broker) \
        .annotate(active_positions_total=Count("positions", filter=Q(positions__active=True))) \
        .prefetch_related(
            Prefetch(
                "holdings",
                queryset=Holding.objects.filter(quantity__gt=0, fund__broker_account=broker).select_related('asset'),
            ),
            Prefetch(
                "positions",
                queryset=Position.objects.filter(active=True, fund__broker_account=broker),
            ),
        )
    summary = Fund.get_user_profit_summaries(broker)
    context = {"broker": broker,
        "funds": funds,
        "user_total_weekly_profit": summary["weekly"],
        "user_total_monthly_profit": summary["monthly"],
        "user_total_yearly_profit": summary["yearly"],
        "user_total_all_time_profit": summary["total_all_time_options"],

        "combined_total_all_time": summary["combined_total_all_time"],

        "holding_total_all_time": summary["holding_profit_loss"],
        }
    return render(request, "trackers/broker_detail.html", context)


@login_required
def position_detail_view(request, broker_name, id):
    user = request.user
    broker = get_object_or_404(BrokerAccount, broker_name=broker_name, user=user)
    position = get_object_or_404(Position, id=id, fund__broker_account=broker)
    trades = position.trades.order_by("date")

    return render(request, "trackers/position_detail.html", {
        "position": position,
        "trades": trades,
    })

@login_required
def check_fund_name(request):
    name = request.GET.get('name', '').strip()
    broker_id = request.GET.get('broker_id')
    exists = False
    broker = BrokerAccount.objects.filter(user=request.user).first()
    if request.user.is_authenticated and name and broker_id:
        exists = Fund.objects.filter(
            name__iexact=name,
            broker_account_id=broker_id,
            broker_account__user=request.user
        ).exists()

    return JsonResponse({'exists': exists})

# This is used when we click on the "expired worthless" button
# i think its useless beacause i can use "Buy to Close"  button
@login_required
def mark_position_expired(request, id):
    position = get_object_or_404(Position, id=id, fund__user=request.user, active=True)

    if request.method == "POST":
        if "confirm" in request.POST:
            # Mark position as closed
            position.active = False
            position.save()

            # Create the offsetting "Buy to Close" trade at 0 cost
            Trade.objects.create(
                position=position,
                option=position.option,
                trade_type="BC",  # Buy to Close
                quantity=position.remaining_quantity,
                price=Decimal("0.00"),
                date=position.option.expiration_date,
                active=False,
            )

            messages.success(request, "Position marked as expired and closed with a Buy to Close trade.")
            return redirect("user_fund_detail", id=position.fund.id, slug=position.fund.slug)

        else:
            return redirect("user_fund_detail", id=position.fund.id, slug=position.fund.slug)

    return render(request, "trackers/confirm_expired.html", {"position": position})


@login_required
def close_position_trade(request, id, broker_name):
    broker = get_object_or_404(BrokerAccount, broker_name=broker_name, user=request.user)
    position = get_object_or_404(Position, id=id, fund__broker_account=broker, active=True)
    option = position.option
    fund = position.fund

    if request.method == 'POST':
        form = CloseTradeForm(request.POST)
        if form.is_valid():
            premium = form.cleaned_data['premium']
            quantity = form.cleaned_data['quantity']
            commission = form.cleaned_data['commission']
            notes = form.cleaned_data['notes']

            if quantity > position.remaining_quantity:
                messages.error(request, "Cannot close more than the remaining quantity.")
                return render(request, 'trackers/close_trade.html', {'form': form, 'position': position})

            # Create closing trade
            trade = Trade.objects.create(
                position=position,
                option=option,
                trade_type='BC' if position.trade_type == 'S' else 'S',
                quantity=quantity,
                price=premium,
                # IMPORTANT:::::: this should be expire date of options or should add a filed(null=true) to from
                date=option.expiration_date,
                commission=commission,
                active=False,
            )
            # IMPARTANT::: also change the posion price ex. frsit.trade.price - new.trade.price        
            pnl = position.profit_loss + trade.total_price
            # Update position
            position.remaining_quantity -= quantity
            if position.remaining_quantity <= 0:
                position.active = False
            position.commission += commission
            position.profit_loss = pnl
            position.save()

            update_fund_summary(fund, trade.date, trade.total_price)

            messages.success(request, "Closing trade recorded and position updated.")
            return redirect('user_fund_detail', broker_name=broker_name, id=fund.id, slug=fund.slug)
    else:
        form = CloseTradeForm(initial={
            'quantity': position.remaining_quantity,
            'commission': 0.00
        })

    return render(request, 'trackers/close_trade.html', {
        'form': form,
        'position': position,
    })

@login_required
def edit_trade_view(request, broker_name, trade_id):
    broker = get_object_or_404(BrokerAccount, broker_name=broker_name, user=request.user)
    trade = get_object_or_404(Trade, id=trade_id, option__fund__broker_account=broker)
    option = trade.option
    position = trade.position
    print("trade price old", trade.price)

    initial_data = {
        "fund": option.fund,
        "broker": broker,
        "symbol": option.ticker,
        "trade_date": trade.date,
        "expiry_date": option.expiration_date,
        "strike_price": option.strike_price,
        "premium": trade.price,
        "quantity": trade.quantity,
        "option_type": "CALL" if option.type == "C" else "PUT",
        "action": trade.trade_type,
        "commission": trade.commission,
        "notes": "",
    }

    if request.method == "POST":
        form = OptionsTradeForm(request.POST, user=request.user)
        if form.is_valid():
            cd = form.cleaned_data

            update_fund_summary(option.fund, trade.date, -trade.total_price)

            # Update Option
            option.strike_price = cd["strike_price"]
            option.expiration_date = cd["expiry_date"]
            option.type = "C" if cd["option_type"] == "CALL" else "P"
            option.regenerate_ticker()
            option.save()

            # Calculate differences
            old_commission = trade.commission
            new_commission = cd['commission']
            differance_commission = new_commission - old_commission

            # old_price = trade.price
            new_price = cd["premium"]
            # price_multiplier = -1 if trade.trade_type in ["BC", "B"] else 1
            # differance_price = (new_price - old_price) * price_multiplier

            # position.profit_loss += (differance_price * 100) - differance_commission
            # print("price diff", differance_price, old_price, new_price)

            position.remaining_quantity = (
                position.remaining_quantity - trade.quantity + cd["quantity"]
            )
            print(position.profit_loss)
            # Update Trade
            trade.trade_type = cd["action"]
            trade.quantity = cd["quantity"]
            trade.price = new_price
            trade.date = cd["trade_date"]
            trade.commission = new_commission
            trade.save()

            # Update Position
            position.trade_type = cd["action"]
            position.date = cd["trade_date"].date()
            position.commission += differance_commission
            position.profit_loss = trade.total_price
            position.save()

            update_fund_summary(option.fund, trade.date, trade.total_price)
            return redirect("position_detail", broker.broker_name, id=position.id)
    else:
        form = OptionsTradeForm(initial=initial_data, user=request.user)

    return render(request, "trackers/edit_trade.html", {
        "form": form,
        "position": position,
        "trade": trade,
    })

@login_required
def create_or_update_holding(request):
    if request.method == "POST":
        form = HoldingForm(request.POST)
        if form.is_valid():
            fund = form.cleaned_data["fund"]
            asset = form.cleaned_data["asset"]
            quantity = form.cleaned_data["quantity"]
            price = form.cleaned_data["price"]

            # Get or create existing holding
            holding, created = Holding.objects.get_or_create(
                fund=fund, asset=asset,
                defaults={
                    "quantity": quantity,
                    "average_price": price,
                    "total_cost": price * quantity,
                }
            )

            if not created:
                holding.update_holding(quantity, price)

            return redirect("holding_list")  # or any other page
    else:
        form = HoldingForm()

    return render(request, "portfolio/holding_form.html", {"form": form})


@login_required
def holding_detail_view(request, broker_name, id):
    broker = get_object_or_404(BrokerAccount, broker_name=broker_name, user=request.user)
    # process_company_file('Defiance')
    # get_data()
    # update_underline_models()
    # update_option_models()
    holding = get_object_or_404(Holding, id=id, fund__broker_account=broker)
    return render(request, 'trackers/holding_detail.html', {'holding': holding})

# @login_required
# def holding_update_view(request, id):
#     # Your logic to update holding goes here
#     return render(request, 'trackers/holding_update.html', {'id': id})

# @login_required
# def holding_sell_view(request, id):
#     # Your logic to sell from the holding goes here
#     return render(request, 'trackers/holding_sell.html', {'id': id})

@login_required
def holding_buy_from_put_view(request, broker_name, position_id):
    broker = get_object_or_404(BrokerAccount, broker_name=broker_name, user=request.user)
    position = get_object_or_404(Position, id=position_id, fund__broker_account=broker)
    fund = position.fund
    asset = position.option.underlying_asset

    if request.method == "POST":
        form = HoldingForm(request.POST)
        if form.is_valid():
            contract = form.cleaned_data["contract"]
            price = form.cleaned_data["price"]

            if contract > position.remaining_quantity:
                form.add_error("contract", f"You can only close up to {position.remaining_quantity} contracts.")
            else:
                holding, created = Holding.objects.get_or_create(
                    fund=fund,
                    asset=asset,
                    defaults={"quantity": 0, "average_price": 0, "total_cost": 0}
                )
                quantity = contract * 100

                total_old_cost = holding.quantity * holding.average_price
                total_new_cost = quantity * price
                total_quantity = holding.quantity + quantity

                holding.quantity = total_quantity
                holding.total_cost = total_old_cost + total_new_cost
                holding.average_price = holding.total_cost / total_quantity
                holding.save()

                position.remaining_quantity -= contract
                if position.remaining_quantity == 0:
                    position.active = False
                position.save()

                Trade.objects.filter(option=position.option, active=True).update(active=False)

                return redirect("holding_detail", broker_name, id=holding.id)
    else:
        form = HoldingForm(
            initial={"fund": fund, "asset": asset, "price": position.option.strike_price,
                     "contract": position.remaining_quantity})

    return render(request, "trackers/holding_trade_form.html", {"form": form, "action": "Buy Shares from PUT","position": position,})


@login_required
def holding_sell_from_call_view(request, broker_name, position_id):
    broker = get_object_or_404(BrokerAccount, broker_name=broker_name, user=request.user)
    position = get_object_or_404(Position, id=position_id, fund__broker_account=broker)
    fund = position.fund
    asset = position.option.underlying_asset

    holding = get_object_or_404(Holding, fund=fund, asset=asset)

    if request.method == "POST":
        form = HoldingForm(request.POST)
        if form.is_valid():
            contract = form.cleaned_data["contract"]
            price = form.cleaned_data["price"]
            quantity = contract * 100

            if quantity > holding.quantity:
                form.add_error("contract", f"You can only close up to {position.remaining_quantity} contracts.")
            else:
                holding.quantity -= quantity
                holding.total_cost = holding.quantity * holding.average_price
                holding.realized_profit += (price - holding.average_price) * quantity
                holding.save()

                position.remaining_quantity -= contract
                if position.remaining_quantity == 0:
                    position.active = False
                position.save()
                Trade.objects.filter(option=position.option, active=True).update(active=False)

                return redirect("holding_detail", broker_name, id=holding.id)
    else:
        form = HoldingForm(
            initial={"fund": fund, "asset": asset, "price": position.option.strike_price, 
                     "contract": position.remaining_quantity})

    return render(request, "trackers/holding_trade_form.html", {"form": form, "action": "Sell Shares from CALL","position": position,})


def fund_profit_summary_data(request, fund_id):
    summaries = FundProfitSummary.objects.filter(fund_id=fund_id).order_by("start_date")

    weekly = {}
    monthly = {}
    annually = {}

    for s in summaries:
        week_label = f"{s.start_date.isocalendar().year}-W{s.start_date.isocalendar().week}"
        weekly[week_label] = weekly.get(week_label, 0) + float(s.weekly_profit or 0)

        month_label = s.start_date.strftime("%Y-%m")
        monthly[month_label] = monthly.get(month_label, 0) + float(s.monthly_profit or 0)

        year_label = str(s.start_date.year)
        annually[year_label] = annually.get(year_label, 0) + float(s.annually_profit or 0)

    def format_summary(data_dict):
        return [{"label": k, "profit": round(v, 2)} for k, v in sorted(data_dict.items())]

    return JsonResponse({
        "weekly": format_summary(weekly),
        "monthly": format_summary(monthly),
        "annually": format_summary(annually)
    })

# i was working on thsi one
# then i relized that i also need to add Broker to account
def holding_transaction(request):
    if request.method == 'POST':
        form = ManualHoldingForm(request.POST)
        if form.is_valid():
            fund = form.cleaned_data['fund']
            asset = form.cleaned_data['asset']
            transaction_type = form.cleaned_data['transaction_type']
            quantity = form.cleaned_data['trade_quantity']
            price = form.cleaned_data['trade_price']

            # Try to find existing holding
            holding, created = Holding.objects.get_or_create(
                fund=fund, asset=asset,
                defaults={'quantity': 0, 'average_price': 0, 'total_cost': 0}
            )

            if transaction_type == 'buy':
                holding.update_holding(quantity, price)
            elif transaction_type == 'sell':
                holding.sell(quantity, price)

            return redirect('holding_detail', id=holding.id)
    else:
        form = ManualHoldingForm()
    return render(request, 'trackers/holding_form.html', {'form': form})


# THIS IS ONLY FOR TESTING
def home(request):
    # process_company_file("YieldMax")
    download_daily_trades()
    options = Option.objects.all()
    context = {"options": options}
    
    return render(request, 'trackers/dashboard.html', context)

def import_csv_view(request):
    filepath = os.path.join(settings.MEDIA_ROOT, "excel_files", "IBKR", "options.csv")
    parser = ParserFactory.get_parser("IBKR", filepath, request.user)
    print("Importing file from:", filepath)  # Add this to debug
    parser.parse_and_save()
    # if not os.path.exists(filepath):
    #     raise FileNotFoundError(f"File does not exist at: {filepath}")

    # importer = OptionImportService(filepath, user=request.user)
    # importer.run()
    return HttpResponse("Doen.")


# views.py
import yfinance as yf
from django.http import JsonResponse

def live_price(request, symbol):
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! requesting new price")
    data = yf.Ticker(symbol).history(period="1d")
    price = data["Close"].iloc[-1] if not data.empty else None
    return JsonResponse({"price": round(price, 2) if price else None})

def option_chain(request, symbol, expiry):
    ticker = yf.Ticker(symbol)
    try:
        chain = ticker.option_chain(expiry)
        calls = chain.calls.to_dict("records")
        puts = chain.puts.to_dict("records")
        return JsonResponse({
            "calls": calls,
            "puts": puts,
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
    
def get_funds(request):
    broker_id = request.GET.get('broker_id')
    funds = Fund.objects.filter(broker_account__id = broker_id)
    data = [{'id': fund.id, 'name': fund.name} for fund in funds]
    return JsonResponse(data, safe=False)