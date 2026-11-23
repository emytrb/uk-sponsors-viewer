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


def get_page_html() -> str:
    with httpx.Client(follow_redirects=True, timeout=30.0) as client:
        response = get_response_with_retries(client, str(settings.uk_sponsors_url))
        return response.text


def get_csv_file(url: str) -> str | None:
    logger.info(f"Fetching file: {url}")
    with httpx.Client(follow_redirects=True, timeout=30.0) as client:
        response = get_response_with_retries(client, url)
        if response.is_success:
            logger.debug("File fetched successfully.")
            return response.text
        return None


def get_uk_sponsors_csv_file() -> str:
    logger.info("Beginnning CSV file fetching task...")
    page_html = get_page_html()
    for match in get_all_matching_file_urls(page_html):
        csv_url = match.group(0)
        csv_filename = match.group("filename")
        csv_file = get_csv_file(csv_url)
        if not csv_file:
            continue
        if csv_filename == LAST_FILENAME:
            continue  # TODO: stop when most recent file is the same as the last fetched file
        check_result = check_csv(csv_filename, csv_file)
        if check_result.is_valid:
            return csv_file
    raise RuntimeError("No valid CSV file found.")
