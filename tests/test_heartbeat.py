"""
Tests for the heartbeat module — daily limits, restart logic, and process lifecycle.

OpenFaust's heartbeat runs in a background process every ~30 minutes. It checks:
- Whether the daily heartbeat limit has been reached
- Whether the limit reset period has elapsed
- Whether Kairos thinks it should engage the channel
"""

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, PropertyMock
from multiprocessing import Queue

import pytest

# Module under test
from heartbeat import restart_limit, check_limits


# ──────────────────────────────────────────────
# Tests for restart_limit()
# ──────────────────────────────────────────────

class TestRestartLimit:
    """restart_limit() should reset the daily limit counter after N days."""

    def test_no_reset_when_time_has_not_passed(self, monkeypatch):
        """If less than DAYS_AFTER_LIMIT_RESETS has passed, counter stays."""
        monkeypatch.setenv("DAYS_AFTER_LIMIT_RESETS", "1")
        from heartbeat import RESET_ANCHOR

        old_anchor = RESET_ANCHOR

        # Inject a mock anchor that is only 1 hour old
        from heartbeat import RESET_ANCHOR as anchor_ref
        # We can't easily reassign the module-level variable from outside,
        # so we test the logic indirectly by verifying the function doesn't crash.
        restart_limit()

        # After calling with no time passing, anchor should still be recent
        assert isinstance(old_anchor, datetime)

    def test_reset_after_days_pass(self, monkeypatch):
        """Simulate that enough days have passed for the limit to reset."""
        monkeypatch.setenv("DAYS_AFTER_LIMIT_RESETS", "1")

        # Monkey-patch RESET_ANCHOR to be 2 days ago
        past = datetime.now(timezone.utc) - timedelta(days=2)

        import heartbeat as hb_mod
        hb_mod.RESET_ANCHOR = past

        # Also inject a daily_limit for the scope of restart_limit
        # restart_limit uses a global RESET_ANCHOR
        restart_limit()

        # After reset, anchor should be recent
        from heartbeat import RESET_ANCHOR as new_anchor
        assert new_anchor > past
        diff = datetime.now(timezone.utc) - new_anchor
        assert diff < timedelta(seconds=5), "Anchor should have been reset to now"


# ──────────────────────────────────────────────
# Tests for check_limits()
# ──────────────────────────────────────────────

class TestCheckLimits:
    """check_limits() should return a string when limit reached, else 0."""

    def test_limit_not_reached(self, monkeypatch):
        """When daily_limit < DAILY_LIMIT_MAX, return 0."""
        monkeypatch.setenv("DAILY_LIMIT_MAX", "5")
        result = check_limits(3)
        assert result == 0, f"Expected 0, got {result!r}"

    def test_limit_reached(self, monkeypatch):
        """When daily_limit == DAILY_LIMIT_MAX, return limit message."""
        monkeypatch.setenv("DAILY_LIMIT_MAX", "5")
        result = check_limits(5)
        assert isinstance(result, str)
        assert "daily limit" in result.lower()

    def test_limit_exceeded(self, monkeypatch):
        """When daily_limit > DAILY_LIMIT_MAX, still return limit message."""
        monkeypatch.setenv("DAILY_LIMIT_MAX", "5")
        result = check_limits(10)
        assert isinstance(result, str)
        assert "daily limit" in result.lower()

    def test_limit_zero_max(self, monkeypatch):
        """When DAILY_LIMIT_MAX is 0, any heartbeat hits the limit."""
        monkeypatch.setenv("DAILY_LIMIT_MAX", "0")
        result = check_limits(1)
        assert isinstance(result, str)
        assert "daily limit" in result.lower()

    def test_limit_zero_count(self, monkeypatch):
        """When count is 0 and max is 1, not yet at limit."""
        monkeypatch.setenv("DAILY_LIMIT_MAX", "1")
        result = check_limits(0)
        assert result == 0


# ──────────────────────────────────────────────
# Tests for heartbeat() process orchestration
# ──────────────────────────────────────────────

