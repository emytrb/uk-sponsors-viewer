import csv
import io
import logging
import re

import httpx

logger = logging.getLogger(__name__)

UK_SPONSORS_URL = (
    "https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers"
)


EXPECTED_HEADERS = [
    "Organisation Name",
    "Town/City",
    "County",
    "Type & Rating",
    "Route",
]
# The exact URL
FULL_URL_RE = re.compile(
    r"https://assets\.publishing\.service\.gov\.uk/media/[^/\"'\s]+/SP_-_Worker_and_Temporary_Worker_Web_Register_-_\d{4}-\d{2}-\d{2}\.csv"
)

# Any URL but with the exact filename (in case the domain changes)
FILENAME_ONLY_RE = re.compile(
    r"https?://[^\"'\s<>]+/SP_-_Worker_and_Temporary_Worker_Web_Register_-_\d{4}-\d{2}-\d{2}\.csv"
)

# Last fallback: Any CSV file in the source code
ANY_CSV_FILE_RE = re.compile(r"https?://[^\"'\s<>]+\.csv(?=[?#\"'<\s]|$)")

PATTERNS = [FULL_URL_RE, FILENAME_ONLY_RE, ANY_CSV_FILE_RE]


def get_uk_sponsors_csv_file() -> str:
    logger.info("Beginnning CSV file fetching task...")
    with httpx.Client(follow_redirects=True, timeout=30.0) as client:
        response = client.get(UK_SPONSORS_URL)
        response.raise_for_status()

        for p in PATTERNS:
            logger.info(f"Starting pattern: {p}")
            matches = p.findall(response.text)
            if not matches or len(matches) == 0:
                logger.info("No matches. Moving to next pattern.")
                continue
            logger.info(f"Found {len(matches)} matching file(s).")
            for csv_url in matches:
                logger.info(f"Fetching file: {csv_url}")
                csv_file_response = client.get(csv_url)
                csv_file_response.raise_for_status()
                logger.info("Checking CSV file...")
                csv_file = csv_file_response.text
                logger.info("File fetched successfully.")
                if check_csv(csv_file):
                    return csv_file
                logger.info("File didn't pass the check. Moving to next match.")
            logger.info(
                "When through all matches of current pattern. Moving to next pattern."
            )
        raise RuntimeError("No valid CSV file found.")


def check_csv(file: str) -> bool:
    stream = io.StringIO(file, newline="")
    reader = csv.reader(stream)
    headers = next(reader, [])
    logger.info(f"Found {len(headers)} header(s).")
    row_count = sum(1 for _ in reader)
    if len(headers) != len(EXPECTED_HEADERS):
        logger.info(
            f"Number of headers don't match. (Expected: {len(EXPECTED_HEADERS)})"
        )
        return False
    if row_count < 100:
        logger.info(f"Number of rows too small. (Row count: {row_count})")
        return False

    if not all(expected_header in headers for expected_header in EXPECTED_HEADERS):
        logger.info(
            f"Headers don't correspond to expected headers. (actual headers: {str(headers)})"
        )
        return False
    return True
