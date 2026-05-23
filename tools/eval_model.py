"""
Evaluate model calibration against completed race results.

Computes Brier score, log loss, and calibration buckets comparing Oracle
probabilities to actual outcomes. Uses race_results/qualifying_results
directly — does not require outcomes table to be settled.

Usage:
    python -m tools.eval_model --race-id 259
    python -m tools.eval_model --season 2026
"""
import argparse
import math
from collections import defaultdict

from rich.console import Console
from rich.table import Table

from tools.train_model import MODEL_VERSION

console = Console()

_PODIUM_POSITIONS = {1, 2, 3}

BUCKET_EDGES = [0.0, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 1.01]


def _actual_outcome(market_type: str, abbrev: str, race_res: dict, quali_res: dict) -> int:
    if market_type == "pole":
        pos = quali_res.get(abbrev)
        return 1 if pos == 1 else 0
    pos = race_res.get(abbrev)
    if pos is None:
        return 0
    if market_type == "race_winner":
        return 1 if pos == 1 else 0
    if market_type == "podium":
        return 1 if pos in _PODIUM_POSITIONS else 0
    if market_type == "sprint":
        return 1 if pos == 1 else 0
    return 0


def brier_score(probs: list[float], actuals: list[int]) -> float:
    return sum((p - y) ** 2 for p, y in zip(probs, actuals)) / len(probs)


def log_loss(probs: list[float], actuals: list[int], eps: float = 1e-7) -> float:
    return -sum(
        y * math.log(max(p, eps)) + (1 - y) * math.log(max(1 - p, eps))
        for p, y in zip(probs, actuals)
    ) / len(probs)


def calibration_buckets(probs, actuals):
    buckets: dict[int, list] = defaultdict(list)
    for p, y in zip(probs, actuals):
        for i in range(len(BUCKET_EDGES) - 1):
            if BUCKET_EDGES[i] <= p < BUCKET_EDGES[i + 1]:
                buckets[i].append((p, y))
                break
    return buckets


def _load_eval_rows(race_id: int, model_version: str):
    """Load aligned (oracle, kalshi, actual, market_type) rows for a race.

    Only predictions with a live Kalshi price are included, so Oracle and Kalshi
    are compared on the same set (predictions with no price aren't bettable and
    have nothing to compare against).
    """
    from tools.db import cursor
    with cursor() as cur:
        cur.execute("SELECT id, name FROM races WHERE id = %s", (race_id,))
        race = cur.fetchone()
        if not race:
            return None, [], [], [], []
        cur.execute(
            "SELECT oracle_probability, kalshi_mid_price, m.market_type, m.driver_abbreviation "
            "FROM predictions p JOIN markets m ON p.market_id = m.id "
            "WHERE m.race_id = %s AND p.model_version = %s AND p.kalshi_mid_price IS NOT NULL",
            (race_id, model_version),
        )
        predictions = cur.fetchall()
        cur.execute(
            "SELECT abbreviation, position FROM race_results WHERE race_id = %s AND position IS NOT NULL",
            (race_id,),
        )
        race_res = {r[0]: r[1] for r in cur.fetchall()}
        cur.execute(
            "SELECT abbreviation, position FROM qualifying_results WHERE race_id = %s AND position IS NOT NULL",
            (race_id,),
        )
        quali_res = {r[0]: r[1] for r in cur.fetchall()}

    oracle_probs, kalshi_probs, actuals, market_types = [], [], [], []
    if race_res or quali_res:
        for oracle_p, kalshi_p, mtype, abbrev in predictions:
            actuals.append(_actual_outcome(mtype, abbrev or "", race_res, quali_res))
            oracle_probs.append(float(oracle_p))
            kalshi_probs.append(float(kalshi_p))
            market_types.append(mtype)
    return race, oracle_probs, kalshi_probs, actuals, market_types


def compute_metrics(race_id: int, model_version: str = MODEL_VERSION) -> dict:
    """Structured per-market + overall Brier/log-loss for a settled race.

    Returns {} if there are no settled, priced predictions. Shape:
    {"overall": {n, oracle_brier, kalshi_brier, oracle_logloss, kalshi_logloss},
     "by_market": {market_type: {...same...}}}
    """
    _, oracle, kalshi, actuals, mtypes = _load_eval_rows(race_id, model_version)
    if not actuals:
        return {}

    def _metrics(idx):
        op = [oracle[i] for i in idx]
        kp = [kalshi[i] for i in idx]
        ya = [actuals[i] for i in idx]
        return {
            "n": len(idx),
            "oracle_brier": brier_score(op, ya),
            "kalshi_brier": brier_score(kp, ya),
            "oracle_logloss": log_loss(op, ya),
            "kalshi_logloss": log_loss(kp, ya),
        }

    by_market = {
        mt: _metrics([i for i, m in enumerate(mtypes) if m == mt])
        for mt in sorted(set(mtypes))
    }
    return {"overall": _metrics(list(range(len(actuals)))), "by_market": by_market}