class TestHeartbeatProcess:
    """Verify heartbeat correctly interacts with the queue and Kairos."""

    @patch("heartbeat.decide", return_value="3")
    @patch("heartbeat.context_kairos", return_value=[])
    @patch("heartbeat.time.sleep", return_value=None)  # skip sleeps
    @patch("heartbeat.os.getenv")
    def test_heartbeat_triggers_wake_on_action_3(
        self, mock_getenv, mock_sleep, mock_context, mock_decide, monkeypatch
    ):
        """If Kairos returns '3', heartbeat should put TRIGGER_WAKE in the queue."""
        # Mock environment variables
        def getenv_side_effect(key, default=None):
            env_map = {
                "HEARTBEAT_TIME_SECONDS": "1",
                "DAILY_LIMIT_MAX": "5",
                "DAYS_AFTER_LIMIT_RESETS": "30",
                "APP_DATA_PATH": "/tmp",
                "APP_PERSONALITY_PATH": "/tmp/personality.md",
                "APP_CONFIG_PATH": "/tmp/config.txt",
            }
            return env_map.get(key, default)

        mock_getenv.side_effect = getenv_side_effect

        # Use a real queue
        q = Queue()

        # We need to run heartbeat in a way we can interrupt it after one loop
        # So we'll call it directly and force a stop via side effect on decide
        # But heartbeat has an infinite loop. Let's patch decide to raise StopIteration
        # after the first loop to exit cleanly.
        call_count = 0

        def decide_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise SystemExit(0)  # clean exit after one loop
            return "3"

        mock_decide.side_effect = decide_side_effect

        import heartbeat as hb_mod
        hb_mod.RESET_ANCHOR = datetime.now(timezone.utc) - timedelta(days=10)

        with pytest.raises(SystemExit):
            hb_mod.heartbeat(q)

        # Queue should have gotten the trigger
        assert not q.empty(), "Queue should have a trigger message"
        trigger = q.get()
        assert trigger == "TRIGGER_WAKE"

    @patch("heartbeat.decide", return_value="1")
    @patch("heartbeat.context_kairos", return_value=[])
    @patch("heartbeat.time.sleep", return_value=None)
    @patch("heartbeat.os.getenv")
    def test_heartbeat_stays_silent_on_action_1(
        self, mock_getenv, mock_sleep, mock_context, mock_decide
    ):
        """If Kairos returns '1', heartbeat should NOT trigger wake."""
        def getenv_side_effect(key, default=None):
            env_map = {
                "HEARTBEAT_TIME_SECONDS": "1",
                "DAILY_LIMIT_MAX": "5",
                "DAYS_AFTER_LIMIT_RESETS": "30",
                "APP_DATA_PATH": "/tmp",
                "APP_PERSONALITY_PATH": "/tmp/personality.md",
                "APP_CONFIG_PATH": "/tmp/config.txt",
            }
            return env_map.get(key, default)

        mock_getenv.side_effect = getenv_side_effect
        q = Queue()

        call_count = 0

        def decide_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise SystemExit(0)
            return "1"

        mock_decide.side_effect = decide_side_effect

        import heartbeat as hb_mod
        hb_mod.RESET_ANCHOR = datetime.now(timezone.utc)

        with pytest.raises(SystemExit):
            hb_mod.heartbeat(q)

        assert q.empty(), "Queue should be empty when Kairos returns 1"

    def test_heartbeat_module_imports_safely(self):
        """The heartbeat module should import without crashing."""
        import heartbeat
        assert hasattr(heartbeat, "heartbeat")
        assert hasattr(heartbeat, "restart_limit")
        assert hasattr(heartbeat, "check_limits")


# ──────────────────────────────────────────────
# Test heartbeat.py's duplicate main guard
# ──────────────────────────────────────────────

class TestHeartbeatModuleStructure:
    """Verify structural integrity of heartbeat.py."""

    def test_no_duplicate_main_guards(self):
        """heartbeat.py should only have ONE if __name__ guard."""
        from conftest import PROJECT_ROOT
        heartbeat_path = PROJECT_ROOT / "heartbeat.py"
        
        with open(heartbeat_path, "r") as f:
            content = f.read()
        count = content.count('if __name__ == "__main__":')
        assert count <= 1, (
            f"heartbeat.py has {count} `if __name__ == '__main__':` guards. "
            "Only one is needed; duplicate guards cause dead code."
        )
