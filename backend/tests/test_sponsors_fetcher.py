"""Tests for the GOV.UK sponsors fetcher."""

from collections.abc import Callable

import httpx
import pytest

from backend.config.settings import Settings
from backend.services import sponsors_fetcher
from backend.services.sponsors_fetcher import get_csv_file, get_page_html, get_uk_sponsors_csv_file

ASSET_BASE = "https://assets.publishing.service.gov.uk/media/some-media-id"
FILENAME = "SP_-_Worker_and_Temporary_Worker_Web_Register_-_{date}.csv"
CSV_PATH_MARKER = "SP_-_Worker_and_Temporary_Worker_Web_Register_-_"


def _csv_url(date: str) -> str:
    return f"{ASSET_BASE}/{FILENAME.format(date=date)}"


def _page_html(*csv_urls: str) -> str:
    links = "".join(f'<a href="{url}">Download CSV</a>' for url in csv_urls)
    return f"<html><body>{links}</body></html>"


@pytest.fixture
def install_mock_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[Callable[[httpx.Request], httpx.Response]], None]:
    """Route ``httpx.Client`` requests in ``sponsors_fetcher`` to a handler."""

    def install(handler: Callable[[httpx.Request], httpx.Response]) -> None:
        transport = httpx.MockTransport(handler)
        real_client = httpx.Client

        def client_factory(*args: object, **kwargs: object) -> httpx.Client:
            kwargs.pop("transport", None)
            return real_client(*args, transport=transport, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(sponsors_fetcher.httpx, "Client", client_factory)

    return install


def test_get_page_html_returns_response_text(
    install_mock_client: Callable[[Callable[[httpx.Request], httpx.Response]], None],
) -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(200, text="<html>register page</html>")

    install_mock_client(handler)

    assert get_page_html() == "<html>register page</html>"
    assert requested == [str(sponsors_fetcher.settings.uk_sponsors_url)]


def test_get_page_html_retries_transient_failures(
    install_mock_client: Callable[[Callable[[httpx.Request], httpx.Response]], None],
    sleep_spy: list[float],
) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(503)
        return httpx.Response(200, text="<html>ok</html>")

    install_mock_client(handler)

    assert get_page_html() == "<html>ok</html>"
    assert len(calls) == 2
    assert len(sleep_spy) == 1


def test_get_csv_file_returns_response_text(
    install_mock_client: Callable[[Callable[[httpx.Request], httpx.Response]], None],
    read_test_file: Callable[[str], str],
) -> None:
    expected = read_test_file("test_file_2.csv")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=expected)

    install_mock_client(handler)

    assert get_csv_file(_csv_url("2026-11-20")) == expected


def test_get_uk_sponsors_csv_file_returns_first_valid_csv(
    install_mock_client: Callable[[Callable[[httpx.Request], httpx.Response]], None],
    csv_settings: Settings,
    read_test_file: Callable[[str], str],
) -> None:
    valid_csv = read_test_file("test_file_2.csv")
    csv_url = _csv_url("2026-11-20")
    page = _page_html(csv_url)
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        if CSV_PATH_MARKER in request.url.path:
            return httpx.Response(200, text=valid_csv)
        return httpx.Response(200, text=page)

    install_mock_client(handler)

    assert get_uk_sponsors_csv_file() == valid_csv
    assert any(path.endswith(FILENAME.format(date="2026-11-20")) for path in requested)
    assert sum(path.endswith(".csv") for path in requested) >= 1


def test_get_uk_sponsors_csv_file_skips_invalid_csvs(
    install_mock_client: Callable[[Callable[[httpx.Request], httpx.Response]], None],
    csv_settings: Settings,
    read_test_file: Callable[[str], str],
) -> None:
    invalid_csv = "Organisation Name\nAcme Ltd\n"
    valid_csv = read_test_file("test_file_3.csv")
    invalid_url = _csv_url("2026-11-18")
    valid_url = _csv_url("2026-11-20")
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        if request.url.path.endswith(FILENAME.format(date="2026-11-18")):
            return httpx.Response(200, text=invalid_csv)
        if request.url.path.endswith(FILENAME.format(date="2026-11-20")):
            return httpx.Response(200, text=valid_csv)
        return httpx.Response(200, text=_page_html(invalid_url, valid_url))

    install_mock_client(handler)

    assert get_uk_sponsors_csv_file() == valid_csv
    assert any(path.endswith(FILENAME.format(date="2026-11-18")) for path in requested)
    assert any(path.endswith(FILENAME.format(date="2026-11-20")) for path in requested)


def test_get_uk_sponsors_csv_file_raises_when_no_csv_link(
    install_mock_client: Callable[[Callable[[httpx.Request], httpx.Response]], None],
    csv_settings: Settings,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html><body>No downloads here</body></html>")

    install_mock_client(handler)

    with pytest.raises(RuntimeError, match="No valid CSV file found"):
        get_uk_sponsors_csv_file()


def test_get_uk_sponsors_csv_file_raises_when_all_csvs_invalid(
    install_mock_client: Callable[[Callable[[httpx.Request], httpx.Response]], None],
    csv_settings: Settings,
    read_test_file: Callable[[str], str],
) -> None:
    header_only = read_test_file("header.csv")
    page = _page_html(_csv_url("2026-11-20"))

    def handler(request: httpx.Request) -> httpx.Response:
        if CSV_PATH_MARKER in request.url.path:
            return httpx.Response(200, text=header_only)
        return httpx.Response(200, text=page)

    install_mock_client(handler)

    with pytest.raises(RuntimeError, match="No valid CSV file found"):
        get_uk_sponsors_csv_file()


def test_get_uk_sponsors_csv_file_skips_last_fetched_filename(
    install_mock_client: Callable[[Callable[[httpx.Request], httpx.Response]], None],
    csv_settings: Settings,
    read_test_file: Callable[[str], str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    filename = FILENAME.format(date="2026-11-20")
    monkeypatch.setattr(sponsors_fetcher, "LAST_FILENAME", filename)

    def handler(request: httpx.Request) -> httpx.Response:
        if CSV_PATH_MARKER in request.url.path:
            return httpx.Response(200, text=read_test_file("test_file_2.csv"))
        return httpx.Response(200, text=_page_html(_csv_url("2026-11-20")))

    install_mock_client(handler)

    with pytest.raises(RuntimeError, match="No valid CSV file found"):
        get_uk_sponsors_csv_file()