def persist_metrics(race_id: int, model_version: str = MODEL_VERSION) -> int:
    """Write per-market + overall calibration metrics to model_metrics. Idempotent."""
    from tools.db import cursor
    m = compute_metrics(race_id, model_version)
    if not m:
        console.print(f"[yellow]No settled predictions to persist for race {race_id}[/]")
        return 0
    rows = [("overall", m["overall"])] + list(m["by_market"].items())
    with cursor() as cur:
        for market_type, vals in rows:
            cur.execute("""
                INSERT INTO model_metrics
                    (race_id, model_version, market_type, n,
                     oracle_brier, kalshi_brier, oracle_logloss, kalshi_logloss)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (race_id, model_version, market_type) DO UPDATE
                    SET n = EXCLUDED.n,
                        oracle_brier = EXCLUDED.oracle_brier,
                        kalshi_brier = EXCLUDED.kalshi_brier,
                        oracle_logloss = EXCLUDED.oracle_logloss,
                        kalshi_logloss = EXCLUDED.kalshi_logloss,
                        computed_at = NOW()
            """, (race_id, model_version, market_type, vals["n"],
                  round(vals["oracle_brier"], 5), round(vals["kalshi_brier"], 5),
                  round(vals["oracle_logloss"], 5), round(vals["kalshi_logloss"], 5)))
    console.print(f"[green]Persisted {len(rows)} metric rows for race {race_id}[/]")
    return len(rows)


def metrics_trend(season: int, model_version: str = MODEL_VERSION):
    """Print per-market Brier (Oracle vs Kalshi) across a season's rounds."""
    from tools.db import cursor
    with cursor() as cur:
        cur.execute("""
            SELECT r.round, mm.market_type, mm.oracle_brier, mm.kalshi_brier
            FROM model_metrics mm JOIN races r ON mm.race_id = r.id
            WHERE r.season = %s AND mm.model_version = %s AND mm.market_type != 'overall'
            ORDER BY r.round, mm.market_type
        """, (season, model_version))
        rows = cur.fetchall()
    if not rows:
        console.print(f"[yellow]No persisted metrics for {season}[/]")
        return
    t = Table(title=f"{season} Brier trend (Oracle vs Kalshi) — lower is better", header_style="bold")
    t.add_column("Round", justify="right")
    t.add_column("Market", style="cyan")
    t.add_column("Oracle Brier", justify="right")
    t.add_column("Kalshi Brier", justify="right")
    t.add_column("Edge", justify="center")
    for rnd, mt, ob, kb in rows:
        ob, kb = float(ob), float(kb)
        t.add_row(str(rnd), mt, f"{ob:.4f}", f"{kb:.4f}",
                  "[green]✓[/]" if ob < kb else "[red]✗[/]")
    console.print(t)


