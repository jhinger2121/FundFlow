from django.contrib import admin
from trackers.models import Fund, Option, Trade, Position, UnderlyingAsset, Company, PositionHistory, FundProfitSummary, CompanyProfitSummary, Holding, HoldingSnapshot, BrokerAccount

admin.site.register(Fund)
admin.site.register(Option)
admin.site.register(Trade)
admin.site.register(Position)
admin.site.register(UnderlyingAsset)
admin.site.register(Company)
admin.site.register(PositionHistory)
admin.site.register(FundProfitSummary)
admin.site.register(CompanyProfitSummary)
admin.site.register(Holding)
admin.site.register(HoldingSnapshot)
admin.site.register(BrokerAccount)
