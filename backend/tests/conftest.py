"""Shared pytest fixtures for the backend test suite."""

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from backend.config.settings import Settings, get_settings

FILES_DIR = Path(__file__).parent / "files"


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> Iterator[None]:
    """Keep ``get_settings()`` from leaking cached values between tests."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def clean_settings_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Remove every known settings env var so tests are hermetic.

    Both upper- and lower-case names are removed because pydantic-settings
    reads environment variables case-insensitively.
    """
    for field_name in Settings.model_fields:
        monkeypatch.delenv(field_name, raising=False)
        monkeypatch.delenv(field_name.upper(), raising=False)
    return monkeypatch


@pytest.fixture
def settings_factory(clean_settings_env: pytest.MonkeyPatch) -> Callable[..., Settings]:
    """Build ``Settings`` instances from explicit values only."""

    def factory(**overrides: Any) -> Settings:
        return Settings(_env_file=None, **overrides)

    return factory


@pytest.fixture
def settings(settings_factory: Callable[..., Settings]) -> Settings:
    """Settings using the application defaults, isolated from the host env."""
    return settings_factory()


@pytest.fixture
def csv_settings(settings_factory: Callable[..., Settings], monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Settings wired into ``csv_check`` with a permissive row threshold.

    ``csv_check`` captures its settings at import time, so the module attribute
    is patched instead of the environment. Tests may mutate the returned object
    to exercise other thresholds.
    """
    test_settings = settings_factory(sponsors_minimum_row_count=1)
    monkeypatch.setattr("backend.services.csv_check.settings", test_settings)
    return test_settings


@pytest.fixture(scope="session")
def test_files_dir() -> Path:
    """Directory containing the CSV fixtures."""
    return FILES_DIR


@pytest.fixture
def read_test_file() -> Callable[[str], str]:
    """Read a file from ``tests/files`` as text."""

    def read(filename: str) -> str:
        return (FILES_DIR / filename).read_text(encoding="utf-8")

    return read


@pytest.fixture
def sleep_spy(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Record retry delays instead of sleeping for real."""
    delays: list[float] = []
    monkeypatch.setattr("backend.services.common_fetcher.time.sleep", delays.append)
    return delays
