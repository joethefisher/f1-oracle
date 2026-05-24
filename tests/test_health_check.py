"""Tests for the health watchdog rules + dedupe (tools/health_check.py)."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from tools import health_check
from tools.health_check import Alert, derive_health

NOW = datetime(2026, 5, 24, 18, 0, tzinfo=timezone.utc)


def facts(**over):
    """Healthy baseline (race ~10h out, predictions in, prices fresh); override per test."""
    base = {
        "no_upcoming_race": False,
        "race_id": 260,
        "race_name": "Canadian GP",
        "race_dt": NOW + timedelta(hours=10),
        "missing_market_types": set(),
        "has_predictions": True,
        "has_race_results": False,
        "outcomes_settled": False,
        "has_portfolio": False,
        "snapshot_age_hours": 1.0,
    }
    base.update(over)
    return base


def keys(alerts):
    return {a.key for a in alerts}


def test_healthy_state_no_alerts():
    assert derive_health(facts(), NOW) == []


def test_no_upcoming_race_short_circuits():
    out = derive_health({"no_upcoming_race": True, "race_id": None}, NOW)
    assert len(out) == 1 and out[0].key == "season:no_upcoming"


def test_no_predictions_after_quali():
    out = derive_health(facts(has_predictions=False), NOW)
    assert "260:no_predictions" in keys(out)


def test_predictions_present_no_alert():
    assert "260:no_predictions" not in keys(derive_health(facts(has_predictions=True), NOW))


def test_not_settled_after_race():
    # Race finished 8h ago, no outcomes.
    out = derive_health(facts(race_dt=NOW - timedelta(hours=8), has_race_results=True,
                              outcomes_settled=False), NOW)
    assert "260:not_settled" in keys(out)


def test_no_portfolio_after_settlement():
    out = derive_health(facts(race_dt=NOW - timedelta(hours=10), has_race_results=True,
                              outcomes_settled=True, has_portfolio=False), NOW)
    assert "260:no_portfolio" in keys(out)


def test_markets_missing_in_discovery_window():
    out = derive_health(facts(race_dt=NOW + timedelta(days=4),
                              missing_market_types={"pole"}, has_predictions=False), NOW)
    assert "260:markets_missing" in keys(out)


def test_stale_prices_midweekend():
    out = derive_health(facts(snapshot_age_hours=5.0), NOW)
    assert "260:stale_prices" in keys(out)


def test_fresh_prices_no_warn():
    assert "260:stale_prices" not in keys(derive_health(facts(snapshot_age_hours=0.5), NOW))


# ── dedupe ───────────────────────────────────────────────────────────────────

def test_reconcile_opens_new_alert(monkeypatch):
    a = Alert("alert", "260:no_predictions", "msg")
    monkeypatch.setattr(health_check, "_open_alerts", lambda: {})
    with patch("tools.health_check.notify.send") as send:
        new, resolved = health_check.reconcile([a], 260, dry_run=True)
    assert [x.key for x in new] == ["260:no_predictions"]
    assert resolved == []
    send.assert_not_called()  # dry run never sends


def test_reconcile_dedupes_already_open(monkeypatch):
    a = Alert("alert", "260:no_predictions", "msg")
    monkeypatch.setattr(health_check, "_open_alerts", lambda: {"260:no_predictions": "msg"})
    new, resolved = health_check.reconcile([a], 260, dry_run=True)
    assert new == [] and resolved == []  # not re-notified


def test_reconcile_resolves_cleared(monkeypatch):
    monkeypatch.setattr(health_check, "_open_alerts", lambda: {"260:not_settled": "msg"})
    new, resolved = health_check.reconcile([], 260, dry_run=True)
    assert resolved == ["260:not_settled"]
