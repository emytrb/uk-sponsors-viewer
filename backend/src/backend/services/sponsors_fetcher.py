import logging

import httpx

from backend.config.settings import get_settings
from backend.services.common_fetcher import get_response_with_retries
from backend.services.csv_check import check_csv
from backend.services.html_parser import get_all_matching_file_urls

logger = logging.getLogger(__name__)
settings = get_settings()


# TODO: Get the filename of the last fetched file
LAST_FILENAME = ""


def get_page_html(client: httpx.Client) -> str:
    response = get_response_with_retries(client, str(settings.uk_sponsors_url))
    return response.text


def get_csv_file(client: httpx.Client, url: str) -> str:
    logger.info(f"Fetching file: {url}")
    return get_response_with_retries(client, url).text


def get_uk_sponsors_csv_file(client: httpx.Client | None = None) -> str:
    """Fetch the first valid CSV linked from the GOV.UK register page.

    One ``httpx.Client`` is shared by the page request and every candidate
    download so connections and TLS sessions are reused. A client is created
    (and closed) when the caller does not provide one.
    """
    if client is None:
        with httpx.Client(follow_redirects=True, timeout=30.0) as owned_client:
            return _get_valid_csv(owned_client)
    return _get_valid_csv(client)


def _get_valid_csv(client: httpx.Client) -> str:
    logger.info("Beginnning CSV file fetching task...")
    page_html = get_page_html(client)
    for match in get_all_matching_file_urls(page_html):
        csv_url = match.group(0)
        csv_filename = match.group("filename")
        if csv_filename == LAST_FILENAME:
            break  # TODO: check that there aren't newer files before stopping
        csv_file = None
        try:
            csv_file = get_csv_file(client, csv_url)
        except httpx.HTTPError:
            continue
        check_result = check_csv(csv_filename, csv_file)
        if check_result.is_valid:
            return csv_file
    raise RuntimeError("No valid CSV file found.")
