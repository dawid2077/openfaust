"""
Tests for tosqlite.py — saving API response metadata to the database.

The save() function stores both the user query and the AI response as
a pair of rows in the history table, along with raw metadata.
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

# Module under test — to avoid side effects on import, we reload after env setup
import tosqlite
import importlib


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture(autouse=True)
def setup_env_and_db(tmp_path, monkeypatch):
    """Set environment and create the database before each test."""
    monkeypatch.setenv("APP_DATA_PATH", str(tmp_path))
    # Reload tosqlite so it picks up the new env
    importlib.reload(tosqlite)

    # Create the table
    conn = sqlite3.connect(tmp_path / "data.db")
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
    return tmp_path


@pytest.fixture
def sample_openai_response():
    """Simulate a real OpenAI-style response JSON string."""
    response_data = {
        "id": "chatcmpl-abc123",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "mistralai/mistral-small-2603",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Oh, you want my help? How unexpected. Fine, the answer is 42."
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 20,
            "total_tokens": 70
        }
    }
    return json.dumps(response_data)


# ──────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────

class TestSave:
    """save() should store user+assistant message pairs."""

    def test_saves_two_rows(self, setup_env_and_db, sample_openai_response):
        """Each save() call should insert exactly 2 rows (user + assistant)."""
        tosqlite.save(
            nickname="Alice",
            data=sample_openai_response,
            user_id=1001,
            messagecontent="What is the meaning of life?",
            bot_id=9001,
            bot_name="Faust",
        )

        conn = sqlite3.connect(setup_env_and_db / "data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM history")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 2, f"Expected 2 rows, got {count}"

    def test_user_row_correct(self, setup_env_and_db, sample_openai_response):
        """The first row should be the user message (is_event=2)."""
        tosqlite.save(
            nickname="Alice",
            data=sample_openai_response,
            user_id=1001,
            messagecontent="Hello?",
            bot_id=9001,
            bot_name="Faust",
        )

        conn = sqlite3.connect(setup_env_and_db / "data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM history WHERE is_event=2")
        rows = cursor.fetchall()
        conn.close()

        assert len(rows) == 1
        row = rows[0]
        assert row[3] == "1001"  # user_id
        assert row[4] == "Alice"  # username
        assert row[5] == "user"   # role
        assert row[6] == "Hello?"  # content
        assert row[7] is not None  # raw_metadata

    def test_assistant_row_correct(self, setup_env_and_db, sample_openai_response):
        """The second row should be the assistant message (is_event=3)."""
        tosqlite.save(
            nickname="Alice",
            data=sample_openai_response,
            user_id=1001,
            messagecontent="Hello!",
            bot_id=9001,
            bot_name="Faust",
        )

        conn = sqlite3.connect(setup_env_and_db / "data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM history WHERE is_event=3")
        rows = cursor.fetchall()
        conn.close()

        assert len(rows) == 1
        row = rows[0]
        assert row[3] == "9001"  # bot_id
        assert row[4] == "Faust"  # bot_name
        assert row[5] == "assistant"  # role
        assert row[6] == "Oh, you want my help? How unexpected. Fine, the answer is 42."

    def test_saves_raw_metadata(self, setup_env_and_db, sample_openai_response):
        """The full API response JSON should be stored in raw_metadata."""
        tosqlite.save(
            nickname="Alice",
            data=sample_openai_response,
            user_id=1001,
            messagecontent="Test",
            bot_id=9001,
            bot_name="Faust",
        )

        conn = sqlite3.connect(setup_env_and_db / "data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT raw_metadata FROM history WHERE is_event=2")
        raw = cursor.fetchone()[0]
        conn.close()

        parsed = json.loads(raw)
        assert parsed["choices"][0]["message"]["content"] == \
            "Oh, you want my help? How unexpected. Fine, the answer is 42."

    def test_multiple_calls_increment_rows(self, setup_env_and_db, sample_openai_response):
        """Multiple save() calls should create 2N rows."""
        for i in range(3):
            tosqlite.save(
                nickname="User",
                data=sample_openai_response,
                user_id=1000 + i,
                messagecontent=f"Message {i}",
                bot_id=9001,
                bot_name="Faust",
            )

        conn = sqlite3.connect(setup_env_and_db / "data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM history")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 6, f"Expected 6 rows (3 calls x 2), got {count}"

    def test_malformed_json_data(self, setup_env_and_db):
        """Save should not crash if data is not valid JSON."""
        try:
            tosqlite.save(
                nickname="Alice",
                data="not valid json at all",
                user_id=1,
                messagecontent="Test",
                bot_id=9001,
                bot_name="Faust",
            )
        except Exception as e:
            pytest.fail(f"save() raised unexpected exception: {e}")

        # Should still have 2 rows
        conn = sqlite3.connect(setup_env_and_db / "data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM history")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 2

    def test_empty_choices(self, setup_env_and_db):
        """Save should handle responses with empty choices gracefully."""
        data = json.dumps({"id": "test", "choices": []})

        try:
            tosqlite.save(
                nickname="Alice",
                data=data,
                user_id=1,
                messagecontent="Test",
                bot_id=9001,
                bot_name="Faust",
            )
        except Exception as e:
            pytest.fail(f"save() raised: {e}")

        conn = sqlite3.connect(setup_env_and_db / "data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM history")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 2

    def test_timestamp_format(self, setup_env_and_db, sample_openai_response):
        """Timestamps should be valid ISO format."""
        tosqlite.save(
            nickname="Alice",
            data=sample_openai_response,
            user_id=1,
            messagecontent="Hi",
            bot_id=9001,
            bot_name="Faust",
        )

        conn = sqlite3.connect(setup_env_and_db / "data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT time_stamp FROM history LIMIT 1")
        ts = cursor.fetchone()[0]
        conn.close()

        parsed = datetime.fromisoformat(ts)
        assert isinstance(parsed, datetime)


class TestTosqliteModule:
    """Structural tests for tosqlite."""
    
    def test_save_function_exists(self):
        """The save function should be importable."""
        import tosqlite
        assert callable(tosqlite.save)
