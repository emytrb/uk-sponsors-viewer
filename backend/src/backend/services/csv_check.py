import csv
import io
import logging

from backend.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CsvCheckResult:
    def __init__(
        self,
        filename: str,
        is_valid: bool,
        row_count: int | None = None,
        checksum: str | None = None,
        rows: list[dict[str, str]] | None = None,
    ):
        self.filename = filename
        self.is_valid = is_valid
        self.row_count = row_count
        self.checksum = checksum
        self.rows = rows


def check_csv(filename: str, content: str) -> CsvCheckResult:
    logger.info("Checking CSV file...")
    stream = io.StringIO(content, newline="")
    reader = csv.DictReader(stream)
    headers = list(reader.fieldnames or [])
    logger.debug(f"Found {len(headers)} header(s).")
    if not is_headers_valid(headers):
        return CsvCheckResult(filename, False)
    rows: list[dict[str, str]] = list(reader)
    if not is_row_count_valid(len(rows)):
        return CsvCheckResult(filename, False)
    return CsvCheckResult(filename, True, len(rows), "", rows)


def is_headers_valid(headers: list[str]):
    if not all(expected_header in headers for expected_header in settings.sponsors_file_expected_headers):
        logger.debug(f"Headers don't correspond to expected headers. (actual headers: {str(headers)})")
        return False
    return True


def is_row_count_valid(count: int):
    if not settings.sponsors_enable_row_check:
        return True
    if count < settings.sponsors_minimum_row_count:
        logger.debug(f"Number of rows too small. (Row count: {count})")
        return False
    return True
