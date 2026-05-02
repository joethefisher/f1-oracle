import pytest
from unittest.mock import patch, MagicMock


def test_get_connection_raises_without_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    import importlib
    import tools.db as db
    importlib.reload(db)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        db.get_connection()


def test_get_connection_uses_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    import importlib
    import tools.db as db
    importlib.reload(db)
    with patch("psycopg.connect") as mock_connect:
        mock_connect.return_value = MagicMock()
        conn = db.get_connection()
        mock_connect.assert_called_once_with("postgresql://user:pass@host/db")


def test_cursor_commits_on_success(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    import importlib
    import tools.db as db
    importlib.reload(db)

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__ = lambda s: mock_conn
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("psycopg.connect", return_value=mock_conn):
        importlib.reload(db)
        with db.cursor() as cur:
            assert cur is mock_cursor
        mock_conn.commit.assert_called_once()


def test_cursor_rolls_back_on_error(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    import importlib
    import tools.db as db
    importlib.reload(db)

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__ = lambda s: mock_conn
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("psycopg.connect", return_value=mock_conn):
        importlib.reload(db)
        with pytest.raises(ValueError):
            with db.cursor():
                raise ValueError("test error")
        mock_conn.rollback.assert_called_once()


def test_init_creates_all_tables(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    import importlib
    import tools.db as db
    importlib.reload(db)

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("psycopg.connect", return_value=mock_conn):
        importlib.reload(db)
        import tools.db_init as db_init
        importlib.reload(db_init)
        db_init.init_db()

    executed_sql = " ".join(
        str(c.args[0]) for c in mock_cursor.execute.call_args_list
    )
    for table in ["races", "markets", "predictions", "virtual_bets",
                  "outcomes", "portfolio_snapshots", "race_results", "qualifying_results"]:
        assert table in executed_sql, f"Expected CREATE TABLE for {table}"
