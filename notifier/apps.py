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

    # Class-level flag to track initialization
    _scheduler_initialized = False

    def ready(self):
        """Initialize the scheduler when Django is fully ready."""
        if self._should_skip_scheduler():
            return

        # Connect only once
        if not self._scheduler_initialized:
            request_started.connect(self._initialize_scheduler, weak=False)
            self._scheduler_initialized = True

    def _should_skip_scheduler(self):
        """Determine if scheduler should be skipped based on command/mode."""
        management_commands = [
            'makemigrations', 'migrate', 'collectstatic', 'shell',
            'createsuperuser', 'test', 'loaddata', 'dumpdata',
            'flush', 'makemessages', 'compilemessages', 'runapscheduler'
        ]
        
        # Skip during management commands
        if any(cmd in sys.argv for cmd in management_commands):
            return True
            
        # Skip during runserver reload
        if os.environ.get('RUN_MAIN') != 'true' and 'runserver' in sys.argv:
            return True
            
        return False

    def _initialize_scheduler(self, sender=None, **kwargs):
        """Initialize and start the APScheduler after Django is ready."""
        # Ensure this only runs once
        if hasattr(self, '_scheduler') and getattr(self._scheduler, 'running', False):
            return

        try:
            # Ensure database connections are ready
            connections['default'].ensure_connection()
            
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.interval import IntervalTrigger
            from django_apscheduler.jobstores import DjangoJobStore, register_events
            from notifier.jobs import scheduled_dispatch_job

            # Create scheduler instance
            self._scheduler = BackgroundScheduler()
            self._scheduler.add_jobstore(DjangoJobStore(), "default")

            # Add job with proper locking
            self._scheduler.add_job(
                scheduled_dispatch_job,
                trigger=IntervalTrigger(minutes=1),
                id="dispatch_notification_job",
                name="Dispatch Notification Job",
                replace_existing=True,
                max_instances=1
            )

            register_events(self._scheduler)
            self._scheduler.start()

            logger.info("✅ APScheduler successfully started (delayed initialization)")

        except (OperationalError, ProgrammingError) as e:
            logger.warning("Database not ready for scheduler: %s", str(e))
        except Exception as e:
            logger.error("❌ Scheduler initialization failed: %s", str(e), exc_info=True)
        finally:
            request_started.disconnect(self._initialize_scheduler)
