import logging
import re

logger = logging.getLogger(__name__)

# The exact URL
FULL_URL_RE = re.compile(
    r"https://assets\.publishing\.service\.gov\.uk/media/[^/\"'\s]+/"
    r"(?P<filename>SP_-_Worker_and_Temporary_Worker_Web_Register_-_\d{4}-\d{2}-\d{2}\.csv)"
)

# Any URL but with the exact filename (in case the domain changes)
FILENAME_ONLY_RE = re.compile(
    r"https?://[^\"'\s<>]+/"
    r"(?P<filename>SP_-_Worker_and_Temporary_Worker_Web_Register_-_\d{4}-\d{2}-\d{2}\.csv)"
)

# Last fallback: Any CSV file in the source code
ANY_CSV_FILE_RE = re.compile(r"https?://[^\"'\s<>]+/(?P<filename>[^/\"'\s<>]+\.csv)(?=[?#\"'<\s]|$)")

PATTERNS = [FULL_URL_RE, FILENAME_ONLY_RE, ANY_CSV_FILE_RE]


def get_all_matching_file_urls(page_html: str) -> list[re.Match[str]]:
    urls = []
    for p in PATTERNS:
        logger.info(f"Starting pattern: {p}")
        matches = list(p.finditer(page_html))
        if not matches:
            logger.info("No matches. Moving to next pattern.")
            continue
        logger.info(f"Found {len(matches)} matching file(s).")
        for match in matches:
            urls.append(match)
    return list(dict.fromkeys(urls))
