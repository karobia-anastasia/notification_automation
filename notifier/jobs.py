
from asyncio.log import logger
from notifier.management.commands.send_dispatch_notifications import run_dispatch_notification_job


def scheduled_dispatch_job():
    try:
        print("🔄 [DEBUG] Job started")
        run_dispatch_notification_job()
        print("✅ [DEBUG] Job completed successfully")
    except Exception as e:
        logger.error("❌ Job failed: %s", str(e), exc_info=True)
        print(f"❌ [DEBUG] Job crashed: {e}")