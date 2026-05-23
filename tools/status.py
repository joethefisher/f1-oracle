"""
Race status as a derived, self-healing field.

`races.status` is only a trailing/UI indicator — the orchestrator drives the
weekend phase from DB *facts* (do qualifying/race results exist?), not status.
But status still gates `find_target_race` and `race_gate.py`, so a corrupted
value can hide a race entirely (this is what happened when a premature race
ingest wrongly marked the Canadian GP 'completed' with zero results).

`reconcile_recent_races()` recomputes status from facts for all near-term races
*by date* — independent of the current status — so corruption self-heals before
anything reads status. It must run before any status-filtered query.

Truth table (no trusting the stored value):
  - race results with positions exist          -> completed
  - else within the race-weekend/date window   -> active
  - else qualifying results exist              -> active
  - else                                       -> upcoming
"""
from datetime import datetime, timedelta, timezone

# Race-weekend window: a race is "active" from a few days before until a couple
# days after its scheduled time (covers practice/quali through post-race settle).
ACTIVE_BEFORE = timedelta(days=3)
ACTIVE_AFTER = timedelta(days=2)


def derive_status(race_dt, has_race_results: bool, has_quali_results: bool,
                  now: datetime | None = None) -> str:
    """Pure status derivation from facts. No DB access — unit-testable."""
    now = now or datetime.now(timezone.utc)
    if has_race_results:
        return "completed"
    if race_dt is not None:
        if race_dt.tzinfo is None:
            race_dt = race_dt.replace(tzinfo=timezone.utc)
        if race_dt - ACTIVE_BEFORE <= now <= race_dt + ACTIVE_AFTER:
            return "active"
    if has_quali_results:
        return "active"
    return "upcoming"


def reconcile_race_status(race_id: int, now: datetime | None = None,
                          write: bool = True) -> str | None:
    """Recompute and persist one race's status from facts. Returns new status."""
    from tools.db import cursor
    with cursor() as cur:
        cur.execute("SELECT race_date_utc, status FROM races WHERE id = %s", (race_id,))
        row = cur.fetchone()
        if not row:
            return None
        race_dt, current = row
        cur.execute(
            "SELECT COUNT(*) FROM race_results WHERE race_id = %s AND position IS NOT NULL",
            (race_id,),
        )
        has_race = cur.fetchone()[0] > 0
        cur.execute(
            "SELECT COUNT(*) FROM qualifying_results WHERE race_id = %s AND position IS NOT NULL",
            (race_id,),
        )
        has_quali = cur.fetchone()[0] > 0

    new_status = derive_status(race_dt, has_race, has_quali, now)
    if write and new_status != current:
        with cursor() as cur:
            cur.execute("UPDATE races SET status = %s WHERE id = %s", (new_status, race_id))
    return new_status


def reconcile_recent_races(window_days: int = 14, now: datetime | None = None,
                           write: bool = True) -> dict[int, str]:
    """Reconcile status for every race within ±window_days of now, by DATE.

    Selecting by date (not status) is what breaks the catch-22 where a race
    wrongly marked 'completed' would never be picked up by status-filtered
    queries. Returns {race_id: new_status} for any race whose status changed.
    """
    from tools.db import cursor
    now = now or datetime.now(timezone.utc)
    with cursor() as cur:
        cur.execute(
            """SELECT id FROM races
               WHERE race_date_utc BETWEEN %s AND %s
               ORDER BY race_date_utc""",
            (now - timedelta(days=window_days), now + timedelta(days=window_days)),
        )
        race_ids = [r[0] for r in cur.fetchall()]

    changed: dict[int, str] = {}
    for rid in race_ids:
        # Re-read current to detect changes (reconcile_race_status writes if needed)
        from tools.db import cursor as _c
        with _c() as cur:
            cur.execute("SELECT status FROM races WHERE id = %s", (rid,))
            before = cur.fetchone()[0]
        after = reconcile_race_status(rid, now=now, write=write)
        if after != before:
            changed[rid] = after
    return changed
