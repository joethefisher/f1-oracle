# Phase 1 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the database schema, shared DB connection module, FastF1 ingestion pipeline, and wire market discovery + order book snapshots into the database so the rest of the system has a reliable data foundation.

**Architecture:** A shared `tools/db.py` module owns all Postgres connection logic and is imported by every tool. `tools/db_init.py` creates all tables idempotently. Ingestion tools write structured data to Postgres. All tools fail fast with a clear error if `DATABASE_URL` is not set.

**Tech Stack:** Python 3.14, psycopg2-binary, FastF1, pytest, python-dotenv, rich

---

## File Map

| File | Role |
|------|------|
| `tools/db.py` | Shared DB connection, cursor context manager |
| `tools/db_init.py` | Create all tables (idempotent) |
| `tools/db_verify.py` | Print table names + row counts |
| `tools/ingest_fastf1.py` | Pull qualifying + race sessions from FastF1 → DB |
| `tools/ingest_historical.py` | Pull last 3 seasons of circuit results → DB |
| `tools/save_markets.py` | Write discovered Kalshi markets → DB |
| `tools/snapshot_orderbook.py` | Extended: also write snapshots to DB |
| `tests/test_db_init.py` | Schema creation tests (mocked connection) |
| `tests/test_ingest_fastf1.py` | FastF1 ingestion tests (mocked FastF1) |
| `tests/test_portfolio_math.py` | Half-Kelly formula unit tests (no DB needed) |
| `requirements.txt` | Add fastf1, psycopg2-binary, pytest, numpy, pandas |

---

## Task 1: Update dependencies and test infrastructure

**Files:**
- Modify: `requirements.txt`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Update requirements.txt**

```
requests==2.32.3
python-dotenv==1.0.1
rich==13.9.4
fastf1==3.4.0
psycopg2-binary==2.9.9
pytest==8.3.4
pytest-mock==3.14.0
numpy==2.2.5
pandas==2.2.3
```

- [ ] **Step 2: Install updated dependencies**

Run: `.venv/bin/pip install -q -r requirements.txt`
Expected: all packages install without error

- [ ] **Step 3: Create tests/__init__.py**

Empty file — makes `tests/` a package.

```python
```

- [ ] **Step 4: Create tests/conftest.py**

```python
import os
import pytest

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "requires_db: mark test as requiring a live DATABASE_URL"
    )

def pytest_runtest_setup(item):
    if item.get_closest_marker("requires_db"):
        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not set — skipping DB integration test")
```

- [ ] **Step 5: Verify pytest discovers tests**

Run: `.venv/bin/pytest tests/ --collect-only`
Expected: "no tests ran" (no test files yet — confirms collection works)

- [ ] **Step 6: Commit**

```bash
git add requirements.txt tests/
git commit -m "feat: add test infrastructure and extend dependencies"
```

---

## Task 2: Shared DB connection module

**Files:**
- Create: `tools/db.py`
- Create: `tests/test_db_init.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_db_init.py`:

```python
import pytest
from unittest.mock import patch, MagicMock, call
import psycopg2


def test_get_connection_raises_without_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from tools.db import get_connection
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        get_connection()


def test_get_connection_uses_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    with patch("psycopg2.connect") as mock_connect:
        mock_connect.return_value = MagicMock()
        from tools import db
        import importlib
        importlib.reload(db)
        conn = db.get_connection()
        mock_connect.assert_called_once_with("postgresql://user:pass@host/db")


def test_cursor_context_manager(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("psycopg2.connect", return_value=mock_conn):
        from tools import db
        import importlib
        importlib.reload(db)
        with db.cursor() as cur:
            assert cur is mock_cursor
        mock_conn.commit.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_db_init.py -v`
Expected: ImportError — `tools/db.py` does not exist yet

- [ ] **Step 3: Create tools/db.py**

```python
import os
from contextlib import contextmanager

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set. Add it to .env")
    return psycopg2.connect(url)


@contextmanager
def cursor():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_db_init.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add tools/db.py tests/test_db_init.py
git commit -m "feat: add shared DB connection module with tests"
```

---

