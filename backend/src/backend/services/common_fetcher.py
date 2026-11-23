import logging
import random
import time

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RetryPolicy(BaseModel):
    retryable_status_codes: frozenset[int] = frozenset({408, 429, 500, 502, 503, 504})
    max_attempts: int = 3
    backoff_base_seconds: float = 0.5
    backoff_max_seconds: float = 8.0


DEFAULT_RETRY_POLICY = RetryPolicy()


def _retry_after_seconds(response: httpx.Response) -> float | None:
    """Return a numeric ``Retry-After`` header, ignoring the HTTP-date form."""
    raw = response.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        return None


def _backoff_delay(attempt: int, retry_policy: RetryPolicy, retry_after: float | None = None) -> float:
    """Exponential backoff with jitter, capped at ``BACKOFF_MAX_SECONDS``."""
    if retry_after is not None:
        return min(retry_after, retry_policy.backoff_max_seconds)
    ceiling = min(retry_policy.backoff_base_seconds * 2 ** (attempt - 1), retry_policy.backoff_max_seconds)
    return random.uniform(ceiling / 2, ceiling)


def get_response_with_retries(
    client: httpx.Client,
    url: str,
    *,
    retry_policy: RetryPolicy = DEFAULT_RETRY_POLICY,
) -> httpx.Response:
    """GET ``url``, retrying transient failures with exponential backoff.

    Retries transport errors (connect/read timeouts, dropped connections, proxy
    failures) and the retryable status codes in ``RETRYABLE_STATUS_CODES``.
    Any other status - 404, 403, ... - is raised immediately, since retrying
    cannot change the outcome. ``Retry-After`` is honoured when present.
    """
    max_attempts = max(1, retry_policy.max_attempts)
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        retry_after: float | None = None
        try:
            response = client.get(url)
        except httpx.UnsupportedProtocol as exc:
            logger.error("Request has an unusable URL %s: %s", url, exc)
            raise
        except httpx.TransportError as exc:
            last_error = exc
            logger.warning(
                "Transport/Timeout error for %s (attempt %d/%d): %s",
                url,
                attempt,
                max_attempts,
                exc,
            )
        else:
            if response.is_success:
                return response
            if response.status_code not in retry_policy.retryable_status_codes:
                logger.error(
                    "Request failed with non-retryable status %s for %s",
                    response.status_code,
                    url,
                )
                response.raise_for_status()
            last_error = httpx.HTTPStatusError(
                f"Retryable status {response.status_code} for {url}",
                request=response.request,
                response=response,
            )
            retry_after = _retry_after_seconds(response)
            logger.warning(
                "Request failed with status %s for %s (attempt %d/%d)",
                response.status_code,
                url,
                attempt,
                max_attempts,
            )

        if attempt == max_attempts:
            break
        delay = _backoff_delay(attempt, retry_policy, retry_after)
        logger.info(
            "Retrying %s in %.2fs (attempt %d/%d)",
            url,
            delay,
            attempt + 1,
            max_attempts,
        )
        time.sleep(delay)

    if last_error is None:
        raise RuntimeError(f"Request to {url} failed without raising an error")
    logger.error("Request failed after %d attempts: %s", max_attempts, url)
    raise last_error
