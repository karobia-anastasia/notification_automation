from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django_apscheduler.jobstores import DjangoJobStore, register_events, register_job
import logging
import time

logger = logging.getLogger(__name__)

def my_scheduled_job():
    logger.info("Running my scheduled job...")
    # Your logic here

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")

    @register_job(scheduler, IntervalTrigger(seconds=30), name="My Job", jobstore='default')
    def job_wrapper():
        my_scheduled_job()

    register_events(scheduler)
    scheduler.start()

    logger.info("Scheduler started...")
