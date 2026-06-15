"""
Tests for the database layer: dockersetup, tosqlite, save_messages, and context.
All tests use an isolated temporary SQLite file.

Note: tosqlite.py and save_messages.py have module-level DB connections,
so tests that exercise those modules use importlib.reload() after setting
the APP_DATA_PATH environment variable.
"""

import importlib
import os
import sqlite3
from pathlib import Path

import pytest


# =========================================================================
# dockersetup – init_db
# =========================================================================


class TestInitDb:
    def test_init_db_creates_table(self, init_test_db: Path):
        """init_db() should create the 'history' table."""
        db = str(init_test_db / "data.db")
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='history'")
        assert cursor.fetchone() is not None, "history table was not created"
        conn.close()

    def test_init_db_creates_personality_file(self, init_test_db: Path):
        """init_db() should create personality.md if it doesn't exist."""
        p = init_test_db / "personality.md"
        assert p.exists(), "personality.md was not created"
        content = p.read_text(encoding="utf-8")
        assert "Faust" in content or "tsundere" in content

    def test_init_db_creates_config_file(self, init_test_db: Path):
        """init_db() should create config.txt if it doesn't exist."""
        p = init_test_db / "config.txt"
        assert p.exists(), "config.txt was not created"
        content = p.read_text(encoding="utf-8")
        assert "DAILY_LIMIT_MAX" in content

    def test_init_db_is_idempotent(self, init_test_db: Path):
        """Calling init_db() twice should not raise."""
        from dockersetup import init_db

        init_db()  # second call
        db = str(init_test_db / "data.db")
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='history'")
        assert cursor.fetchone()[0] == 1
        conn.close()


# =========================================================================
# save_messages – save_normal_message
# =========================================================================


class TestSaveNormalMessage:
    def _reload_save_messages(self, tmp_data_dir: Path):
        """Set env and reload save_messages module so it picks up the temp path."""
        os.environ["APP_DATA_PATH"] = str(tmp_data_dir)
        import save_messages as sm
        importlib.reload(sm)
        return sm

    def test_save_normal_message_inserts_row(self, init_test_db: Path, tmp_data_dir: Path):
        """save_normal_message() should insert a user message into history."""
        sm = self._reload_save_messages(tmp_data_dir)
        sm.save_normal_message("Hello world", "dawid", 42)

        db = str(tmp_data_dir / "data.db")
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute("SELECT is_event, username, role, content FROM history WHERE is_event=1")
        rows = cursor.fetchall()
        conn.close()

        assert len(rows) == 1
        assert rows[0] == (1, "dawid", "user", "Hello world")

    def test_save_normal_message_multiple(self, init_test_db: Path, tmp_data_dir: Path):
        """Multiple calls should insert multiple rows."""
        sm = self._reload_save_messages(tmp_data_dir)
        sm.save_normal_message("msg1", "alice", 10)
        sm.save_normal_message("msg2", "bob", 20)

        db = str(tmp_data_dir / "data.db")
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM history WHERE is_event=1")
        assert cursor.fetchone()[0] == 2
        conn.close()

    def test_save_normal_message_empty_content(self, init_test_db: Path, tmp_data_dir: Path):
        """Empty message content should still be saved."""
        sm = self._reload_save_messages(tmp_data_dir)
        sm.save_normal_message("", "dawid", 42)

        db = str(tmp_data_dir / "data.db")
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM history WHERE is_event=1")
        assert cursor.fetchone()[0] == ""
        conn.close()


# =========================================================================
# tosqlite – save
# =========================================================================


class TestToSqliteSave:
    def _reload_tosqlite(self, tmp_data_dir: Path):
        """Set env and reload tosqlite module so it picks up the temp path."""
        os.environ["APP_DATA_PATH"] = str(tmp_data_dir)
        import tosqlite as ts
        importlib.reload(ts)
        return ts

    def test_save_inserts_user_and_assistant(self, init_test_db: Path, tmp_data_dir: Path):
        """save() should insert one user row and one assistant row."""
        ts = self._reload_tosqlite(tmp_data_dir)

        fake_metadata = (
            '{"id":"gen-test","choices":[{"finish_reason":"stop","index":0,'
            '"message":{"content":"Sure thing!","role":"assistant","refusal":null}}],'
            '"created":1700000000,"model":"mistralai/mistral-small-2603","object":"chat.completion",'
            '"usage":{"completion_tokens":5,"prompt_tokens":10,"total_tokens":15}}'
        )
        ts.save("dawid", fake_metadata, 100, "Hello!", 999, "Faust")

        db = str(tmp_data_dir / "data.db")
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute("SELECT is_event, username, role, content FROM history ORDER BY id")
        rows = cursor.fetchall()
        conn.close()

        assert len(rows) == 2
        assert rows[0] == (2, "dawid", "user", "Hello!")
        assert rows[1] == (3, "Faust", "assistant", "Sure thing!")

    def test_save_with_invalid_json(self, init_test_db: Path, tmp_data_dir: Path):
        """If raw_metadata is not valid JSON, save should still work."""
        ts = self._reload_tosqlite(tmp_data_dir)
        ts.save("dawid", "not-json-at-all", 100, "hi", 999, "Faust")

        db = str(tmp_data_dir / "data.db")
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM history")
        assert cursor.fetchone()[0] == 2  # still inserts both rows
        conn.close()


# =========================================================================
# context – context_call & context_kairos
# =========================================================================


class TestContextCall:
    def test_context_call_returns_messages(self, populated_db: Path):
        """context_call() should return the history as a list of dicts."""
        # Reload context module with the correct DB path
        import context as ctx
        importlib.reload(ctx)

        result = ctx.context_call()
        assert isinstance(result, list)
        assert len(result) == 3

    def test_context_call_structure(self, populated_db: Path):
        """Each item should have 'role' and 'content' keys."""
        import context as ctx
        importlib.reload(ctx)

        result = ctx.context_call()
        for msg in result:
            assert "role" in msg
            assert "content" in msg

    def test_context_call_user_prefix(self, populated_db: Path):
        """User messages should have username: prefix in content."""
        import context as ctx
        importlib.reload(ctx)

        result = ctx.context_call()
        user_msgs = [m for m in result if m["role"] == "user"]
        assert any("dawid:" in m["content"] for m in user_msgs)

    def test_context_call_empty_db(self, init_test_db: Path):
        """context_call() should return [] for an empty database."""
        import context as ctx
        importlib.reload(ctx)

        result = ctx.context_call()
        assert result == []


class TestContextKairos:
    def test_context_kairos_returns_messages(self, populated_db: Path):
        """context_kairos() should return the history."""
        import context as ctx
        importlib.reload(ctx)

        result = ctx.context_kairos()
        assert isinstance(result, list)
        assert len(result) == 3

    def test_context_kairos_includes_time(self, populated_db: Path):
        """Kairos context should include 'minutes ago' metadata."""
        import context as ctx
        importlib.reload(ctx)

        result = ctx.context_kairos()
        for msg in result:
            assert "minutes ago" in msg["content"]

    def test_context_kairos_empty_db(self, init_test_db: Path):
        """context_kairos() should return [] for an empty database."""
        import context as ctx
        importlib.reload(ctx)

        assert ctx.context_kairos() == []
