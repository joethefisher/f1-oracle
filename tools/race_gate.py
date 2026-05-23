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
            # Gate purely by date — NOT status. A corrupted status must never be
            # able to hide a race weekend from the pipeline (the orchestrator
            # reconciles status from facts once it runs). The date window covers
            # pre-weekend market discovery (~7d out) through post-race settlement.
            cur.execute("""
                SELECT COUNT(*) FROM races
                WHERE race_date_utc BETWEEN NOW() - INTERVAL '3 days'
                                       AND NOW() + INTERVAL '8 days'
            """)
            count = cur.fetchone()[0]
    active = count > 0
    print(f"active={'true' if active else 'false'}")
    sys.exit(0)


if __name__ == "__main__":
    main()
