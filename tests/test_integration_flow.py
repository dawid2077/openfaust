"""
Integration tests for OpenFaust — container-based.

Tests the real SQLite database, message persistence, context formatting,
and Kairos routing. No mocking — tests that need an API key are
conditionally skipped when OPENROUTER_API_KEY is not set.

Run locally:
    OPENROUTER_API_KEY=sk-...  python -m pytest tests/test_integration_flow.py -v

Run in Docker (test_runner service):
    docker compose --profile test run --rm test_runner
"""

import importlib
import os
import sqlite3
from pathlib import Path

import pytest



# =========================================================================
# Helper: point modules at a temporary data directory
# =========================================================================


def _reload_with_env(data_dir: Path):
    """Set env vars and reload our modules so they pick up the temp DB."""
    os.environ["APP_DATA_PATH"] = str(data_dir)
    os.environ["APP_PERSONALITY_PATH"] = str(data_dir / "personality.md")
    os.environ["APP_CONFIG_PATH"] = str(data_dir / "config.txt")

    for name in ("dockersetup", "save_messages", "context", "tosqlite", "identity_get"):
        if name in __import__("sys").modules:
            importlib.reload(__import__("sys").modules[name])


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def env(tmp_path: Path) -> Path:
    """Isolated tmp dir with initialised DB, personality, and config files."""
    _reload_with_env(tmp_path)
    # init_db() is called by dockersetup, which runs at import time.
    # After reloading, we need to call it explicitly:
    import dockersetup as ds

    ds.init_db()
    return tmp_path


@pytest.fixture
def seeded(env: Path) -> Path:
    """env + 7 pre-populated history rows."""
    from save_messages import save_normal_message

    messages = [
        ("Cześć wszystkim!", "dawid", 1001),
        ("Hej Faust, pomożesz mi?", "dawid", 1001),
        ("Oh, it's you again. What do you want?", "Faust", 999),
        ("Potrzebuję pomocy z kodem", "dawid", 1001),
        ("No dobra, mów o co chodzi.", "Faust", 999),
    ]
    for content, user, uid in messages:
        save_normal_message(content, user, uid)

    # Add an LLM response pair (is_event=2 user + is_event=3 assistant)
    db_path = str(env / "data.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO history (is_event, time_stamp, user_id, username, role, content) "
        'VALUES (2, "2026-06-01 10:00:00+02:00", "1001", "dawid", "user", '
        '"Co myślisz o pythonie?")'
    )
    conn.execute(
        "INSERT INTO history (is_event, time_stamp, user_id, username, role, content) "
        'VALUES (3, "2026-06-01 10:00:05+02:00", "999", "Faust", "assistant", '
        '"Python? Hmph. It\'s acceptable, I suppose.")'
    )
    conn.commit()
    conn.close()
    return env


# =========================================================================
# Tests — Layer 1: Database + Context (no API key needed)
# =========================================================================


class TestDatabase:
    """Verify that messages flow correctly through the real SQLite database."""

    def test_table_created(self, env: Path):
        """init_db() should create the 'history' table."""
        db = str(env / "data.db")
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='history'"
        ).fetchone()
        conn.close()
        assert row is not None

    def test_save_and_count(self, seeded: Path):
        """5 save_normal_message() calls = 5 rows with is_event=1."""
        db = str(seeded / "data.db")
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM history WHERE is_event=1").fetchone()[0]
        conn.close()
        assert count == 5

    def test_save_llm_pair(self, seeded: Path):
        """An LLM response pair inserts one user row (+ 1 assistant row)."""
        db = str(seeded / "data.db")
        conn = sqlite3.connect(db)
        user = conn.execute("SELECT COUNT(*) FROM history WHERE is_event=2").fetchone()[0]
        asst = conn.execute("SELECT COUNT(*) FROM history WHERE is_event=3").fetchone()[0]
        conn.close()
        assert user == 1
        assert asst == 1

    def test_context_call_returns_messages(self, seeded: Path):
        """context_call() should return formatted message dicts."""
        import context

        importlib.reload(context)
        result = context.context_call()
        assert len(result) >= 5
        for msg in result:
            assert "role" in msg
            assert "content" in msg
            if msg["role"] == "user":
                assert ": " in msg["content"]  # username: prefix

    def test_context_kairos_includes_timestamps(self, seeded: Path):
        """context_kairos() should append 'minutes ago' metadata."""
        import context

        importlib.reload(context)
        result = context.context_kairos()
        assert len(result) >= 5
        for msg in result:
            assert "minutes ago" in msg["content"]

    def test_context_empty(self, env: Path):
        """context_call/kairos return [] for an empty database."""
        import context

        importlib.reload(context)
        assert context.context_call() == []
        assert context.context_kairos() == []

    def test_multiple_users(self, seeded: Path):
        """Usernames should be distinguishable in context output."""
        import context

        importlib.reload(context)
        msgs = [m for m in context.context_call() if m["role"] == "user"]
        names = set(m["content"].split(":")[0].strip() for m in msgs)
        assert "dawid" in names


