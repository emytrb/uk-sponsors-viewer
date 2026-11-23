import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Path

from backend.api.routes import router
from backend.config.logging_config import setup_logging
from backend.config.settings import get_settings
from backend.schedulers.sponsor_sync_scheduler import sponsor_sync_scheduler

BANNER_PATH = Path(__file__).resolve().parent / "assets" / "banner.txt"


def print_banner() -> None:
    if BANNER_PATH.exists():
        banner = BANNER_PATH.read_text(encoding="utf-8")
        print(f"\n{banner}\n")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(get_settings().log_level)
    logger = logging.getLogger(__name__)
    logger.info("Starting up FastAPI service")
    start_schedulers()
    print_banner()
    yield
    logger.info("Shutting down FastAPI service")


app = FastAPI(lifespan=lifespan)
app.include_router(router)


def start_schedulers() -> None:
    sponsor_sync_scheduler.start()


@app.get("/")
async def root():
    return {"message": "Hello World"}
