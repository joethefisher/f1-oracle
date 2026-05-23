"""
Correlation-aware (joint) half-Kelly bet sizing.

Bets within a race weekend are correlated: the three podium contracts compete for
three slots, and the winner is always a subset of the podium. Sizing each bet
independently (the old behavior) ignores this and over-stakes clustered bets.

Approach:
  1. Simulate full finishing orders with a Plackett-Luce model driven by the
     Oracle's win probabilities (exponential-race / Gumbel sampling). This yields
     the *joint* dependence structure across drivers and markets.
  2. For each candidate bet, derive a 0/1 outcome whose marginal equals that
     bet's own per-market Oracle probability (via a quantile cut on the driver's
     simulated finishing rank). So eligibility/edge keep using the calibrated
     per-market models, while the *correlation* comes from the shared ordering.
  3. Choose stakes that maximize expected log growth E[log(1 + Σ fᵢ·rᵢ)] over the
     simulated scenarios (concave in f), then apply the half-Kelly fraction and
     per-bet / per-weekend caps.

For a single uncorrelated bet this reduces to the classic half-Kelly fraction
0.5·(q − p)/(1 − p), matching tools.portfolio.half_kelly_bet_size.
"""
import numpy as np

from tools.portfolio import MIN_EDGE

N_SIM_DEFAULT = 20000
MAX_BET_PCT = 0.10    # cap on each final stake (fraction of bankroll)
MAX_TOTAL_PCT = 0.50  # cap on total final stake across a weekend batch
KELLY_FRACTION = 0.5  # half-Kelly


def simulate_ranks(strengths: dict, n: int = N_SIM_DEFAULT, rng=None) -> dict:
    """Plackett-Luce finishing orders via exponential-race (Gumbel) sampling.

    Returns {driver: int ndarray (n,)} of 0-indexed finishing ranks (0 == first).
    Marginal P(driver finishes first) == strengthᵢ / Σ strengths, so passing the
    Oracle win probabilities as strengths reproduces them as the win marginal.
    """
    rng = rng or np.random.default_rng()
    drivers = list(strengths)
    s = np.array([max(float(strengths[d]), 1e-12) for d in drivers])
    keys = -np.log(rng.random((n, len(drivers)))) / s   # smaller key => finishes earlier
    order = np.argsort(keys, axis=1)
    ranks = np.empty_like(order)
    rows = np.arange(n)[:, None]
    ranks[rows, order] = np.arange(len(drivers))[None, :]
    return {d: ranks[:, j] for j, d in enumerate(drivers)}


def candidate_outcomes(ranks: dict, candidates: list, rng=None) -> np.ndarray:
    """0/1 outcome matrix (n_samples, n_candidates).

    Each column's marginal equals that candidate's per-market Oracle probability:
    we take the q-fraction of scenarios in which the driver finished best (lowest
    rank), with a uniform jitter to break rank ties — preserving the joint
    dependence carried by the shared finishing order.
    """
    rng = rng or np.random.default_rng()
    if not candidates:
        return np.empty((0, 0))
    n = len(next(iter(ranks.values())))
    cols = []
    for c in candidates:
        r = ranks.get(c["driver"])
        q = float(c["oracle_prob"])
        if r is None:
            cols.append(np.zeros(n))
            continue
        q = min(max(q, 0.0), 1.0)
        key = r.astype(float) + rng.random(n) * 0.999  # jitter within a rank
        thr = np.quantile(key, q) if q > 0 else -np.inf
        cols.append((key <= thr).astype(float))
    return np.column_stack(cols)


def optimize_kelly(prices, outcomes, kelly_fraction: float = KELLY_FRACTION,
                   max_bet: float = MAX_BET_PCT, max_total: float = MAX_TOTAL_PCT):
    """Joint half-Kelly fractions of bankroll for a set of correlated bets.

    prices: (k,) Kalshi mid prices. outcomes: (n, k) 0/1 win indicators (correlated
    across columns). Returns final per-bet fractions (already scaled by
    kelly_fraction and capped per-bet then in total).
    """
    prices = np.asarray(prices, dtype=float)
    k = len(prices)
    if k == 0:
        return np.zeros(0)
    returns = outcomes / prices[None, :] - 1.0  # net return per $1 staked, per sample

    def neg_log_growth(f):
        with np.errstate(all="ignore"):
            w = 1.0 + returns @ f
            if not np.all(w > 1e-9):
                return 1e9
            return -np.mean(np.log(w))

    f_full = _maximize_log_growth(neg_log_growth, k)
    if f_full is None:
        # Fallback: independent full-Kelly per bet from simulated marginals.
        q = outcomes.mean(axis=0)
        with np.errstate(divide="ignore", invalid="ignore"):
            f_full = np.where(prices < 1.0, (q - prices) / (1.0 - prices), 0.0)
        f_full = np.clip(np.nan_to_num(f_full), 0.0, 1.0)

    f = np.clip(f_full, 0.0, None) * kelly_fraction
    f = np.minimum(f, max_bet)            # per-bet cap on final stake
    total = f.sum()
    if total > max_total:                 # per-weekend cap on total final stake
        f = f * (max_total / total)
    return f


def _maximize_log_growth(neg_obj, k):
    """SLSQP maximization of log growth; returns None to trigger the fallback."""
    try:
        from scipy.optimize import minimize, Bounds, LinearConstraint
        bounds = Bounds(np.zeros(k), np.ones(k))
        # Keep total < 1 so wealth stays positive even if every bet loses.
        total_cap = LinearConstraint(np.ones(k), 0.0, 0.95)
        x0 = np.full(k, 0.95 / k * 0.5)
        res = minimize(neg_obj, x0, method="SLSQP", bounds=bounds,
                       constraints=[total_cap], options={"maxiter": 300, "ftol": 1e-10})
        if res.success and np.all(np.isfinite(res.x)):
            return np.clip(res.x, 0.0, 1.0)
    except Exception:
        pass
    return None


def size_portfolio(candidates: list, strengths: dict, bankroll: float,
                   n: int = N_SIM_DEFAULT, rng=None,
                   kelly_fraction: float = KELLY_FRACTION,
                   max_bet: float = MAX_BET_PCT, max_total: float = MAX_TOTAL_PCT) -> list:
    """Size a batch of correlated candidate bets with joint half-Kelly.

    candidates: list of dicts with at least {market_type, driver, price (Kalshi mid),
    oracle_prob}. Returns the same list with `bet_size` (dollars) and `fraction`
    added. Only bets with a valid price and edge ≥ MIN_EDGE are sized; the rest
    get bet_size 0.
    """
    rng = rng or np.random.default_rng()
    out = [dict(c, bet_size=0.0, fraction=0.0) for c in candidates]

    eligible_idx = [
        i for i, c in enumerate(candidates)
        if c.get("price") is not None and 0.0 < c["price"] < 1.0
        and (c["oracle_prob"] - c["price"]) >= MIN_EDGE
    ]
    if not eligible_idx:
        return out

    elig = [candidates[i] for i in eligible_idx]
    ranks = simulate_ranks(strengths, n=n, rng=rng)
    outcomes = candidate_outcomes(ranks, elig, rng=rng)
    prices = np.array([c["price"] for c in elig], dtype=float)
    fracs = optimize_kelly(prices, outcomes, kelly_fraction, max_bet, max_total)

    for j, i in enumerate(eligible_idx):
        out[i]["fraction"] = float(fracs[j])
        out[i]["bet_size"] = round(float(fracs[j]) * bankroll, 2)
    return out
