"""Tests for orchestrator orderbook parsing.

Kalshi's orderbook endpoint returns prices under `orderbook_fp` as dollar
strings (e.g. "0.3100"). The orchestrator previously read the old
`orderbook`/`yes` cents format and produced all-null prices, which made the
model treat every Kalshi mid as 0 and place bets on bogus edges.
"""
from tools.orchestrate import _best_price, _parse_orderbook, _compute_mid


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


def test_best_price_takes_highest_bid():
    assert _best_price([["0.2700", "50"], ["0.3100", "434"], ["0.2800", "122"]]) == 0.31


def test_best_price_empty_is_none():
    assert _best_price([]) is None
    assert _best_price(None) is None


def test_parse_orderbook_fp_format():
    yes_bid, yes_ask, no_bid, no_ask = _parse_orderbook(SAMPLE)
    assert yes_bid == 0.31           # highest yes bid
    assert no_bid == 0.68            # highest no bid
    assert abs(yes_ask - 0.32) < 1e-9   # complement of best no bid
    assert abs(no_ask - 0.69) < 1e-9    # complement of best yes bid


def test_parse_orderbook_mid_is_sane():
    yes_bid, yes_ask, _, _ = _parse_orderbook(SAMPLE)
    mid = _compute_mid(yes_bid, yes_ask)
    assert abs(mid - 0.315) < 1e-9


def test_parse_orderbook_empty_book_yields_none():
    yes_bid, yes_ask, no_bid, no_ask = _parse_orderbook({"orderbook_fp": {}})
    assert yes_bid is None and yes_ask is None and no_bid is None and no_ask is None


def test_parse_orderbook_one_sided():
    # No resting no-side orders: yes_ask cannot be derived, but yes_bid still works.
    book = {"orderbook_fp": {"yes_dollars": [["0.1000", "10"]], "no_dollars": []}}
    yes_bid, yes_ask, no_bid, no_ask = _parse_orderbook(book)
    assert yes_bid == 0.10
    assert yes_ask is None
    assert no_bid is None
    assert abs(no_ask - 0.90) < 1e-9
