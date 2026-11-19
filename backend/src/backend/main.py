import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.routes import router
from backend.config.logging_config import setup_logging
from backend.config.splash_screen import print_splash_logo

setup_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up FastAPI service")
    print_splash_logo()
    yield
    logger.info("Shutting down FastAPI service")


app = FastAPI(lifespan=lifespan)
app.include_router(router)


@app.get("/")
async def root():
    return {"message": "Hello World"}
