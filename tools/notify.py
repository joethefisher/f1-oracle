"""
Telegram notification transport.

Single responsibility: deliver a message to the configured Telegram chat. All
notification *content* is built elsewhere (tools/summaries.py) — this module only
sends. If TELEGRAM_API_TOKEN / TELEGRAM_CHAT_ID are unset it logs and no-ops, so
local runs and CI without secrets never fail.

Plain text (no parse_mode) on purpose: messages include dynamic content and
tracebacks, and Markdown/HTML escaping is a footgun. Emoji + line breaks read
fine in Telegram.

Usage:
    python -m tools.notify "hello from the F1 Oracle"
"""
import logging
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("notify")

API_TOKEN_ENV = "TELEGRAM_API_TOKEN"
CHAT_ID_ENV = "TELEGRAM_CHAT_ID"
TIMEOUT = 10


def is_configured() -> bool:
    return bool(os.getenv(API_TOKEN_ENV) and os.getenv(CHAT_ID_ENV))


def send(text: str, *, retries: int = 3) -> bool:
    """Send a Telegram message. Returns True on success, False if unconfigured/failed."""
    token = os.getenv(API_TOKEN_ENV)
    chat_id = os.getenv(CHAT_ID_ENV)
    if not (token and chat_id):
        first_line = text.splitlines()[0] if text else ""
        log.info("Telegram not configured (%s/%s unset) — skipping: %s",
                 API_TOKEN_ENV, CHAT_ID_ENV, first_line)
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    delay = 2
    for attempt in range(retries):
        try:
            resp = requests.post(url, json=payload, timeout=TIMEOUT)
        except requests.RequestException as e:
            log.warning("Telegram send failed (attempt %d): %s", attempt + 1, e)
            time.sleep(delay)
            delay *= 2
            continue
        if resp.status_code == 429 or resp.status_code >= 500:
            log.warning("Telegram %d (attempt %d) — retrying in %ds",
                        resp.status_code, attempt + 1, delay)
            time.sleep(delay)
            delay *= 2
            continue
        if resp.status_code != 200:
            log.error("Telegram send error %d: %s", resp.status_code, resp.text[:200])
            return False
        return True
    log.error("Telegram send failed after %d retries", retries)
    return False


def main():
    text = " ".join(sys.argv[1:]) or "F1 Oracle test notification"
    print("sent" if send(text) else "not sent (unconfigured or error)")


if __name__ == "__main__":
    main()
