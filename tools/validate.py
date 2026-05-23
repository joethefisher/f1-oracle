"""
Output validation for model predictions — loud, fail-safe sanity checks.

The podium normalization bug (probabilities normalized to sum 1 instead of 3)
lived in production silently because nothing checked the model's outputs — the
race-weekend workflow even documented the *wrong* invariant ("probs sum to ~1
per market"). These checks assert the invariants that actually matter and make a
violation impossible to miss.

Default behavior is fail-safe: on a violation the caller logs it and skips
*betting* for that market (predictions are still stored so the public site shows
the Oracle's view). Set STRICT_VALIDATION=true to hard-abort instead.
"""
import math
import os


class ValidationError(Exception):
    """Raised when validation fails and STRICT_VALIDATION is enabled."""


def _is_bad_prob(p) -> bool:
    return p is None or (isinstance(p, float) and math.isnan(p))


def validate_distribution(market_type: str, probs: list, target_sum: float,
                          tol: float | None = None) -> list[str]:
    """Return a list of problem descriptions for a market's probability vector.

    Empty list == valid. Checks: non-empty, every prob in (0, 1], no NaN/None,
    and the vector sums to its combinatorial target (1 for winner/pole, 3 for
    podium — exactly the bug that previously went unnoticed).
    """
    problems: list[str] = []
    if not probs:
        return [f"{market_type}: no predictions produced"]

    for i, p in enumerate(probs):
        if _is_bad_prob(p):
            problems.append(f"{market_type}: NaN/None probability at index {i}")
        elif not (0.0 < p <= 1.0):
            problems.append(f"{market_type}: probability {p!r} outside (0, 1] at index {i}")

    total = sum(p for p in probs if not _is_bad_prob(p))
    tol = tol if tol is not None else 0.02 * target_sum + 0.01
    if abs(total - target_sum) > tol:
        problems.append(
            f"{market_type}: probability sum {total:.4f} != target {target_sum} (tol {tol:.3f})"
        )
    return problems


def validate_prices(market_type: str, prices: list) -> list[str]:
    """Problems for prices about to be bet on: each must be a real price in (0, 1)."""
    problems: list[str] = []
    for i, m in enumerate(prices):
        if m is None or (isinstance(m, float) and math.isnan(m)):
            problems.append(f"{market_type}: NaN/None price at index {i}")
        elif not (0.0 < m < 1.0):
            problems.append(f"{market_type}: price {m!r} outside (0, 1) at index {i}")
    return problems


def is_strict() -> bool:
    return os.getenv("STRICT_VALIDATION", "false").lower() == "true"
