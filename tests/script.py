"""
test_script.py — Unit test per script.py (GitNotifyBot)
"""

import sqlite3
import pytest
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
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
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