## Task 3: Database schema (db_init.py)

**Files:**
- Create: `tools/db_init.py`

- [ ] **Step 1: Write the failing test** (add to `tests/test_db_init.py`)

```python
def test_init_creates_all_tables(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__ = lambda s: mock_conn
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("psycopg2.connect", return_value=mock_conn):
        from tools import db
        import importlib
        importlib.reload(db)
        import tools.db_init as db_init
        importlib.reload(db_init)
        db_init.init_db()

    executed_sql = " ".join(
        str(c.args[0]) for c in mock_cursor.execute.call_args_list
    )
    for table in ["races", "markets", "predictions", "virtual_bets", "outcomes", "portfolio_snapshots"]:
        assert table in executed_sql, f"Expected CREATE TABLE for {table}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_db_init.py::test_init_creates_all_tables -v`
Expected: ImportError or AttributeError

- [ ] **Step 3: Create tools/db_init.py**

```python
"""
Create all F1 Oracle database tables. Safe to run multiple times (idempotent).

Usage:
    python tools/db_init.py
"""

from tools.db import cursor
from rich.console import Console

console = Console()

SCHEMA = """
CREATE TABLE IF NOT EXISTS races (
    id          SERIAL PRIMARY KEY,
    season      INTEGER NOT NULL,
    round       INTEGER NOT NULL,
    name        TEXT NOT NULL,
    circuit     TEXT NOT NULL,
    race_date_utc TIMESTAMPTZ,
    is_sprint_weekend BOOLEAN DEFAULT FALSE,
    status      TEXT NOT NULL DEFAULT 'upcoming',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (season, round)
);

CREATE TABLE IF NOT EXISTS markets (
    id                  SERIAL PRIMARY KEY,
    race_id             INTEGER REFERENCES races(id),
    kalshi_ticker       TEXT NOT NULL UNIQUE,
    kalshi_event_ticker TEXT NOT NULL,
    market_type         TEXT NOT NULL,
    driver_name         TEXT,
    status              TEXT NOT NULL DEFAULT 'open',
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS predictions (
    id                  SERIAL PRIMARY KEY,
    market_id           INTEGER REFERENCES markets(id),
    oracle_probability  NUMERIC(6,4) NOT NULL,
    kalshi_mid_price    NUMERIC(6,4) NOT NULL,
    edge                NUMERIC(6,4) NOT NULL,
    predicted_at        TIMESTAMPTZ DEFAULT NOW(),
    model_version       TEXT NOT NULL DEFAULT 'v1'
);

CREATE TABLE IF NOT EXISTS virtual_bets (
    id                  SERIAL PRIMARY KEY,
    prediction_id       INTEGER REFERENCES predictions(id),
    bet_size_dollars    NUMERIC(10,2) NOT NULL,
    kelly_fraction      NUMERIC(8,6) NOT NULL,
    bankroll_at_time    NUMERIC(10,2) NOT NULL,
    placed_at           TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS outcomes (
    id              SERIAL PRIMARY KEY,
    market_id       INTEGER REFERENCES markets(id) UNIQUE,
    winning_side    TEXT NOT NULL,
    settled_at      TIMESTAMPTZ DEFAULT NOW(),
    source          TEXT NOT NULL DEFAULT 'fastf1'
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id                      SERIAL PRIMARY KEY,
    race_id                 INTEGER REFERENCES races(id) UNIQUE,
    bankroll_after          NUMERIC(10,2) NOT NULL,
    return_pct              NUMERIC(8,4) NOT NULL,
    kalshi_baseline_value   NUMERIC(10,2),
    snapshot_at             TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS race_results (
    id              SERIAL PRIMARY KEY,
    race_id         INTEGER REFERENCES races(id),
    driver_number   TEXT,
    abbreviation    TEXT,
    driver_name     TEXT NOT NULL,
    team_name       TEXT,
    position        INTEGER,
    grid_position   INTEGER,
    status          TEXT,
    points          NUMERIC(6,2),
    UNIQUE (race_id, driver_number)
);

CREATE TABLE IF NOT EXISTS qualifying_results (
    id              SERIAL PRIMARY KEY,
    race_id         INTEGER REFERENCES races(id),
    driver_number   TEXT,
    abbreviation    TEXT,
    driver_name     TEXT NOT NULL,
    team_name       TEXT,
    position        INTEGER,
    grid_position   INTEGER,
    status          TEXT,
    points          NUMERIC(6,2),
    UNIQUE (race_id, driver_number)
);
"""


def init_db():
    with cursor() as cur:
        cur.execute(SCHEMA)
    console.print("[green]Schema created successfully.[/]")


if __name__ == "__main__":
    init_db()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_db_init.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add tools/db_init.py tests/test_db_init.py
git commit -m "feat: add database schema with idempotent init"
```

