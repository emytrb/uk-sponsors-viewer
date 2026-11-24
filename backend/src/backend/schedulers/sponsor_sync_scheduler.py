from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.config.settings import get_settings
from backend.services.sync_sponsors import sync_sponsors

sponsor_sync_scheduler = BackgroundScheduler()
settings = get_settings()

sponsor_sync_scheduler.add_job(sync_sponsors, CronTrigger.from_crontab(settings.sponsors_sync_cron))
