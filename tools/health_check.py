"""
Independent phase-aware health watchdog.

Verifies that what *should* have happened by now actually has — markets
discovered, predictions made after qualifying, outcomes settled after the race —
and alerts via Telegram if a step is overdue. It catches the silent "ran green,
did nothing" failure that a self-reporting orchestrator can't.

Deliberately independent: imports only tools.db and tools.notify (NOT the
orchestrator or any model code), and runs on its own cron, so it fires even when
the orchestrator is the thing that's broken or never ran.

Alerts are de-duplicated via the health_alerts table: each distinct problem pings
once when it opens and once when it resolves — no every-run spam.

Usage:
    python -m tools.health_check
    python -m tools.health_check --dry-run   # evaluate + print, don't notify/write
"""
import argparse
import logging
from collections import namedtuple
from datetime import datetime, timedelta, timezone

from tools import notify
from tools.db import cursor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%SZ")
log = logging.getLogger("health_check")

Alert = namedtuple("Alert", ["severity", "key", "message"])  # severity: "warn" | "alert"

EXPECTED_MARKET_TYPES = {"race_winner", "podium", "pole"}
_EMOJI = {"warn": "⚠️", "alert": "🚨"}


# ─────────────────────────────────────────────────────────────────────────────
# Pure rules (unit-testable: facts in, alerts out)
# ─────────────────────────────────────────────────────────────────────────────

def derive_health(facts: dict, now: datetime) -> list[Alert]:
    """Evaluate expectation rules. `facts` is built by load_facts (or a test)."""
    if facts.get("no_upcoming_race"):
        return [Alert("alert", "season:no_upcoming",
                      "No upcoming race in the DB — the season needs setup.")]

    rid = facts.get("race_id")
    if rid is None:
        return []

    dt = facts["race_dt"]
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    name = facts.get("race_name") or f"race {rid}"
    alerts: list[Alert] = []

    # Markets should be discovered in the week before the race.
    if dt - timedelta(days=7) <= now <= dt - timedelta(days=1) and facts.get("missing_market_types"):
        miss = sorted(facts["missing_market_types"])
        alerts.append(Alert("warn", f"{rid}:markets_missing",
                            f"{name}: markets still missing {miss} inside the discovery window."))

    # After qualifying (and before the race is run) predictions must exist.
    if now > dt - timedelta(hours=20) and not facts.get("has_race_results") \
            and not facts.get("has_predictions"):
        alerts.append(Alert("alert", f"{rid}:no_predictions",
                            f"{name}: qualifying has passed but no predictions exist."))

    # After the race, outcomes must settle.
    if now > dt + timedelta(hours=6) and not facts.get("outcomes_settled"):
        alerts.append(Alert("alert", f"{rid}:not_settled",
                            f"{name}: race finished >6h ago but outcomes aren't settled."))

    # After settlement, a portfolio snapshot must exist.
    if now > dt + timedelta(hours=8) and facts.get("outcomes_settled") \
            and not facts.get("has_portfolio"):
        alerts.append(Alert("alert", f"{rid}:no_portfolio",
                            f"{name}: settled but no portfolio snapshot was written."))

    # During the weekend, prices should be refreshed regularly.
    age = facts.get("snapshot_age_hours")
    if dt - timedelta(days=3) <= now <= dt + timedelta(hours=2) and age is not None and age > 3:
        alerts.append(Alert("warn", f"{rid}:stale_prices",
                            f"{name}: latest Kalshi snapshot is {age:.1f}h old."))

    return alerts


# ─────────────────────────────────────────────────────────────────────────────
# DB fact loading (own minimal queries — no orchestrator import)
# ─────────────────────────────────────────────────────────────────────────────

def _scalar(cur, sql, params):
    cur.execute(sql, params)
    return cur.fetchone()[0]


