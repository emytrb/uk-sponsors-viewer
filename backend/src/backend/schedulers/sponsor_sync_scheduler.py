from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.services.sync_sponsors import sync_sponsors

sponsor_sync_scheduler = BackgroundScheduler()

sponsor_sync_scheduler.add_job(sync_sponsors, CronTrigger.from_crontab("0 2 * * *"))
