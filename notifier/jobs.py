
from notifier.management.commands.send_dispatch_notifications import run_dispatch_notification_job

def scheduled_dispatch_job():
    run_dispatch_notification_job()