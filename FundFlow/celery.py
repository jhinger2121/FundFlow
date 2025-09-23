import os

from celery.schedules import crontab
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FundFlow.settings.local')

# key_file = '/tmp/keyfile.key'
# cert_file = '/tmp/certfile.crt'
# ca_file = '/tmp/CAtmp.pem'


app = Celery('FundFlow')
app.conf.broker_url = 'redis://localhost:6379/0'
app.conf.result_backend = 'redis://localhost:6379/0'
# app.conf.redis_backend_use_ssl = {
#                  'ssl_keyfile': key_file, 'ssl_certfile': cert_file,
#                  'ssl_ca_certs': ca_file,
#                  'ssl_cert_reqs': 'CERT_REQUIRED'
#             }


# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.beat_scheduler = "django_celery_beat.schedulers:DatabaseScheduler"

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Set timezone to match Django's timezone
app.conf.enable_utc = True
app.conf.timezone = 'America/Toronto'

# @app.task(bind=True)
# def debug_task(self):
#     print(f'Request: {self.request!r}')


# app.conf.beat_schedule = {
#     "save_weekly_snapshots": {
#         "task": "my_app.tasks.save_weekly_snapshots",
#         "schedule": crontab(hour=23, minute=30, day_of_week="6"),  # Runs Sunday at 11:30 PM
#     },
#     "save_monthly_snapshots": {
#         "task": "my_app.tasks.save_monthly_snapshots",
#         "schedule": crontab(hour=23, minute=30, day_of_month="28-31"),  # Runs last day of the month
#     },
#     "save_annual_snapshots": {
#         "task": "my_app.tasks.save_annual_snapshots",
#         "schedule": crontab(hour=23, minute=30, day_of_month="31", month_of_year="12"),  # Runs Dec 31st
#     },
# }

# # FUNDS TASKS
# app.conf.beat_schedule = {
#     "save-fund-profit-summary": {
#         "task": "your_app.tasks.save_fund_profit_summary",
#         "schedule": crontab(hour=23, minute=59),  # Runs at 11:59 PM daily
#     },
# }
