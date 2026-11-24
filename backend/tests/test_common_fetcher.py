"""Tests for the shared httpx retry helper."""

from collections.abc import Callable

import httpx
import pytest

from backend.services.common_fetcher import (
    RetryPolicy,
    _backoff_delay,
    _retry_after_seconds,
    get_response_with_retries,
)

URL = "https://uk-sponsors-test.com/test"
DEFAULT_MAX_BACKOFF = RetryPolicy().backoff_max_seconds


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_success_is_returned_without_retry(sleep_spy: list[float]) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, text="payload")

    with _client(handler) as client:
        response = get_response_with_retries(client, URL)

    assert response.text == "payload"
    assert len(calls) == 1
    assert sleep_spy == []


def test_retryable_status_is_retried_then_succeeds(sleep_spy: list[float]) -> None:
    responses = iter([httpx.Response(503), httpx.Response(200, text="ok")])
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return next(responses)

    with _client(handler) as client:
        response = get_response_with_retries(client, URL)

    assert response.text == "ok"
    assert len(calls) == 2
    assert len(sleep_spy) == 1
    assert 0.25 <= sleep_spy[0] <= 0.5


def test_retryable_status_exhausts_attempts(sleep_spy: list[float]) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(503)

    with _client(handler) as client, pytest.raises(httpx.HTTPStatusError) as exc_info:
        get_response_with_retries(client, URL)

    assert exc_info.value.response.status_code == 503
    assert len(calls) == 3
    assert len(sleep_spy) == 2


def test_non_retryable_status_is_raised_immediately(sleep_spy: list[float]) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(404)

    with _client(handler) as client, pytest.raises(httpx.HTTPStatusError) as exc_info:
        get_response_with_retries(client, URL)

    assert exc_info.value.response.status_code == 404
    assert len(calls) == 1
    assert sleep_spy == []


def test_transport_error_is_retried(sleep_spy: list[float]) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ConnectError("connection dropped", request=request)
        return httpx.Response(200, text="recovered")

    with _client(handler) as client:
        response = get_response_with_retries(client, URL)

    assert response.text == "recovered"
    assert len(calls) == 2
    assert len(sleep_spy) == 1


def test_transport_error_exhausts_attempts(sleep_spy: list[float]) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise httpx.ReadTimeout("timed out", request=request)

    with _client(handler) as client, pytest.raises(httpx.ReadTimeout):
        get_response_with_retries(client, URL)

    assert len(calls) == 3
    assert len(sleep_spy) == 2


def test_unsupported_protocol_is_not_retried(sleep_spy: list[float]) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise httpx.UnsupportedProtocol("bad scheme", request=request)

    with _client(handler) as client, pytest.raises(httpx.UnsupportedProtocol):
        get_response_with_retries(client, URL)

    assert len(calls) == 1
    assert sleep_spy == []


def test_retry_after_header_controls_delay(sleep_spy: list[float]) -> None:
    responses = iter(
        [
            httpx.Response(429, headers={"Retry-After": "2"}),
            httpx.Response(200, text="ok"),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return next(responses)

    with _client(handler) as client:
        response = get_response_with_retries(client, URL)

    assert response.text == "ok"
    assert sleep_spy == [2.0]


def test_retry_after_header_is_capped_by_policy(sleep_spy: list[float]) -> None:
    responses = iter(
        [
            httpx.Response(429, headers={"Retry-After": "120"}),
            httpx.Response(200, text="ok"),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return next(responses)

    with _client(handler) as client:
        get_response_with_retries(client, URL)

    assert sleep_spy == [DEFAULT_MAX_BACKOFF]


def test_single_attempt_policy_does_not_sleep(sleep_spy: list[float]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    policy = RetryPolicy(max_attempts=1)

    with _client(handler) as client, pytest.raises(httpx.HTTPStatusError):
        get_response_with_retries(client, URL, retry_policy=policy)

    assert sleep_spy == []


def test_retry_after_seconds_parses_numeric_values() -> None:
    assert _retry_after_seconds(httpx.Response(429, headers={"Retry-After": "5"})) == 5.0
    assert _retry_after_seconds(httpx.Response(429, headers={"Retry-After": "-3"})) == 0.0


def test_retry_after_seconds_ignores_http_dates_and_missing_headers() -> None:
    http_date = httpx.Response(429, headers={"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"})

    assert _retry_after_seconds(http_date) is None
    assert _retry_after_seconds(httpx.Response(429)) is None


def test_backoff_delay_is_bounded_by_policy() -> None:
    policy = RetryPolicy(backoff_base_seconds=2.0, backoff_max_seconds=10.0)

    for attempt in range(1, 6):
        delay = _backoff_delay(attempt, policy)
        ceiling = min(policy.backoff_base_seconds * 2 ** (attempt - 1), policy.backoff_max_seconds)
        assert ceiling / 2 <= delay <= ceiling


def test_backoff_delay_honours_retry_after() -> None:
    policy = RetryPolicy(backoff_base_seconds=2.0, backoff_max_seconds=10.0)

    assert _backoff_delay(3, policy, retry_after=4.0) == 4.0
    assert _backoff_delay(3, policy, retry_after=50.0) == 10.0
    assert _backoff_delay(3, policy, retry_after=0.0) == 0.0
