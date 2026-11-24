"""Tests for the pydantic-settings configuration."""

import pytest
from pydantic import HttpUrl, ValidationError

from backend.config.settings import Settings, get_settings


def test_settings_defaults(settings: Settings) -> None:
    assert settings.log_level == "INFO"
    assert settings.uk_sponsors_url == HttpUrl(
        "https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers"
    )
    assert settings.sponsors_sync_cron == "0 2 * * *"
    assert settings.sponsors_file_expected_headers == [
        "Organisation Name",
        "Town/City",
        "County",
        "Type & Rating",
        "Route",
    ]
    assert settings.sponsors_enable_row_check is True
    assert settings.sponsors_minimum_row_count == 50000


def test_settings_read_from_environment(clean_settings_env: pytest.MonkeyPatch) -> None:
    clean_settings_env.setenv("LOG_LEVEL", "DEBUG")
    clean_settings_env.setenv("UK_SPONSORS_URL", "https://example.com/register")
    clean_settings_env.setenv("SPONSORS_SYNC_CRON", "15 3 * * 1")
    clean_settings_env.setenv("SPONSORS_ENABLE_ROW_CHECK", "false")
    clean_settings_env.setenv("SPONSORS_MINIMUM_ROW_COUNT", "42")

    settings = Settings(_env_file=None)

    assert settings.log_level == "DEBUG"
    assert str(settings.uk_sponsors_url) == "https://example.com/register"
    assert settings.sponsors_sync_cron == "15 3 * * 1"
    assert settings.sponsors_enable_row_check is False
    assert settings.sponsors_minimum_row_count == 42


def test_settings_parse_list_environment_variable(clean_settings_env: pytest.MonkeyPatch) -> None:
    clean_settings_env.setenv("SPONSORS_FILE_EXPECTED_HEADERS", '["Name", "City"]')

    settings = Settings(_env_file=None)

    assert settings.sponsors_file_expected_headers == ["Name", "City"]


def test_invalid_sponsors_url_is_rejected(settings_factory) -> None:
    with pytest.raises(ValidationError):
        settings_factory(uk_sponsors_url="not-a-url")


def test_get_settings_is_cached(clean_settings_env: pytest.MonkeyPatch) -> None:
    clean_settings_env.setenv("LOG_LEVEL", "ERROR")

    first = get_settings()
    second = get_settings()

    assert first is second
    assert first.log_level == "ERROR"


def test_cache_clear_picks_up_new_environment(clean_settings_env: pytest.MonkeyPatch) -> None:
    clean_settings_env.setenv("LOG_LEVEL", "ERROR")
    assert get_settings().log_level == "ERROR"

    clean_settings_env.setenv("LOG_LEVEL", "DEBUG")
    assert get_settings().log_level == "ERROR"

    get_settings.cache_clear()
    assert get_settings().log_level == "DEBUG"