# =========================================================================
# Tests — Layer 2: Identity extraction (no API key needed)
# =========================================================================


class TestIdentity:
    """Fallback behaviour of get_companion_identity()."""

    def test_missing_file(self, env: Path):
        """No file -> returns 'Faust'."""
        from identity_get import get_companion_identity

        assert get_companion_identity(env / "nonexistent.md") == "Faust"

    def test_empty_file(self, env: Path):
        """Empty file -> returns 'Faust'."""
        from identity_get import get_companion_identity

        (env / "empty.md").write_text("", encoding="utf-8")
        assert get_companion_identity(env / "empty.md") == "Faust"

    def test_whitespace_file(self, env: Path):
        """Whitespace-only file -> returns 'Faust'."""
        from identity_get import get_companion_identity

        (env / "ws.md").write_text("   \n\n  ", encoding="utf-8")
        assert get_companion_identity(env / "ws.md") == "Faust"


# =========================================================================
# Tests — Layer 3: Kairos routing (requires real OPENROUTER_API_KEY)
# =========================================================================


def _has_real_api_key() -> bool:
    """True if OPENROUTER_API_KEY looks like a real key (not a test placeholder)."""
    key = os.getenv("OPENROUTER_API_KEY", "")
    if not key:
        return False
    # Skip the placeholder that conftest.py's setdefault injects
    if "test-skip" in key or key.startswith("fake"):
        return False
    return True


need_api = pytest.mark.skipif(
    not _has_real_api_key(),
    reason="Real OPENROUTER_API_KEY not set — skipping API-dependent tests",
)

# Full pipeline needs real API key AND clean env (not polluted by unit test mocks)
need_pipeline = pytest.mark.skipif(
    not _has_real_api_key(),
    reason="Real OPENROUTER_API_KEY required for full pipeline test — run in isolation",
)


@need_api
class TestKairos:
    """Real API calls to the Kairos routing engine."""

    def _profile(self, seeded: Path) -> str:
        return (seeded / "personality.md").read_text(encoding="utf-8")

    def test_decide_returns_action(self, seeded: Path):
        """decide() should return '1', '2', or '3'."""
        from kairos import decide

        result = decide("Faust, are you there?", [], self._profile(seeded))
        assert result in ("1", "2", "3")

    def test_decide_with_context(self, seeded: Path):
        """decide() with real context should not crash."""
        import context

        importlib.reload(context)
        from kairos import decide

        ctx = context.context_kairos()
        result = decide("What do you think?", ctx, self._profile(seeded))
        assert result in ("1", "2", "3")


# =========================================================================
# Tests — Layer 4: Full pipeline (requires OPENROUTER_API_KEY)
# =========================================================================


@need_pipeline
class TestPipeline:
    """End-to-end: save message -> call LLM -> verify response persisted."""

    def test_call_mistral_saves_response(self, env: Path):
        """call_mistral() returns text and the response is stored in the DB."""
        # Reload api module to get a clean client (not polluted by other tests' mocks)
        import api
        importlib.reload(api)
        from api import call_mistral

        response = call_mistral(
            messagecontent="Say hello in one sentence.",
            nickname="tester",
            user_id=42,
            bot_id=999,
            bot_name="Faust",
        )
        assert isinstance(response, str)
        assert len(response) > 0

        db = str(env / "data.db")
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT role, content FROM history WHERE is_event=3 ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "assistant"
        assert len(row[1]) > 0
