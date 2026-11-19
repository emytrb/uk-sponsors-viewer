from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.services.sync_sponsors import sync_sponsors

sched = BackgroundScheduler()

sched.add_job(sync_sponsors, "cron", CronTrigger.from_crontab("0 2 * * *"))