---

## Task 4: DB verify tool

**Files:**
- Create: `tools/db_verify.py`

- [ ] **Step 1: Create tools/db_verify.py**

```python
"""
Verify database schema by printing table names and row counts.

Usage:
    python tools/db_verify.py
"""

from tools.db import cursor
from rich.console import Console
from rich.table import Table

TABLES = ["races", "markets", "predictions", "virtual_bets", "outcomes", "portfolio_snapshots"]
console = Console()


def verify_db():
    table = Table(title="Database Status")
    table.add_column("Table", style="cyan")
    table.add_column("Rows", justify="right")

    with cursor() as cur:
        for t in TABLES:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                count = cur.fetchone()[0]
                table.add_row(t, str(count))
            except Exception as e:
                table.add_row(t, f"[red]ERROR: {e}[/]")

    console.print(table)


if __name__ == "__main__":
    verify_db()
```

- [ ] **Step 2: Commit**

```bash
git add tools/db_verify.py
git commit -m "feat: add db_verify tool"
```

---

## Task 5: Half-Kelly portfolio math (pure unit tests, no DB)

**Files:**
- Create: `tools/portfolio.py`
- Create: `tests/test_portfolio_math.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_portfolio_math.py`:

```python
from tools.portfolio import half_kelly_bet_size, kalshi_mid_price


def test_half_kelly_no_bet_below_min_edge():
    # Edge is 4% — below 5% threshold — should return 0
    result = half_kelly_bet_size(
        oracle_prob=0.32,
        kalshi_mid=0.28,
        bankroll=1000.0,
    )
    assert result == 0.0


def test_half_kelly_bet_size_basic():
    # Oracle 35%, Kalshi 28% → edge 7%
    # kelly = 0.07 / (1 - 0.28) = 0.07 / 0.72 ≈ 0.0972
    # half_kelly = 0.0486
    # bet = 0.0486 * 1000 = $48.61
    result = half_kelly_bet_size(
        oracle_prob=0.35,
        kalshi_mid=0.28,
        bankroll=1000.0,
    )
    assert abs(result - 48.61) < 0.1


def test_half_kelly_capped_at_10_pct_bankroll():
    # Very large edge should be capped at 10% of bankroll = $100
    result = half_kelly_bet_size(
        oracle_prob=0.90,
        kalshi_mid=0.10,
        bankroll=1000.0,
    )
    assert result == 100.0


def test_half_kelly_zero_edge_exactly():
    result = half_kelly_bet_size(
        oracle_prob=0.28,
        kalshi_mid=0.28,
        bankroll=1000.0,
    )
    assert result == 0.0


def test_kalshi_mid_price_both_sides():
    assert kalshi_mid_price(bid=0.25, ask=0.30) == 0.275


def test_kalshi_mid_price_ask_only():
    # No bid — use ask only
    assert kalshi_mid_price(bid=None, ask=0.30) == 0.30


def test_kalshi_mid_price_neither_raises():
    import pytest
    with pytest.raises(ValueError, match="no price"):
        kalshi_mid_price(bid=None, ask=None)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_portfolio_math.py -v`
Expected: ImportError — `tools/portfolio.py` does not exist

- [ ] **Step 3: Create tools/portfolio.py**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_portfolio_math.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add tools/portfolio.py tests/test_portfolio_math.py
git commit -m "feat: add half-Kelly bet sizing with unit tests"
```

---

## Task 6: FastF1 ingestion — race results

**Files:**
- Create: `tools/ingest_fastf1.py`
- Create: `tests/test_ingest_fastf1.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_ingest_fastf1.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd


