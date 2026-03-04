import sqlite3
import pytest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr("script.DB_FILE", db_file)
    monkeypatch.setattr("config.DB_FILE", db_file)
    import script
    script.DB_FILE = db_file
    script.init_db()
    yield db_file


def test_init_db_creates_tables(temp_db):
    import script
    with sqlite3.connect(temp_db) as conn:
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
    assert "users" in tables
    assert "repos" in tables
    assert "releases" in tables


def test_get_user_token_missing(temp_db):
    import script
    assert script.get_user_token(9999) is None


def test_get_user_token_present(temp_db):
    import script
    with sqlite3.connect(temp_db) as conn:
        conn.execute("INSERT INTO users VALUES (1, 'ghtoken123', 'testuser')")
    assert script.get_user_token(1) == "ghtoken123"


def test_get_user_info_missing(temp_db):
    import script
    assert script.get_user_info(42) is None


def test_get_user_info_present(temp_db):
    import script
    with sqlite3.connect(temp_db) as conn:
        conn.execute("INSERT INTO users VALUES (7, 'tok', 'mario')")
    info = script.get_user_info(7)
    assert info["token"] == "tok"
    assert info["username"] == "mario"


def test_delete_user_removes_all(temp_db):
    import script
    with sqlite3.connect(temp_db) as conn:
        conn.execute("INSERT INTO users VALUES (5, 'tok', 'user5')")
        conn.execute("INSERT INTO repos VALUES (5, 'a/b', 'main', 'sha1')")
        conn.execute("INSERT INTO releases VALUES (5, 'a/b', 'v1.0')")
    script.delete_user(5)
    assert script.get_user_token(5) is None
    assert script.load_all_repos() == []
    assert script.load_all_releases() == []


def test_add_and_load_repos(temp_db):
    import script
    script.add_repo_db(1, "user/repo", "main", "abc123")
    repos = script.load_all_repos()
    assert len(repos) == 1
    assert repos[0] == (1, "user/repo", "main", "abc123")


def test_add_repo_replace_existing(temp_db):
    import script
    script.add_repo_db(1, "user/repo", "main", "sha1")
    script.add_repo_db(1, "user/repo", "main", "sha2")
    repos = script.load_all_repos()
    assert len(repos) == 1
    assert repos[0][3] == "sha2"


def test_remove_repo_with_branch(temp_db):
    import script
    script.add_repo_db(1, "user/repo", "main", "sha1")
    script.add_repo_db(1, "user/repo", "dev", "sha2")
    script.remove_repo_db(1, "user/repo", "main")
    repos = script.load_all_repos()
    assert len(repos) == 1
    assert repos[0][2] == "dev"


def test_remove_repo_without_branch(temp_db):
    import script
    script.add_repo_db(1, "user/repo", "main", "sha1")
    script.add_repo_db(1, "user/repo", "dev", "sha2")
    script.remove_repo_db(1, "user/repo")
    assert script.load_all_repos() == []


def test_update_sha_db(temp_db):
    import script
    script.add_repo_db(1, "user/repo", "main", "oldsha")
    script.update_sha_db(1, "user/repo", "main", "newsha")
    assert script.load_all_repos()[0][3] == "newsha"


def test_add_and_load_releases(temp_db):
    import script
    script.add_release_db(1, "user/repo", "v1.0")
    releases = script.load_all_releases()
    assert len(releases) == 1
    assert releases[0] == (1, "user/repo", "v1.0")


def test_update_release_db(temp_db):
    import script
    script.add_release_db(1, "user/repo", "v1.0")
    script.update_release_db(1, "user/repo", "v2.0")
    assert script.load_all_releases()[0][2] == "v2.0"


def test_build_headers_no_token(temp_db):
    import script
    headers = script.build_headers(9999)
    assert "Authorization" not in headers
    assert headers["User-Agent"] == "Telegram-GitHub-Bot"


def test_build_headers_with_token(temp_db):
    import script
    with sqlite3.connect(temp_db) as conn:
        conn.execute("INSERT INTO users VALUES (3, 'mytoken', 'user3')")
    headers = script.build_headers(3)
    assert headers["Authorization"] == "token mytoken"


