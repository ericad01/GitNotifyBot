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
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
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


@pytest.fixture()
def client(temp_db, monkeypatch):
    import oauth_server

    oauth_server.app.config["TESTING"] = True
    with oauth_server.app.test_client() as c:
        yield c


def test_generate_oauth_url_format(temp_db, monkeypatch):
    import oauth_server

    monkeypatch.setattr(oauth_server, "GITHUB_CLIENT_ID", "test_client_id")
    monkeypatch.setattr(oauth_server, "OAUTH_REDIRECT_URI", "http://localhost/callback")
    url = oauth_server.generate_oauth_url(99)
    assert "github.com/login/oauth/authorize" in url
    assert "test_client_id" in url
    assert "state=" in url


def test_generate_oauth_url_saves_state(temp_db, monkeypatch):
    import oauth_server

    monkeypatch.setattr(oauth_server, "GITHUB_CLIENT_ID", "cid")
    monkeypatch.setattr(oauth_server, "OAUTH_REDIRECT_URI", "http://localhost/cb")
    url = oauth_server.generate_oauth_url(55)
    state = [p.split("=")[1] for p in url.split("&") if p.startswith("state=")][0]
    assert oauth_server.pop_state(state) == 55


def test_callback_missing_params(client):
    assert client.get("/callback").status_code == 400


def test_callback_invalid_state(client):
    assert client.get("/callback?code=abc&state=invalidstate").status_code == 400


def test_callback_valid_flow(client, temp_db):
    from unittest.mock import patch, MagicMock
    import oauth_server

    oauth_server.save_state("validstate", 123)
    token_resp = MagicMock()
    token_resp.status_code = 200
    token_resp.json.return_value = {"access_token": "ghp_valid"}
    user_resp = MagicMock()
    user_resp.status_code = 200
    user_resp.json.return_value = {"login": "awesomeuser"}
    with patch("oauth_server.requests.post", return_value=token_resp), patch(
        "oauth_server.requests.get", return_value=user_resp
    ):
        resp = client.get("/callback?code=validcode&state=validstate")
    assert resp.status_code == 200
    assert b"awesomeuser" in resp.data


def test_callback_github_post_error(client, temp_db):
    from unittest.mock import patch, MagicMock
    import oauth_server

    oauth_server.save_state("s2", 456)
    mock_post = MagicMock()
    mock_post.status_code = 500
    with patch("oauth_server.requests.post", return_value=mock_post):
        assert client.get("/callback?code=x&state=s2").status_code == 500


def test_callback_no_access_token(client, temp_db):
    from unittest.mock import patch, MagicMock
    import oauth_server

    oauth_server.save_state("s3", 789)
    mock_post = MagicMock()
    mock_post.status_code = 200
    mock_post.json.return_value = {
        "error": "bad_verification_code",
        "error_description": "wrong",
    }
    with patch("oauth_server.requests.post", return_value=mock_post):
        assert client.get("/callback?code=bad&state=s3").status_code == 500