def make_mock_session(session_type="R"):
    session = MagicMock()
    session.event = {
        "EventName": "Miami Grand Prix",
        "Circuit": {"ShortName": "Miami"},
        "RoundNumber": 6,
    }
    session.date = pd.Timestamp("2026-05-04 20:00:00")

    results = pd.DataFrame({
        "DriverNumber": ["4", "44", "16"],
        "Abbreviation": ["NOR", "HAM", "LEC"],
        "FullName": ["Lando Norris", "Lewis Hamilton", "Charles Leclerc"],
        "TeamName": ["McLaren", "Ferrari", "Ferrari"],
        "Position": [1, 2, 3],
        "GridPosition": [1, 3, 2],
        "Status": ["Finished", "Finished", "Finished"],
        "Points": [25, 18, 15],
    })
    session.results = results
    session.name = "Race" if session_type == "R" else "Qualifying"
    return session


def test_parse_race_results_returns_list_of_dicts():
    from tools.ingest_fastf1 import parse_results
    session = make_mock_session("R")
    rows = parse_results(session, season=2026, round_num=6)
    assert len(rows) == 3
    assert rows[0]["driver_name"] == "Lando Norris"
    assert rows[0]["position"] == 1
    assert rows[0]["season"] == 2026
    assert rows[0]["round"] == 6


def test_parse_qualifying_results_uses_grid_position():
    from tools.ingest_fastf1 import parse_results
    session = make_mock_session("Q")
    rows = parse_results(session, season=2026, round_num=6, session_type="Q")
    assert rows[1]["grid_position"] == 3


def test_parse_results_handles_missing_points_column():
    from tools.ingest_fastf1 import parse_results
    session = make_mock_session("R")
    session.results = session.results.drop(columns=["Points"])
    rows = parse_results(session, season=2026, round_num=6)
    assert rows[0].get("points") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_ingest_fastf1.py -v`
Expected: ImportError — `tools/ingest_fastf1.py` does not exist

- [ ] **Step 3: Create tools/ingest_fastf1.py**

```python
"""
Ingest F1 session data from FastF1 into the database.

Usage:
    python tools/ingest_fastf1.py --season 2026 --round 6 --session R
    python tools/ingest_fastf1.py --season 2026 --round 6 --session Q

Sessions: R=Race, Q=Qualifying, S=Sprint, SQ=Sprint Qualifying
"""

import argparse
import sys
from typing import Any

import fastf1
import pandas as pd
from rich.console import Console

from tools.db import cursor

console = Console()
fastf1.Cache.enable_cache(".tmp/fastf1_cache")


def parse_results(session, season: int, round_num: int, session_type: str = "R") -> list[dict[str, Any]]:
    rows = []
    for _, driver in session.results.iterrows():
        row: dict[str, Any] = {
            "season": season,
            "round": round_num,
            "session_type": session_type,
            "driver_number": str(driver.get("DriverNumber", "")),
            "abbreviation": str(driver.get("Abbreviation", "")),
            "driver_name": str(driver.get("FullName", "")),
            "team_name": str(driver.get("TeamName", "")),
            "position": int(driver["Position"]) if pd.notna(driver.get("Position")) else None,
            "grid_position": int(driver["GridPosition"]) if pd.notna(driver.get("GridPosition")) else None,
            "status": str(driver.get("Status", "")),
            "points": float(driver["Points"]) if "Points" in driver.index and pd.notna(driver.get("Points")) else None,
        }
        rows.append(row)
    return rows


def load_session(season: int, round_num: int, session_type: str):
    console.print(f"Loading FastF1: season={season} round={round_num} session={session_type}")
    session = fastf1.get_session(season, round_num, session_type)
    session.load(telemetry=False, weather=False, messages=False)
    return session


