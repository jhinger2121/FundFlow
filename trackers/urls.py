from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard_view, name="dashboard_view"),

    path("funds/add/", views.add_fund, name="add_fund"),
    path("broker/add/", views.add_broker, name="add_broker"),
    path('submit-trade/', views.submit_options_trade, name='submit_options_trade'),

    path("<str:broker_name>/trade/<int:trade_id>/edit/", views.edit_trade_view, name="edit_trade"),
    path("<str:broker_name>/position/<int:id>/", views.position_detail_view, name="position_detail"),
    path('position/<int:id>/confirm-assignment/', views.mark_position_expired, name='mark_position_expired'),
    # path('position/<int:id>/mark-expired/', views.mark_position_expired, name='mark_position_expired'),
    path('<str:broker_name>/position/<int:id>/close/', views.close_position_trade, name='close_position_trade'),

    path('<str:broker_name>/holding/<int:id>/', views.holding_detail_view, name='holding_detail'),
    path('holding/add/', views.holding_transaction, name='holding_transaction'),
    path("<str:broker_name>/holding/from-put/<int:position_id>/", views.holding_buy_from_put_view, name="holding_buy_from_put"),
    path("<str:broker_name>/holding/from-call/<int:position_id>/", views.holding_sell_from_call_view, name="holding_sell_from_call"),

    
    path("dashboard/", views.user_dashboard, name="user_dashboard"),
    path("<str:broker_slug>/<int:broker_id>/", views.broker_detail, name="broker_detail"),
    # path("funds/", views.funds_list, name="funds_list"),
    # path("options/", views.options_list, name="options_list"),
    # path("trades/", views.trades_list, name="trades_list"),

    # Company URLs
    path("company/<int:id>/<slug:slug>/", views.company_detail, name="company_detail"),
    # path("company/<int:id>/<slug:slug>/update/", views.update_company, name="update-company"),
    # path("company/<int:id>/<slug:slug>/delete/", views.delete_company, name="delete-company"),
    # path("companies/", views.company_list, name="company-list"),

    path('fund/<int:id>/<slug:slug>', views.fund_detail, name='fund_detail'),
    path('<str:broker_name>/myfund/<int:id>/<slug:slug>/', views.user_fund_detail, name='user_fund_detail'),


    path('ajax/check-fund-name/', views.check_fund_name, name='check_fund_name'),
    path('ajax/get-funds/', views.get_funds, name='get_funds'),

    # urls.py
    path("funds/<int:fund_id>/chart-data/", views.fund_profit_summary_data, name="fund_profit_summary_data"),

    path("IBKR/", views.import_csv_view, name="import_csv_view"),
    path("get/", views.home, name="home"),

    path("api/option-chain/<str:symbol>/<str:expiry>/", views.option_chain, name="option_chain"),
    # urls.py
    path('api/live-price/<str:symbol>/', views.live_price, name='live_price'),
    path('api/option-chain/<str:symbol>/<str:expiry>/', views.option_chain, name='option_chain'),

]