def test_get_commits_since_api_error(temp_db):
    import script
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    with patch("script.requests.get", return_value=mock_resp):
        sha, commits = script.get_commits_since(1, "user/repo", "main", "sha1")
    assert sha is None
    assert commits is None


def test_get_commits_since_empty(temp_db):
    import script
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = []
    with patch("script.requests.get", return_value=mock_resp):
        sha, commits = script.get_commits_since(1, "user/repo", "main", "sha1")
    assert sha is None
    assert commits is None


def test_get_commits_since_new_commits(temp_db):
    import script
    commits_data = [
        {"sha": "new1", "commit": {"author": {"name": "Alice"}, "message": "feat: add X"}, "html_url": "http://x"},
        {"sha": "old1", "commit": {"author": {"name": "Bob"}, "message": "fix: y"}, "html_url": "http://y"},
    ]
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = commits_data
    with patch("script.requests.get", return_value=mock_resp):
        sha, new_commits = script.get_commits_since(1, "user/repo", "main", "old1")
    assert sha == "new1"
    assert len(new_commits) == 1


def test_get_commits_since_no_new(temp_db):
    import script
    commits_data = [
        {"sha": "sha1", "commit": {"author": {"name": "Alice"}, "message": "fix"}, "html_url": ""},
    ]
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = commits_data
    with patch("script.requests.get", return_value=mock_resp):
        sha, new_commits = script.get_commits_since(1, "user/repo", "main", "sha1")
    assert sha == "sha1"
    assert new_commits == []


def test_get_latest_release_error(temp_db):
    import script
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    with patch("script.requests.get", return_value=mock_resp):
        result = script.get_latest_release(1, "user/repo")
    assert result is None


def test_get_latest_release_ok(temp_db):
    import script
    release_data = {
        "tag_name": "v1.2.3", "name": "Release 1.2.3", "body": "Changelog here",
        "html_url": "http://github.com/release", "author": {"login": "devuser"}, "prerelease": False,
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = release_data
    with patch("script.requests.get", return_value=mock_resp):
        result = script.get_latest_release(1, "user/repo")
    assert result["tag"] == "v1.2.3"
    assert result["author"] == "devuser"
    assert result["prerelease"] is False

# Aggiungi in fondo a tests/test_script.py

def test_get_latest_release_prerelease(temp_db):
    import script
    release_data = {
        "tag_name": "v2.0.0-beta", "name": "Beta", "body": "",
        "html_url": "http://github.com", "author": {"login": "dev"}, "prerelease": True,
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = release_data
    with patch("script.requests.get", return_value=mock_resp):
        result = script.get_latest_release(1, "user/repo")
    assert result["prerelease"] is True


def _make_commit(sha, msg, author, url="http://x"):
    return {"sha": sha, "commit": {"author": {"name": author}, "message": msg}, "html_url": url}


def test_format_commit_digest_single(temp_db):
    import script
    commits = [_make_commit("abc1234", "feat: awesome", "Alice")]
    result = script.format_commit_digest("user/repo", "main", commits)
    assert "1 nuovi commit" in result
    assert "Alice" in result
    assert "abc1234" in result


def test_format_commit_digest_many(temp_db):
    import script
    commits = [_make_commit(f"sha{i}", f"fix: thing {i}", "Bob") for i in range(8)]
    result = script.format_commit_digest("user/repo", "dev", commits)
    assert "8 nuovi commit" in result
    assert "e altri 3 commit" in result


def test_format_commit_digest_multiple_authors(temp_db):
    import script
    commits = [_make_commit("a1", "feat: x", "Alice"), _make_commit("b2", "fix: y", "Bob")]
    result = script.format_commit_digest("user/repo", "main", commits)
    assert "Alice" in result
    assert "Bob" in result


def test_format_commit_digest_truncates_long_message(temp_db):
    import script
    commits = [_make_commit("abc1234", "feat: title\nThis is the body\nmore body", "Dev")]
    result = script.format_commit_digest("user/repo", "main", commits)
    assert "feat: title" in result
    assert "This is the body" not in result