def upsert_race(season: int, round_num: int, session) -> int:
    event = session.event
    name = event.get("EventName", f"Round {round_num}")
    circuit = event.get("Circuit", {}).get("ShortName", "Unknown") if isinstance(event.get("Circuit"), dict) else str(event.get("OfficialEventName", "Unknown"))
    race_date = session.date.isoformat() if hasattr(session.date, "isoformat") else str(session.date)

    with cursor() as cur:
        cur.execute("""
            INSERT INTO races (season, round, name, circuit, race_date_utc, status)
            VALUES (%s, %s, %s, %s, %s, 'completed')
            ON CONFLICT (season, round) DO UPDATE
                SET name = EXCLUDED.name,
                    circuit = EXCLUDED.circuit,
                    race_date_utc = EXCLUDED.race_date_utc,
                    status = 'completed'
            RETURNING id
        """, (season, round_num, name, circuit, race_date))
        race_id = cur.fetchone()[0]
    return race_id


def upsert_results(rows: list[dict], race_id: int, session_type: str):
    table = "race_results" if session_type == "R" else "qualifying_results"
    with cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id              SERIAL PRIMARY KEY,
                race_id         INTEGER REFERENCES races(id),
                driver_number   TEXT,
                abbreviation    TEXT,
                driver_name     TEXT NOT NULL,
                team_name       TEXT,
                position        INTEGER,
                grid_position   INTEGER,
                status          TEXT,
                points          NUMERIC(6,2),
                UNIQUE (race_id, driver_number)
            )
        """)
        for row in rows:
            cur.execute(f"""
                INSERT INTO {table}
                    (race_id, driver_number, abbreviation, driver_name, team_name,
                     position, grid_position, status, points)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (race_id, driver_number) DO UPDATE
                    SET position = EXCLUDED.position,
                        grid_position = EXCLUDED.grid_position,
                        status = EXCLUDED.status,
                        points = EXCLUDED.points
            """, (
                race_id, row["driver_number"], row["abbreviation"], row["driver_name"],
                row["team_name"], row["position"], row["grid_position"],
                row["status"], row["points"],
            ))
    console.print(f"[green]Upserted {len(rows)} rows into {table}[/]")


def ingest(season: int, round_num: int, session_type: str = "R"):
    session = load_session(season, round_num, session_type)
    rows = parse_results(session, season, round_num, session_type)
    race_id = upsert_race(season, round_num, session)
    upsert_results(rows, race_id, session_type)
    console.print(f"[green]Ingested {season} R{round_num} ({session_type}) — {len(rows)} drivers[/]")


def main():
    parser = argparse.ArgumentParser(description="Ingest F1 session data from FastF1")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--round", type=int, required=True, dest="round_num")
    parser.add_argument("--session", default="R", choices=["R", "Q", "S", "SQ"])
    args = parser.parse_args()
    ingest(args.season, args.round_num, args.session)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_ingest_fastf1.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add tools/ingest_fastf1.py tests/test_ingest_fastf1.py
git commit -m "feat: add FastF1 ingestion tool with parse tests"
```

---

## Task 7: Save discovered markets to DB

**Files:**
- Create: `tools/save_markets.py`
- Create: `tests/test_save_markets.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_save_markets.py`:

```python
from tools.save_markets import build_market_rows


def test_build_market_rows_race_winner():
    markets = [
        {
            "ticker": "KXF1RACE-MIAGP26-NOR",
            "event_ticker": "KXF1RACE-MIAGP26",
            "yes_sub_title": "Lando Norris",
            "status": "open",
        },
        {
            "ticker": "KXF1RACE-MIAGP26-VER",
            "event_ticker": "KXF1RACE-MIAGP26",
            "yes_sub_title": "Max Verstappen",
            "status": "open",
        },
    ]
    rows = build_market_rows(markets, race_id=1, market_type="race_winner")
    assert len(rows) == 2
    assert rows[0]["kalshi_ticker"] == "KXF1RACE-MIAGP26-NOR"
    assert rows[0]["driver_name"] == "Lando Norris"
    assert rows[0]["market_type"] == "race_winner"
    assert rows[0]["race_id"] == 1


def test_build_market_rows_uses_title_when_no_sub_title():
    markets = [{"ticker": "KXF1POLE-MIAGP26-NOR", "event_ticker": "KXF1POLE-MIAGP26",
                "yes_sub_title": None, "title": "Lando Norris pole", "status": "open"}]
    rows = build_market_rows(markets, race_id=1, market_type="pole")
    assert rows[0]["driver_name"] == "Lando Norris pole"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_save_markets.py -v`
Expected: ImportError

- [ ] **Step 3: Create tools/save_markets.py**

```python
"""
Write discovered Kalshi markets to the database.

