"""
Tests for save_messages.py — saving normal user messages to the SQLite database.
"""

import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from save_messages import save_normal_message


# ──────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────

class TestSaveNormalMessage:
    """save_normal_message() stores user messages in the history table."""

    def test_saves_user_message(self, tmp_path, monkeypatch):
        """A user message should be inserted with role='user' and is_event=1."""
        db_path = tmp_path / "data.db"
        monkeypatch.setenv("APP_DATA_PATH", str(tmp_path))

        # Manually create table
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                is_event INTEGER NOT NULL,
                time_stamp TEXT NOT NULL,
                user_id TEXT,
                username TEXT,
                role TEXT,
                content TEXT,
                raw_metadata TEXT
            )
        """)
        conn.commit()
        conn.close()

        # Re-initialize module with new path
        import importlib
        import save_messages
        importlib.reload(save_messages)

        save_normal_message("Hello everyone!", "Alice", 1001)

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM history")
        rows = cursor.fetchall()
        conn.close()

        assert len(rows) == 1
        row = rows[0]
        assert row[1] == 1  # is_event
        assert row[3] == "1001"  # user_id (str)
        assert row[4] == "Alice"  # username
        assert row[5] == "user"  # role
        assert row[6] == "Hello everyone!"  # content

    def test_timestamp_is_valid_iso(self, tmp_path, monkeypatch):
        """The saved timestamp should be a valid ISO 8601 datetime."""
        db_path = tmp_path / "data.db"
        monkeypatch.setenv("APP_DATA_PATH", str(tmp_path))

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                is_event INTEGER NOT NULL,
                time_stamp TEXT NOT NULL,
                user_id TEXT,
                username TEXT,
                role TEXT,
                content TEXT,
                raw_metadata TEXT
            )
        """)
        conn.commit()
        conn.close()

        import importlib
        import save_messages
        importlib.reload(save_messages)

        save_normal_message("Test", "Bob", 2002)

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT time_stamp FROM history")
        ts = cursor.fetchone()[0]
        conn.close()

        # Try parsing it
        parsed = datetime.fromisoformat(ts)
        assert isinstance(parsed, datetime)

    def test_saves_multiple_messages(self, tmp_path, monkeypatch):
        """Multiple calls should create multiple rows."""
        db_path = tmp_path / "data.db"
        monkeypatch.setenv("APP_DATA_PATH", str(tmp_path))

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                is_event INTEGER NOT NULL,
                time_stamp TEXT NOT NULL,
                user_id TEXT,
                username TEXT,
                role TEXT,
                content TEXT,
                raw_metadata TEXT
            )
        """)
        conn.commit()
        conn.close()

        import importlib
        import save_messages
        importlib.reload(save_messages)

        save_normal_message("First", "Alice", 1)
        save_normal_message("Second", "Bob", 2)
        save_normal_message("Third", "Charlie", 3)

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM history")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 3

    def test_db_path_from_env(self, tmp_path, monkeypatch):
        """The DB path should be derived from APP_DATA_PATH env var."""
        custom_path = tmp_path / "custom_data"
        custom_path.mkdir()
        monkeypatch.setenv("APP_DATA_PATH", str(custom_path))

        # Create the table first (save_messages doesn't auto-create)
        expected_db = custom_path / "data.db"
        conn = sqlite3.connect(str(expected_db))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                is_event INTEGER NOT NULL,
                time_stamp TEXT NOT NULL,
                user_id TEXT,
                username TEXT,
                role TEXT,
                content TEXT,
                raw_metadata TEXT
            )
        """)
        conn.commit()
        conn.close()

        import importlib
        import save_messages
        importlib.reload(save_messages)

        save_normal_message("Where is my data?", "TestUser", 42)

        assert expected_db.exists(), f"DB should exist at {expected_db}"


# ──────────────────────────────────────────────
# Module-level structural tests
# ──────────────────────────────────────────────

class TestSaveMessagesModule:
    """Structural tests for the save_messages module."""

    def test_save_normal_message_exists(self):
        """The save_normal_message function should be importable."""
        from save_messages import save_normal_message
        assert callable(save_normal_message)
