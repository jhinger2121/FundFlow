from django.apps import AppConfig
import sys

class TrackersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'trackers'

    def ready(self):
        # Only run this when running server or celery worker, to avoid migrations errors or other commands
        if not (('runserver' in sys.argv) or ('celery' in sys.argv)):
            return

        from django_celery_beat.models import PeriodicTask, CrontabSchedule
        import json

        # Create or get crontab schedule for 9 PM Monday-Friday Toronto time
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute='*',          # every minute
            hour='*',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )

        # Create or update the periodic task for your scraper task
        PeriodicTask.objects.update_or_create(
            name='process company file',
            defaults={
                'crontab': schedule,
                'task': 'trackers.tasks.download_and_process_chain',
                'args': json.dumps([]),
                'enabled': True,
            }
        )