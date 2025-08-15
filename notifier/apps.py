import sys
import logging
from django.apps import AppConfig
import os
from django.db.utils import OperationalError, ProgrammingError
from django.db import connections
from django.core.signals import request_started

logger = logging.getLogger(__name__)

class NotifierConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifier'

    def ready(self):
        if self._should_skip_scheduler():
            return
            
        # Connect to Django's request_started signal to ensure Django is fully ready
        request_started.connect(self._initialize_scheduler, weak=False)

    def _should_skip_scheduler(self):
        """Determine if scheduler should be skipped based on command/mode."""
        management_commands = [
            'makemigrations', 'migrate', 'collectstatic', 'shell',
            'createsuperuser', 'test', 'loaddata', 'dumpdata',
            'flush', 'makemessages', 'compilemessages'
        ]
        
        if any(cmd in sys.argv for cmd in management_commands):
            return True
            
        if os.environ.get('RUN_MAIN') != 'true' and 'runserver' in sys.argv:
            return True
            
        return False

    def _initialize_scheduler(self, **kwargs):
        """Initialize and start the APScheduler after Django is ready."""
        try:
            # Ensure database connections are ready
            connections['default'].ensure_connection()
            
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.interval import IntervalTrigger
            from django_apscheduler.jobstores import DjangoJobStore, register_events
            from notifier.jobs import scheduled_dispatch_job

            scheduler = BackgroundScheduler()
            scheduler.add_jobstore(DjangoJobStore(), "default")

            scheduler.add_job(
                scheduled_dispatch_job,
                trigger=IntervalTrigger(minutes=1),
                id="dispatch_notification_job",
                name="Dispatch Notification Job",
                replace_existing=True,
            )

            register_events(scheduler)
            scheduler.start()

            logger.info("✅ APScheduler successfully started (delayed initialization)")

        except (OperationalError, ProgrammingError) as e:
            logger.warning("Database not ready for scheduler: %s", str(e))
        except Exception as e:
            logger.error("❌ Scheduler initialization failed: %s", str(e), exc_info=True)