import sqlite3
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test_oauth.db")
    monkeypatch.setattr("oauth_server.DB_FILE", db_file)
    import oauth_server
    oauth_server.DB_FILE = db_file
    oauth_server.ensure_tables()
    yield db_file


def test_ensure_tables_creates_users_and_states(temp_db):
    import oauth_server
    oauth_server.ensure_tables()
    with sqlite3.connect(temp_db) as conn:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
    assert "users" in tables
    assert "oauth_states" in tables


def test_save_and_pop_state(temp_db):
    import oauth_server
    oauth_server.save_state("mystate123", 42)
    assert oauth_server.pop_state("mystate123") == 42


def test_pop_state_removes_record(temp_db):
    import oauth_server
    oauth_server.save_state("oneuse", 7)
    oauth_server.pop_state("oneuse")
    assert oauth_server.pop_state("oneuse") is None


def test_pop_state_nonexistent(temp_db):
    import oauth_server
    assert oauth_server.pop_state("doesnotexist") is None


def test_save_github_token(temp_db):
    import oauth_server
    oauth_server.save_github_token(10, "ghp_token", "testuser")
    with sqlite3.connect(temp_db) as conn:
        row = conn.execute(
            "SELECT github_token, github_username FROM users WHERE chat_id=10"
        ).fetchone()
    assert row[0] == "ghp_token"
    assert row[1] == "testuser"


def test_save_github_token_replace(temp_db):
    import oauth_server
    oauth_server.save_github_token(10, "old_token", "userA")
    oauth_server.save_github_token(10, "new_token", "userA")
    with sqlite3.connect(temp_db) as conn:
        rows = conn.execute("SELECT COUNT(*) FROM users WHERE chat_id=10").fetchone()
    assert rows[0] == 1


def test_get_github_username_success(temp_db):
    from unittest.mock import patch, MagicMock
    import oauth_server
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"login": "johndoe"}
    with patch("oauth_server.requests.get", return_value=mock_resp):
        assert oauth_server.get_github_username("sometoken") == "johndoe"


def test_get_github_username_failure(temp_db):
    from unittest.mock import patch, MagicMock
    import oauth_server
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    with patch("oauth_server.requests.get", return_value=mock_resp):
        assert oauth_server.get_github_username("badtoken") is None