from functools import lru_cache
from typing import Literal

from pydantic import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict()
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    uk_sponsors_url: HttpUrl = HttpUrl(
        "https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers"
    )
    sponsors_sync_cron: str = "0 2 * * *"
    sponsors_file_expected_headers: list[str] = [
        "Organisation Name",
        "Town/City",
        "County",
        "Type & Rating",
        "Route",
    ]
    sponsors_enable_row_check: bool = True
    sponsors_minimum_row_count: int = 50000


@lru_cache
def get_settings() -> Settings:
    return Settings()
