"""
Shared test fixtures and configuration for OpenFaust tests.

All tests that touch the database use an isolated temporary SQLite file
so they never interfere with production data or with each other.
"""

import os
import shutil
import tempfile
import warnings
from pathlib import Path
from typing import Generator

import pytest

# ---------------------------------------------------------------------------
# Global test environment – set before any module imports happen
# ---------------------------------------------------------------------------
os.environ.setdefault("OPENROUTER_API_KEY", "test-skip-key-12345")
os.environ.setdefault("DISCORD_TOKEN", "test-skip-token")
os.environ.setdefault("APP_DATA_PATH", "/tmp/openfaust-test-data")
os.environ.setdefault("APP_PERSONALITY_PATH", "/tmp/openfaust-test-data/personality.md")
os.environ.setdefault("APP_CONFIG_PATH", "/tmp/openfaust-test-data/config.txt")
os.environ.setdefault("HEARTBEAT_TIME_SECONDS", "86400")  # far future
os.environ.setdefault("DAILY_LIMIT_MAX", "10")
os.environ.setdefault("DAYS_AFTER_LIMIT_RESETS", "1")
os.environ.setdefault("MESSAGES_BY_USER_LIMIT", "40")


@pytest.fixture(autouse=True)
def _suppress_resource_warnings():
    """Suppress unclosed-socket / SSL warnings from httpx during tests."""
    warnings.filterwarnings("ignore", category=ResourceWarning)


# ---------------------------------------------------------------------------
# Fixture: isolated temporary directory for each test function
# ---------------------------------------------------------------------------
@pytest.fixture
def tmp_data_dir() -> Generator[Path, None, None]:
    """Create & yield a temporary data directory, then clean it up."""
    tmp = Path(tempfile.mkdtemp(prefix="openfaust-test-"))
    # Pre-populate a minimal personality file so imports don't crash
    (tmp / "personality.md").write_text(
        "You are a helpful tsundere assistant named Faust.",
        encoding="utf-8",
    )
    (tmp / "config.txt").write_text(
        "DAILY_LIMIT_MAX=10\nDAYS_AFTER_LIMIT_RESETS=1\nMESSAGES_BY_USER_LIMIT=40\nHEARTBEAT_TIME_SECONDS=86400\n",
        encoding="utf-8",
    )
    yield tmp
    shutil.rmtree(str(tmp), ignore_errors=True)


@pytest.fixture
def db_path(tmp_data_dir: Path) -> str:
    """Return the path to a temp SQLite database file."""
    return str(tmp_data_dir / "data.db")


# ---------------------------------------------------------------------------
# Fixture: fully initialised test database + environment
# ---------------------------------------------------------------------------
@pytest.fixture
def init_test_db(tmp_data_dir: Path) -> Path:
    """Pre-populate the environment variables and call dockersetup.init_db()."""
    os.environ["APP_DATA_PATH"] = str(tmp_data_dir)
    os.environ["APP_PERSONALITY_PATH"] = str(tmp_data_dir / "personality.md")
    os.environ["APP_CONFIG_PATH"] = str(tmp_data_dir / "config.txt")

    # Avoid circular / side-effect imports – call init_db directly
    from dockersetup import init_db

    init_db()
    return tmp_data_dir


@pytest.fixture
def populated_db(init_test_db: Path) -> Path:
    """Return a temp DB that already has a few history rows."""
    import sqlite3

    db = str(init_test_db / "data.db")
    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    rows = [
        (1, "2026-06-01 10:00:00+02:00", "user_1", "dawid", "user", "Cześć!", None),
        (2, "2026-06-01 10:00:05+02:00", "user_1", "dawid", "user", "Hej Faust", None),
        (3, "2026-06-01 10:00:10+02:00", "bot_1", "Faust", "assistant", "Oh, it's you again.", None),
    ]
    cursor.executemany(
        "INSERT INTO history (is_event, time_stamp, user_id, username, role, content, raw_metadata) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()
    return init_test_db
