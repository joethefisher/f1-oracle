"""Tests for derived, self-healing race status (tools/status.py)."""
from datetime import datetime, timedelta, timezone

from tools.status import derive_status

NOW = datetime(2026, 5, 23, 22, 0, tzinfo=timezone.utc)


def test_race_results_make_it_completed():
    # Even if scheduled far in the future, having results => completed.
    future = NOW + timedelta(days=30)
    assert derive_status(future, has_race_results=True, has_quali_results=False, now=NOW) == "completed"


def test_no_results_but_in_window_is_active():
    # Race tomorrow, no results yet — weekend in progress.
    tomorrow = NOW + timedelta(days=1)
    assert derive_status(tomorrow, has_race_results=False, has_quali_results=False, now=NOW) == "active"


def test_canada_bug_self_heals():
    # The exact Canada case: race ~21h away, no race results, quali ingested.
    # Must NOT be 'completed' (that's the corruption we're healing).
    race_dt = NOW + timedelta(hours=21)
    assert derive_status(race_dt, has_race_results=False, has_quali_results=True, now=NOW) == "active"


def test_quali_only_out_of_window_is_active():
    # Quali exists but race is far off (unusual) — still active, not upcoming.
    far = NOW + timedelta(days=20)
    assert derive_status(far, has_race_results=False, has_quali_results=True, now=NOW) == "active"


def test_far_future_no_data_is_upcoming():
    far = NOW + timedelta(days=20)
    assert derive_status(far, has_race_results=False, has_quali_results=False, now=NOW) == "upcoming"


def test_just_after_race_still_active():
    # 1 day after the race, results not yet ingested — keep active so settlement runs.
    just_after = NOW - timedelta(days=1)
    assert derive_status(just_after, has_race_results=False, has_quali_results=True, now=NOW) == "active"


def test_naive_datetime_is_tolerated():
    naive = (NOW + timedelta(days=1)).replace(tzinfo=None)
    assert derive_status(naive, has_race_results=False, has_quali_results=False, now=NOW) == "active"
