"""
Race week gate for GitHub Actions.

Outputs `active=true` if a race is within the 8-day window, `active=false` otherwise.
Designed to run as a lightweight pre-check job (psycopg only, no fastf1).

Usage (GitHub Actions):
    python tools/race_gate.py >> $GITHUB_OUTPUT
"""

import os
import sys

import psycopg


def main():
    url = os.environ["DATABASE_URL"]
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM races
                WHERE race_date_utc BETWEEN NOW() - INTERVAL '3 days'
                                       AND NOW() + INTERVAL '8 days'
                  AND status IN ('upcoming', 'active')
            """)
            count = cur.fetchone()[0]
    active = count > 0
    print(f"active={'true' if active else 'false'}")
    sys.exit(0)


if __name__ == "__main__":
    main()
