"""
Shared pytest fixtures for the OpenFaust test suite.
"""

import os
import sys
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest

# Ensure project root is on sys.path so imports work
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set test-friendly defaults BEFORE any app module loads
os.environ.setdefault("APP_DATA_PATH", str(PROJECT_ROOT / "tests" / "test_data"))
os.environ.setdefault("APP_PERSONALITY_PATH", str(PROJECT_ROOT / "tests" / "test_data" / "personality.md"))
os.environ.setdefault("APP_CONFIG_PATH", str(PROJECT_ROOT / "tests" / "test_data" / "config.txt"))
os.environ.setdefault("OPENROUTER_API_KEY", "sk-test-key-placeholder")
os.environ.setdefault("DAILY_LIMIT_MAX", "2")
os.environ.setdefault("DAYS_AFTER_LIMIT_RESETS", "1")
os.environ.setdefault("MESSAGES_BY_USER_LIMIT", "40")
os.environ.setdefault("HEARTBEAT_TIME_SECONDS", "1800")


@pytest.fixture
def test_data_dir():
    """Create a clean temporary data directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dst = Path(tmpdir)
        # Ensure config.txt exists
        config_path = dst / "config.txt"
        config_path.write_text(
            "DAILY_LIMIT_MAX=2\n"
            "DAYS_AFTER_LIMIT_RESETS=1\n"
            "MESSAGES_BY_USER_LIMIT=40\n"
            "HEARTBEAT_TIME_SECONDS=1800\n",
            encoding="utf-8",
        )
        # Ensure personality.md exists
        pers_path = dst / "personality.md"
        pers_path.write_text(
            "You are a helpful tsundere assistant named Faust.",
            encoding="utf-8",
        )
        yield dst


@pytest.fixture
def empty_db_path(test_data_dir):
    """Create a fresh empty database and return its path."""
    db_path = test_data_dir / "data.db"
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
    return str(db_path)


@pytest.fixture
def populated_db(empty_db_path):
    """A database pre-loaded with sample messages."""
    conn = sqlite3.connect(empty_db_path)
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    sample_data = [
        (1, now, "user1", "Alice", "user", "Hey everyone!", None),
        (2, now, "user1", "Alice", "user", "What's up?", None),
        (3, now, "bot1", "Faust", "assistant", "Oh look who's talking.", None),
        (1, now, "user2", "Bob", "user", "Faust, you there?", None),
        (2, now, "user2", "Bob", "user", "Hello?", None),
    ]
    cursor.executemany(
        "INSERT INTO history (is_event, time_stamp, user_id, username, role, content, raw_metadata) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        sample_data,
    )
    conn.commit()
    conn.close()
    return empty_db_path


@pytest.fixture
def sample_personality():
    """Return a sample personality string for testing."""
    return (
        "You are a helpful tsundere assistant named Faust who acts sharp, impatient, "
        "and playfully insulting as a defensive mask, but always provides the help the "
        "user needs."
    )
