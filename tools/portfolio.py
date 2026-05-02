"""
Portfolio math: half-Kelly bet sizing and Kalshi mid-price calculation.
"""

MIN_EDGE = 0.05
MAX_BET_PCT = 0.10


def kalshi_mid_price(bid: float | None, ask: float | None) -> float:
    if bid is not None and ask is not None:
        return (bid + ask) / 2
    if ask is not None:
        return ask
    if bid is not None:
        return bid
    raise ValueError("no price available: both bid and ask are None")


def half_kelly_bet_size(
    oracle_prob: float,
    kalshi_mid: float,
    bankroll: float,
) -> float:
    edge = oracle_prob - kalshi_mid
    if edge < MIN_EDGE:
        return 0.0
    denominator = 1.0 - kalshi_mid
    if denominator <= 0:
        return 0.0
    kelly_fraction = edge / denominator
    bet = 0.5 * kelly_fraction * bankroll
    return round(min(bet, MAX_BET_PCT * bankroll), 2)
