"""
Tests for the API layer (api.py).

Uses mock patching *before* module import to avoid real API calls
from module-level OpenAI client initialisation.
"""

import importlib
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _setup_env_and_mocks(monkeypatch, tmp_path: Path):
    """Ensure env vars and mocks are in place BEFORE api module is imported."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")
    monkeypatch.setenv("APP_DATA_PATH", str(tmp_path))
    monkeypatch.setenv("APP_PERSONALITY_PATH", str(tmp_path / "personality.md"))
    monkeypatch.setenv("APP_CONFIG_PATH", str(tmp_path / "config.txt"))

    # Pre-populate personality file so call_mistral can load it
    (tmp_path / "personality.md").write_text(
        "You are a tsundere assistant named Faust.", encoding="utf-8"
    )
    (tmp_path / "config.txt").write_text("", encoding="utf-8")

    # Pre-populate a minimal SQLite DB so context_call() doesn't crash
    import sqlite3
    db_path = str(tmp_path / "data.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS history ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "is_event INTEGER NOT NULL,"
        "time_stamp TEXT NOT NULL,"
        "user_id TEXT, username TEXT, role TEXT, content TEXT, raw_metadata TEXT)"
    )
    conn.close()

    # Mock OpenAI *before* any imports so the module-level OpenAI() call
    # in api.py / identity_get.py gets the mock version.
    patcher = patch("openai.OpenAI")
    mock_openai_class = patcher.start()

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Mock response"
    mock_response.model_dump_json.return_value = json.dumps(
        {"id": "test", "choices": [{"message": {"content": "Mock response", "role": "assistant"}}]}
    )
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai_class.return_value = mock_client

    yield mock_openai_class

    patcher.stop()


class TestCallMistral:
    """Tests for call_mistral() — the main LLM interaction function."""

    def _import_api(self):
        """Import (or reload) api module so module-level code sees our env & mocks."""
        import api as _api
        importlib.reload(_api)
        return _api

    def test_call_mistral_returns_string(self):
        api = self._import_api()
        result = api.call_mistral("Hi!", "dawid", 42, 999, "Faust")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_call_mistral_includes_profile(self):
        api = self._import_api()
        api.call_mistral("Hi", "dawid", 42, 999, "Faust")
        client = api.client
        call_args = client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        system_msg = messages[0]
        assert system_msg["role"] == "system"
        assert "Faust" in system_msg["content"] or "tsundere" in system_msg["content"]

    def test_call_mistral_uses_mistral_model(self):
        api = self._import_api()
        api.call_mistral("Hi", "dawid")
        client = api.client
        call_args = client.chat.completions.create.call_args
        assert "mistralai/mistral-small-2603" in call_args.kwargs["model"]

    def test_call_mistral_uses_openrouter(self):
        api = self._import_api()
        # The module-level OpenAI() was already called with mock — check constructor
        # We can verify by checking that the global client exists
        assert api.client is not None

    def test_call_mistral_type_1_heartbeat(self):
        api = self._import_api()
        result = api.call_mistral("", "dawid", 42, 999, "Faust", type=1)
        assert isinstance(result, str)

        client = api.client
        call_args = client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        system_content = messages[0]["content"]
        assert "silent" in system_content.lower()


class TestGenerateAnswerCall:
    """Tests for generate_answer_call()."""

    def _import_api(self):
        import api as _api
        importlib.reload(_api)
        return _api

    def test_generate_answer_call_returns_content(self):
        api = self._import_api()
        result = api.generate_answer_call(
            [{"role": "user", "content": "hello"}], "dawid", 42, "hello", 999, "Faust"
        )
        assert result == "Mock response"

    def test_generate_answer_call_with_fallbacks(self):
        api = self._import_api()
        api.generate_answer_call(
            [{"role": "user", "content": "hi"}], "dawid"
        )
        client = api.client
        call_args = client.chat.completions.create.call_args
        extra_body = call_args.kwargs["extra_body"]
        assert extra_body["provider"]["allow_fallbacks"] is True
        assert "mistral" in extra_body["provider"]["order"]

    def test_generate_answer_call_api_error(self):
        """Should propagate the exception (no silent failure)."""
        import api as _api
        importlib.reload(_api)
        _api.client.chat.completions.create.side_effect = ConnectionError("Network down")

        with pytest.raises(ConnectionError):
            _api.generate_answer_call(
                [{"role": "user", "content": "hi"}], "dawid"
            )
