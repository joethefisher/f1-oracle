"""Tests for the centralized Kalshi client (tools/kalshi.py).

Kalshi's orderbook endpoint returns prices under `orderbook_fp` as dollar
strings (e.g. "0.3100"). This parsing previously lived (duplicated) in several
tools; when the API migrated formats, only one copy was updated and the
production path silently parsed every price to null. These tests pin the
behavior of the single shared implementation.
"""
from unittest.mock import MagicMock, patch

import pytest

from tools.kalshi import (
    best_price, parse_orderbook, compute_mid, get, paginate,
)


# Real shape observed from /markets/{ticker}/orderbook (depth=5).
SAMPLE = {
    "orderbook_fp": {
        "yes_dollars": [
            ["0.2700", "50.00"],
            ["0.2800", "122.00"],
            ["0.3100", "434.00"],
        ],
        "no_dollars": [
            ["0.6400", "184.00"],
            ["0.6700", "3394.26"],
            ["0.6800", "2571.36"],
        ],
    }
}


# ── orderbook parsing ────────────────────────────────────────────────────────

def test_best_price_takes_highest_bid():
    assert best_price([["0.2700", "50"], ["0.3100", "434"], ["0.2800", "122"]]) == 0.31


def test_best_price_empty_is_none():
    assert best_price([]) is None
    assert best_price(None) is None


def test_parse_orderbook_fp_format():
    yes_bid, yes_ask, no_bid, no_ask = parse_orderbook(SAMPLE)
    assert yes_bid == 0.31           # highest yes bid
    assert no_bid == 0.68            # highest no bid
    assert abs(yes_ask - 0.32) < 1e-9   # complement of best no bid
    assert abs(no_ask - 0.69) < 1e-9    # complement of best yes bid


def test_parse_orderbook_legacy_fallback():
    # Defensive fallback to the legacy `orderbook`/`yes`/`no` keys.
    legacy = {"orderbook": {"yes": [["0.40", "10"]], "no": [["0.55", "10"]]}}
    yes_bid, yes_ask, _, _ = parse_orderbook(legacy)
    assert yes_bid == 0.40
    assert abs(yes_ask - 0.45) < 1e-9


def test_parse_orderbook_mid_is_sane():
    yes_bid, yes_ask, _, _ = parse_orderbook(SAMPLE)
    assert abs(compute_mid(yes_bid, yes_ask) - 0.315) < 1e-9


def test_parse_orderbook_empty_book_yields_none():
    yes_bid, yes_ask, no_bid, no_ask = parse_orderbook({"orderbook_fp": {}})
    assert yes_bid is None and yes_ask is None and no_bid is None and no_ask is None


def test_parse_orderbook_one_sided():
    book = {"orderbook_fp": {"yes_dollars": [["0.1000", "10"]], "no_dollars": []}}
    yes_bid, yes_ask, no_bid, no_ask = parse_orderbook(book)
    assert yes_bid == 0.10
    assert yes_ask is None
    assert no_bid is None
    assert abs(no_ask - 0.90) < 1e-9


def test_compute_mid_one_sided():
    assert compute_mid(0.3, None) == 0.3
    assert compute_mid(None, 0.4) == 0.4
    assert compute_mid(None, None) is None


# ── HTTP client ──────────────────────────────────────────────────────────────

def _resp(status=200, payload=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload or {}
    r.raise_for_status = MagicMock()
    return r


def test_get_returns_json():
    with patch("tools.kalshi.requests.get", return_value=_resp(payload={"ok": 1})) as g:
        assert get("/markets") == {"ok": 1}
        g.assert_called_once()


def test_get_retries_on_429_then_succeeds():
    seq = [_resp(status=429), _resp(payload={"ok": 2})]
    with patch("tools.kalshi.requests.get", side_effect=seq), \
         patch("tools.kalshi.time.sleep"):
        assert get("/markets", retries=4) == {"ok": 2}


def test_get_raises_after_exhausting_retries():
    with patch("tools.kalshi.requests.get", return_value=_resp(status=429)), \
         patch("tools.kalshi.time.sleep"):
        with pytest.raises(RuntimeError):
            get("/markets", retries=2)


def test_paginate_follows_cursor():
    pages = [
        {"markets": [1, 2], "cursor": "abc"},
        {"markets": [3], "cursor": None},
    ]
    with patch("tools.kalshi.get", side_effect=pages), patch("tools.kalshi.time.sleep"):
        assert paginate("/markets", "markets") == [1, 2, 3]
