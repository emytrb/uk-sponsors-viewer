"""Tests for CSV validation and parsing."""

from collections.abc import Callable

import pytest

from backend.config.settings import Settings
from backend.services.csv_check import check_csv, is_headers_valid, is_row_count_valid

EXPECTED_HEADERS = ["Organisation Name", "Town/City", "County", "Type & Rating", "Route"]


def test_parses_valid_csv_file(
    csv_settings: Settings,
    read_test_file: Callable[[str], str],
) -> None:
    content = read_test_file("test_file_1.csv")

    result = check_csv("test_file_1.csv", content)

    assert result.is_valid is True
    assert result.filename == "test_file_1.csv"
    assert result.row_count == 49
    assert result.rows is not None
    assert len(result.rows) == 49
    assert result.rows[0] == {
        "Organisation Name": " AaruvikA Limited",
        "Town/City": "Edinburgh",
        "County": "",
        "Type & Rating": "Worker (A rating)",
        "Route": "Skilled Worker",
    }
    assert result.checksum == ""


def test_header_only_file_is_rejected(
    csv_settings: Settings,
    read_test_file: Callable[[str], str],
) -> None:
    content = read_test_file("header.csv")

    result = check_csv("header.csv", content)

    assert result.is_valid is False
    assert result.row_count is None
    assert result.rows is None


def test_missing_expected_header_is_rejected(csv_settings: Settings) -> None:
    content = "Organisation Name,Town/City\nAcme Ltd,London\n"

    result = check_csv("missing-header.csv", content)

    assert result.is_valid is False


def test_headers_may_be_in_any_order(csv_settings: Settings) -> None:
    content = (
        "Route,County,Organisation Name,Type & Rating,Town/City\nSkilled Worker,,Acme Ltd,Worker (A rating),London\n"
    )

    result = check_csv("reordered.csv", content)

    assert result.is_valid is True
    assert result.rows == [
        {
            "Route": "Skilled Worker",
            "County": "",
            "Organisation Name": "Acme Ltd",
            "Type & Rating": "Worker (A rating)",
            "Town/City": "London",
        }
    ]


def test_quoted_fields_are_parsed(
    csv_settings: Settings,
    read_test_file: Callable[[str], str],
) -> None:
    content = read_test_file("test_file_3.csv")

    result = check_csv("test_file_3.csv", content)

    assert result.is_valid is True
    assert result.rows is not None
    assert result.row_count == 101


def test_row_count_below_threshold_is_rejected(
    csv_settings: Settings,
    read_test_file: Callable[[str], str],
) -> None:
    csv_settings.sponsors_minimum_row_count = 100

    result = check_csv("test_file_1.csv", read_test_file("test_file_1.csv"))

    assert result.is_valid is False


def test_row_count_check_can_be_disabled(
    csv_settings: Settings,
    read_test_file: Callable[[str], str],
) -> None:
    csv_settings.sponsors_minimum_row_count = 100
    csv_settings.sponsors_enable_row_check = False

    result = check_csv("test_file_1.csv", read_test_file("test_file_1.csv"))

    assert result.is_valid is True
    assert result.row_count == 49


def test_empty_content_is_rejected(csv_settings: Settings) -> None:
    result = check_csv("empty.csv", "")

    assert result.is_valid is False
    assert result.row_count is None


def test_is_headers_valid_requires_all_expected_headers(csv_settings: Settings) -> None:
    assert is_headers_valid(EXPECTED_HEADERS) is True
    assert is_headers_valid([*EXPECTED_HEADERS, "Extra"]) is True
    assert is_headers_valid(EXPECTED_HEADERS[:-1]) is False
    assert is_headers_valid(["Organisation Name", "Town/City", "County", "Route"]) is False


def test_is_row_count_valid_uses_inclusive_threshold(csv_settings: Settings) -> None:
    csv_settings.sponsors_minimum_row_count = 10

    assert is_row_count_valid(9) is False
    assert is_row_count_valid(10) is True
    assert is_row_count_valid(11) is True


def test_is_row_count_valid_skips_check_when_disabled(csv_settings: Settings) -> None:
    csv_settings.sponsors_minimum_row_count = 10
    csv_settings.sponsors_enable_row_check = False

    assert is_row_count_valid(0) is True


def test_csv_parser_preserves_leading_and_trailing_spaces(csv_settings: Settings) -> None:
    content = "Organisation Name,Town/City,County,Type & Rating,Route\n  Acme Ltd  , London ,,Worker (A rating),Skilled Worker\n"

    result = check_csv("spaces.csv", content)

    assert result.rows is not None
    assert result.rows[0]["Organisation Name"] == "  Acme Ltd  "
    assert result.rows[0]["Town/City"] == " London "


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("Town/City", True),
        (" Town/City", False),
        ("Town/City ", False),
    ],
)
def test_header_matching_is_exact(csv_settings: Settings, header: str, expected: bool) -> None:
    headers = [EXPECTED_HEADERS[0], header, *EXPECTED_HEADERS[2:]]

    assert is_headers_valid(headers) is expected