def eval_race(race_id: int, model_version: str = MODEL_VERSION):
    race, oracle_probs, kalshi_probs, actuals, market_types = _load_eval_rows(race_id, model_version)
    if race is None:
        console.print(f"[red]Race {race_id} not found[/]")
        return
    if not actuals:
        console.print(f"[yellow]No settled, priced {model_version} predictions for race {race_id}[/]")
        return

    console.print(f"\n[bold cyan]{race[1]} — Model {model_version} Calibration[/]")
    console.print(f"  Predictions: {len(oracle_probs)} across {len(set(market_types))} market types")
    console.print(f"  Actual wins in dataset: {sum(actuals)} / {len(actuals)}")

    # Overall metrics
    oracle_bs = brier_score(oracle_probs, actuals)
    kalshi_bs = brier_score(kalshi_probs, actuals)
    oracle_ll = log_loss(oracle_probs, actuals)
    kalshi_ll = log_loss(kalshi_probs, actuals)

    t = Table(title="Overall Metrics", show_header=True, header_style="bold")
    t.add_column("Metric", style="cyan")
    t.add_column("Oracle", justify="right")
    t.add_column("Kalshi baseline", justify="right")
    t.add_column("Better?", justify="center")
    t.add_row("Brier score ↓", f"{oracle_bs:.4f}", f"{kalshi_bs:.4f}",
              "[green]Oracle[/]" if oracle_bs < kalshi_bs else "[red]Kalshi[/]")
    t.add_row("Log loss ↓", f"{oracle_ll:.4f}", f"{kalshi_ll:.4f}",
              "[green]Oracle[/]" if oracle_ll < kalshi_ll else "[red]Kalshi[/]")
    console.print(t)

    # Per-market-type breakdown
    mt_table = Table(title="By Market Type", show_header=True, header_style="bold")
    mt_table.add_column("Market", style="cyan")
    mt_table.add_column("N", justify="right")
    mt_table.add_column("Oracle Brier ↓", justify="right")
    mt_table.add_column("Kalshi Brier ↓", justify="right")
    mt_table.add_column("Oracle LL ↓", justify="right")
    mt_table.add_column("Kalshi LL ↓", justify="right")

    for mtype in sorted(set(market_types)):
        idx = [i for i, m in enumerate(market_types) if m == mtype]
        op = [oracle_probs[i] for i in idx]
        kp = [kalshi_probs[i] for i in idx]
        y = [actuals[i] for i in idx]
        obs = brier_score(op, y)
        kbs = brier_score(kp, y)
        oll = log_loss(op, y)
        kll = log_loss(kp, y)
        mt_table.add_row(
            mtype, str(len(idx)),
            f"[green]{obs:.4f}[/]" if obs < kbs else f"[red]{obs:.4f}[/]",
            f"[green]{kbs:.4f}[/]" if kbs < obs else f"[red]{kbs:.4f}[/]",
            f"[green]{oll:.4f}[/]" if oll < kll else f"[red]{oll:.4f}[/]",
            f"[green]{kll:.4f}[/]" if kll < oll else f"[red]{kll:.4f}[/]",
        )
    console.print(mt_table)

    # Calibration buckets
    cal_table = Table(title="Calibration: Oracle Predicted vs Actual Win Rate", show_header=True, header_style="bold")
    cal_table.add_column("Pred range", style="cyan")
    cal_table.add_column("N", justify="right")
    cal_table.add_column("Mean pred", justify="right")
    cal_table.add_column("Actual %", justify="right")
    cal_table.add_column("Δ bias", justify="right")

    buckets = calibration_buckets(oracle_probs, actuals)
    for i in range(len(BUCKET_EDGES) - 1):
        items = buckets.get(i, [])
        if not items:
            continue
        mean_p = sum(p for p, _ in items) / len(items)
        actual_rate = sum(y for _, y in items) / len(items)
        bias = mean_p - actual_rate
        bias_str = f"[red]+{bias:.3f}[/]" if bias > 0.05 else (
            f"[yellow]{bias:+.3f}[/]" if abs(bias) > 0.02 else f"[green]{bias:+.3f}[/]"
        )
        lo = int(BUCKET_EDGES[i] * 100)
        hi = int(BUCKET_EDGES[i + 1] * 100)
        cal_table.add_row(
            f"{lo}–{hi}%", str(len(items)),
            f"{mean_p:.1%}", f"{actual_rate:.1%}", bias_str,
        )
    console.print(cal_table)


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--race-id", type=int)
    group.add_argument("--season", type=int)
    parser.add_argument("--model-version", default=MODEL_VERSION)
    parser.add_argument("--persist", action="store_true", help="Persist metrics to model_metrics")
    parser.add_argument("--trend", action="store_true", help="Show season Brier trend (with --season)")
    args = parser.parse_args()

    if args.race_id:
        eval_race(args.race_id, args.model_version)
        if args.persist:
            persist_metrics(args.race_id, args.model_version)
    else:
        if args.trend:
            metrics_trend(args.season, args.model_version)
            return
        from tools.db import cursor
        with cursor() as cur:
            cur.execute(
                "SELECT id FROM races WHERE season = %s AND status = 'completed' ORDER BY round",
                (args.season,),
            )
            race_ids = [r[0] for r in cur.fetchall()]
        for rid in race_ids:
            eval_race(rid, args.model_version)
            if args.persist:
                persist_metrics(rid, args.model_version)


if __name__ == "__main__":
    main()
