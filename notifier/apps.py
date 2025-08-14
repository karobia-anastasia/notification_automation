import sys
import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)

class NotifierConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifier'

    def ready(self):
        # Avoid scheduler running during management commands that don't need it
        if any(cmd in sys.argv for cmd in [
            'makemigrations', 'migrate', 'collectstatic', 'shell',
            'createsuperuser', 'test', 'loaddata', 'dumpdata'
        ]):
            return

        # Avoid duplicate scheduler instances in development
        if os.environ.get('RUN_MAIN') != 'true':
            return

        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.interval import IntervalTrigger
            from django_apscheduler.jobstores import DjangoJobStore, register_events, register_job
            from notifier.jobs import scheduled_dispatch_job

            scheduler = BackgroundScheduler()
            scheduler.add_jobstore(DjangoJobStore(), "default")

            # Schedule the job
            scheduler.add_job(
                scheduled_dispatch_job,
                trigger=IntervalTrigger(minutes=10),
                id="dispatch_notification_job",
                name="Dispatch Notification Job",
                replace_existing=True,
            )

            register_events(scheduler)
            scheduler.start()

            logger.info("✅ APScheduler started: dispatch notification job scheduled every 10 minutes")

        except Exception as e:
            logger.error("❌ Failed to start APScheduler: %s", str(e), exc_info=True)

