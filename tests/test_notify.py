"""Tests for the Telegram transport (tools/notify.py)."""
from unittest.mock import MagicMock, patch

from tools import notify


def _resp(status=200):
    r = MagicMock()
    r.status_code = status
    r.text = ""
    return r


def test_noop_when_unconfigured(monkeypatch):
    monkeypatch.delenv("TELEGRAM_API_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with patch("tools.notify.requests.post") as post:
        assert notify.send("hello") is False
        post.assert_not_called()  # never hits the network when unconfigured


def test_sends_with_correct_payload(monkeypatch):
    monkeypatch.setenv("TELEGRAM_API_TOKEN", "TOK")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    with patch("tools.notify.requests.post", return_value=_resp(200)) as post:
        assert notify.send("hi there") is True
        url = post.call_args.args[0]
        payload = post.call_args.kwargs["json"]
        assert "botTOK/sendMessage" in url
        assert payload["chat_id"] == "123"
        assert payload["text"] == "hi there"


def test_retries_on_429_then_succeeds(monkeypatch):
    monkeypatch.setenv("TELEGRAM_API_TOKEN", "TOK")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    seq = [_resp(429), _resp(200)]
    with patch("tools.notify.requests.post", side_effect=seq), patch("tools.notify.time.sleep"):
        assert notify.send("hi", retries=3) is True


def test_returns_false_on_client_error(monkeypatch):
    monkeypatch.setenv("TELEGRAM_API_TOKEN", "TOK")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    with patch("tools.notify.requests.post", return_value=_resp(400)):
        assert notify.send("hi") is False


def test_is_configured(monkeypatch):
    monkeypatch.setenv("TELEGRAM_API_TOKEN", "TOK")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    assert notify.is_configured() is True
    monkeypatch.delenv("TELEGRAM_CHAT_ID")
    assert notify.is_configured() is False
