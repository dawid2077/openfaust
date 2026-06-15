"""
Tests for dockersetup.py — database initialization and default file creation.

init_db() is the bootstrap that creates:
- The data directory (if missing)
- The SQLite database with the history table
- The personality.md file (if missing)
- The config.txt file (if missing)
"""

import os
import sys
import sqlite3
from pathlib import Path

import pytest


# ──────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────

class TestInitDb:
    """init_db() should create the database and default files."""

    def test_creates_database_file(self, tmp_path, monkeypatch):
        """A .db file should exist at the configured path after init_db()."""
        monkeypatch.setenv("APP_DATA_PATH", str(tmp_path))
        monkeypatch.setenv("APP_PERSONALITY_PATH", str(tmp_path / "personality.md"))
        monkeypatch.setenv("APP_CONFIG_PATH", str(tmp_path / "config.txt"))

        from dockersetup import init_db
        init_db()

        db_path = tmp_path / "data.db"
        assert db_path.exists(), f"Database file should exist at {db_path}"

    def test_creates_history_table(self, tmp_path, monkeypatch):
        """The history table should have the correct schema."""
        monkeypatch.setenv("APP_DATA_PATH", str(tmp_path))
        monkeypatch.setenv("APP_PERSONALITY_PATH", str(tmp_path / "personality.md"))
        monkeypatch.setenv("APP_CONFIG_PATH", str(tmp_path / "config.txt"))

        from dockersetup import init_db
        init_db()

        conn = sqlite3.connect(str(tmp_path / "data.db"))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='history'")
        assert cursor.fetchone() is not None, "history table should exist"

        # Check columns
        cursor.execute("PRAGMA table_info(history)")
        columns = {row[1] for row in cursor.fetchall()}
        expected = {"id", "is_event", "time_stamp", "user_id", "username", "role", "content", "raw_metadata"}
        assert expected.issubset(columns), f"Expected columns {expected}, got {columns}"
        conn.close()

    def test_creates_directory(self, tmp_path, monkeypatch):
        """If the data directory doesn't exist, init_db should create it."""
        data_dir = tmp_path / "nonexistent" / "deep" / "data"
        monkeypatch.setenv("APP_DATA_PATH", str(data_dir))
        monkeypatch.setenv("APP_PERSONALITY_PATH", str(data_dir / "personality.md"))
        monkeypatch.setenv("APP_CONFIG_PATH", str(data_dir / "config.txt"))

        assert not data_dir.exists(), "Directory should not exist before init_db"

        from dockersetup import init_db
        init_db()

        assert data_dir.exists(), f"Directory should be created at {data_dir}"
        assert (data_dir / "data.db").exists()

    def test_creates_personality_file_if_missing(self, tmp_path, monkeypatch):
        """A personality.md file should be created if it doesn't exist."""
        monkeypatch.setenv("APP_DATA_PATH", str(tmp_path))
        pers_path = tmp_path / "personality.md"
        monkeypatch.setenv("APP_PERSONALITY_PATH", str(pers_path))

        from dockersetup import init_db
        init_db()

        assert pers_path.exists(), "personality.md should be created"
        content = pers_path.read_text()
        assert "Faust" in content, "Default personality should mention Faust"

    def test_creates_config_file_if_missing(self, tmp_path, monkeypatch):
        """A config.txt file with defaults should be created if it doesn't exist."""
        monkeypatch.setenv("APP_DATA_PATH", str(tmp_path))
        monkeypatch.setenv("APP_PERSONALITY_PATH", str(tmp_path / "personality.md"))
        config_path = tmp_path / "config.txt"
        monkeypatch.setenv("APP_CONFIG_PATH", str(config_path))

        from dockersetup import init_db
        init_db()

        assert config_path.exists(), "config.txt should be created"
        content = config_path.read_text()
        assert "DAILY_LIMIT_MAX" in content
        assert "HEARTBEAT_TIME_SECONDS" in content

    def test_does_not_overwrite_existing_files(self, tmp_path, monkeypatch):
        """If personality.md already exists, init_db should NOT overwrite it."""
        monkeypatch.setenv("APP_DATA_PATH", str(tmp_path))
        pers_path = tmp_path / "personality.md"
        pers_path.write_text("CUSTOM CUSTOM CONTENT DO NOT OVERWRITE")
        monkeypatch.setenv("APP_PERSONALITY_PATH", str(pers_path))
        monkeypatch.setenv("APP_CONFIG_PATH", str(tmp_path / "config.txt"))

        from dockersetup import init_db
        init_db()

        content = pers_path.read_text()
        assert content == "CUSTOM CUSTOM CONTENT DO NOT OVERWRITE", \
            "Existing personality file should not be overwritten"

    def test_does_not_overwrite_existing_config(self, tmp_path, monkeypatch):
        """If config.txt already exists, init_db should NOT overwrite it."""
        monkeypatch.setenv("APP_DATA_PATH", str(tmp_path))
        monkeypatch.setenv("APP_PERSONALITY_PATH", str(tmp_path / "personality.md"))
        config_path = tmp_path / "config.txt"
        config_path.write_text("CUSTOM_CONFIG=value")
        monkeypatch.setenv("APP_CONFIG_PATH", str(config_path))

        from dockersetup import init_db
        init_db()

        content = config_path.read_text()
        assert content == "CUSTOM_CONFIG=value"

    def test_idempotent_multiple_calls(self, tmp_path, monkeypatch):
        """Calling init_db() multiple times should not raise errors."""
        monkeypatch.setenv("APP_DATA_PATH", str(tmp_path))
        monkeypatch.setenv("APP_PERSONALITY_PATH", str(tmp_path / "personality.md"))
        monkeypatch.setenv("APP_CONFIG_PATH", str(tmp_path / "config.txt"))

        from dockersetup import init_db
        init_db()  # First call
        init_db()  # Second call — should be idempotent
        init_db()  # Third call — no crash


class TestDockersetupModule:
    """Structural tests for dockersetup."""

    def test_init_db_function_exists(self):
        """The init_db function should be importable."""
        from dockersetup import init_db
        assert callable(init_db)
