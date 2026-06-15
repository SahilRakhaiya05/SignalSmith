from __future__ import annotations

from app.services.splunk_data_service import _extract_count, spl_for_count


def test_spl_for_count_appends_stats():
    assert spl_for_count("index=foo bar=1") == "index=foo bar=1 | stats count as count"
    assert spl_for_count("index=foo | stats count as count") == "index=foo | stats count as count"
    assert spl_for_count("index=foo | stats count by service") == "index=foo | stats count by service"


def test_extract_count_from_stats_row():
    data = {"results": [{"count": "868"}], "total_rows": 1}
    assert _extract_count(data) == 868


def test_extract_count_from_mcp_shape():
    data = {"results": [{"count": "146457"}], "truncated": False, "total_rows": 1}
    assert _extract_count(data) == 146457


def test_extract_count_returns_zero_for_event_rows_without_count_field():
    data = {
        "results": [{"service": "auth-service", "http_status": "200"}],
        "total_rows": 5,
    }
    assert _extract_count(data) == 0