def load_facts(now: datetime) -> dict:
    with cursor() as cur:
        cur.execute("""
            SELECT id, name, race_date_utc, is_sprint_weekend
            FROM races
            WHERE race_date_utc BETWEEN %s AND %s
            ORDER BY race_date_utc
            LIMIT 1
        """, (now - timedelta(days=3), now + timedelta(days=8)))
        row = cur.fetchone()

        if not row:
            has_upcoming = _scalar(
                cur, "SELECT COUNT(*) FROM races WHERE race_date_utc >= %s", (now,)
            ) > 0
            return {"no_upcoming_race": not has_upcoming, "race_id": None}

        rid, name, dt, is_sprint = row
        cur.execute("SELECT DISTINCT market_type FROM markets WHERE race_id = %s", (rid,))
        present = {r[0] for r in cur.fetchall()}
        expected = EXPECTED_MARKET_TYPES | ({"sprint"} if is_sprint else set())

        has_predictions = _scalar(cur, """
            SELECT COUNT(*) FROM predictions p JOIN markets m ON p.market_id = m.id
            WHERE m.race_id = %s AND m.market_type = 'race_winner'
        """, (rid,)) > 0
        has_race_results = _scalar(
            cur, "SELECT COUNT(*) FROM race_results WHERE race_id = %s AND position IS NOT NULL",
            (rid,)) > 0
        n_markets = _scalar(cur, "SELECT COUNT(*) FROM markets WHERE race_id = %s", (rid,))
        n_outcomes = _scalar(cur, """
            SELECT COUNT(*) FROM outcomes o JOIN markets m ON o.market_id = m.id
            WHERE m.race_id = %s
        """, (rid,))
        has_portfolio = _scalar(
            cur, "SELECT COUNT(*) FROM portfolio_snapshots WHERE race_id = %s", (rid,)) > 0
        age = _scalar(cur, """
            SELECT EXTRACT(EPOCH FROM (NOW() - MAX(s.snapshot_at))) / 3600.0
            FROM orderbook_snapshots s JOIN markets m ON s.market_id = m.id
            WHERE m.race_id = %s
        """, (rid,))

    return {
        "no_upcoming_race": False,
        "race_id": rid,
        "race_name": name,
        "race_dt": dt,
        "missing_market_types": expected - present,
        "has_predictions": has_predictions,
        "has_race_results": has_race_results,
        "outcomes_settled": n_markets > 0 and n_outcomes >= n_markets,
        "has_portfolio": has_portfolio,
        "snapshot_age_hours": float(age) if age is not None else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Dedupe + notify
# ─────────────────────────────────────────────────────────────────────────────

def _open_alerts() -> dict[str, str]:
    with cursor() as cur:
        cur.execute("SELECT check_key, message FROM health_alerts WHERE resolved_at IS NULL")
        return {r[0]: r[1] for r in cur.fetchall()}


def reconcile(alerts: list[Alert], race_id, dry_run: bool = False) -> tuple[list, list]:
    """Open new alerts, resolve cleared ones, notify once for each transition."""
    open_now = _open_alerts()
    current = {a.key: a for a in alerts}
    new = [a for a in alerts if a.key not in open_now]
    resolved = [k for k in open_now if k not in current]

    for a in new:
        msg = f"{_EMOJI.get(a.severity, '⚠️')} {a.message}"
        log.warning("NEW %s: %s", a.severity, a.message)
        if not dry_run:
            with cursor() as cur:
                cur.execute("""
                    INSERT INTO health_alerts (check_key, race_id, severity, message)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (check_key) DO UPDATE
                        SET resolved_at = NULL, message = EXCLUDED.message,
                            severity = EXCLUDED.severity, opened_at = NOW()
                """, (a.key, race_id, a.severity, a.message))
            notify.send(msg)

    for key in resolved:
        log.info("RESOLVED: %s", open_now[key])
        if not dry_run:
            with cursor() as cur:
                cur.execute(
                    "UPDATE health_alerts SET resolved_at = NOW() WHERE check_key = %s", (key,))
            notify.send(f"✅ Resolved: {open_now[key]}")

    return new, resolved


def run(dry_run: bool = False):
    now = datetime.now(timezone.utc)
    facts = load_facts(now)
    alerts = derive_health(facts, now)
    new, resolved = reconcile(alerts, facts.get("race_id"), dry_run=dry_run)
    if not alerts and not resolved:
        log.info("Health OK — nothing overdue (race_id=%s)", facts.get("race_id"))
    log.info("Health check complete: %d active, %d new, %d resolved",
             len(alerts), len(new), len(resolved))


def main():
    parser = argparse.ArgumentParser(description="F1 Oracle health watchdog")
    parser.add_argument("--dry-run", action="store_true", help="Evaluate and log, no notify/writes")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