Usage:
    python tools/save_markets.py --race-id 1 --event KXF1RACE-MIAGP26 --type race_winner
"""

import argparse
import sys
import time
import requests
from rich.console import Console

from tools.db import cursor

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
HEADERS = {"Accept": "application/json"}
console = Console()

SERIES_TO_TYPE = {
    "KXF1RACE": "race_winner",
    "KXF1RACESPRINT": "sprint_winner",
    "KXF1RACEPODIUM": "podium",
    "KXF1POLE": "pole",
    "KXF1POLEPOSITION": "pole",
    "KXF1CONSTRUCTORS": "constructors",
}


def build_market_rows(markets: list[dict], race_id: int, market_type: str) -> list[dict]:
    rows = []
    for m in markets:
        driver_name = m.get("yes_sub_title") or m.get("title", "")
        rows.append({
            "race_id": race_id,
            "kalshi_ticker": m["ticker"],
            "kalshi_event_ticker": m["event_ticker"],
            "market_type": market_type,
            "driver_name": driver_name,
            "status": m.get("status", "open"),
        })
    return rows


def fetch_markets_for_event(event_ticker: str) -> list[dict]:
    resp = requests.get(
        f"{BASE_URL}/markets",
        headers=HEADERS,
        params={"event_ticker": event_ticker, "status": "open", "limit": 200},
    )
    resp.raise_for_status()
    return resp.json().get("markets", [])


def save_markets(race_id: int, event_ticker: str, market_type: str):
    markets = fetch_markets_for_event(event_ticker)
    rows = build_market_rows(markets, race_id, market_type)

    with cursor() as cur:
        for row in rows:
            cur.execute("""
                INSERT INTO markets
                    (race_id, kalshi_ticker, kalshi_event_ticker, market_type, driver_name, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (kalshi_ticker) DO UPDATE
                    SET status = EXCLUDED.status
            """, (
                row["race_id"], row["kalshi_ticker"], row["kalshi_event_ticker"],
                row["market_type"], row["driver_name"], row["status"],
            ))
    console.print(f"[green]Saved {len(rows)} {market_type} markets for event {event_ticker}[/]")


def main():
    parser = argparse.ArgumentParser(description="Save Kalshi markets to DB")
    parser.add_argument("--race-id", type=int, required=True)
    parser.add_argument("--event", required=True, help="Kalshi event ticker")
    parser.add_argument("--type", required=True, dest="market_type",
                        choices=["race_winner", "sprint_winner", "podium", "pole", "constructors"])
    args = parser.parse_args()
    save_markets(args.race_id, args.event, args.market_type)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/pytest tests/test_save_markets.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add tools/save_markets.py tests/test_save_markets.py
git commit -m "feat: add save_markets tool with DB upsert"
```

---

## Task 8: Run full test suite and push

- [ ] **Step 1: Run all tests**

Run: `.venv/bin/pytest tests/ -v`
Expected: All tests pass. DB tests skip if DATABASE_URL not set.

- [ ] **Step 2: Run linting check**

Run: `.venv/bin/python -m py_compile tools/db.py tools/db_init.py tools/portfolio.py tools/ingest_fastf1.py tools/save_markets.py && echo "syntax OK"`
Expected: `syntax OK`

- [ ] **Step 3: Final commit and push**

```bash
git add -A
git push
```

---

## Validation: When DATABASE_URL is available

Once Supabase credentials are added to `.env`, run in order:

```bash
python tools/db_init.py          # create schema
python tools/db_verify.py        # confirm all 6 tables exist with 0 rows
python tools/ingest_fastf1.py --season 2025 --round 1 --session R  # test with historical race
python tools/db_verify.py        # confirm race_results rows appear
```
