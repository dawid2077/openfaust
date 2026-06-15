"""
Tests for the identity extraction module (identity_get.py).

Uses mocked OpenAI calls so tests are fast, deterministic, and don't require an API key.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestGetCompanionIdentity:
    """Tests for get_companion_identity()."""

    @pytest.fixture(autouse=True)
    def _setup_env(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    @patch("identity_get.OpenAI")
    def test_extracts_name_from_profile(self, mock_openai_class, tmp_path: Path):
        """Should extract the companion name from the personality file."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"name": "Faust"})
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        profile = tmp_path / "personality.md"
        profile.write_text("You are a tsundere assistant named Faust.", encoding="utf-8")

        from identity_get import get_companion_identity

        name = get_companion_identity(profile)
        assert name == "Faust"

    @patch("identity_get.OpenAI")
    def test_extracts_custom_name(self, mock_openai_class, tmp_path: Path):
        """Should extract a custom name from the personality file."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"name": "Mephistopheles"})
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        profile = tmp_path / "personality.md"
        profile.write_text("You are a polite demon butler named Mephistopheles.", encoding="utf-8")

        from identity_get import get_companion_identity

        name = get_companion_identity(profile)
        assert name == "Mephistopheles"

    def test_returns_faust_for_missing_file(self, tmp_path: Path):
        """Missing personality file should fall back to 'Faust'."""
        missing = tmp_path / "nonexistent.md"

        from identity_get import get_companion_identity

        name = get_companion_identity(missing)
        assert name == "Faust"

    def test_returns_faust_for_empty_file(self, tmp_path: Path):
        """Empty personality file should fall back to 'Faust'."""
        empty = tmp_path / "empty.md"
        empty.write_text("", encoding="utf-8")

        from identity_get import get_companion_identity

        name = get_companion_identity(empty)
        assert name == "Faust"

    def test_returns_faust_for_whitespace_file(self, tmp_path: Path):
        """Whitespace-only personality file should fall back to 'Faust'."""
        ws = tmp_path / "whitespace.md"
        ws.write_text("   \n\n  \t  ", encoding="utf-8")

        from identity_get import get_companion_identity

        name = get_companion_identity(ws)
        assert name == "Faust"

    @patch("identity_get.OpenAI")
    def test_returns_faust_on_api_error(self, mock_openai_class, tmp_path: Path):
        """API failure should fall back gracefully to 'Faust'."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Connection refused")
        mock_openai_class.return_value = mock_client

        profile = tmp_path / "personality.md"
        profile.write_text("You are a friendly bot named Bob.", encoding="utf-8")

        from identity_get import get_companion_identity

        name = get_companion_identity(profile)
        assert name == "Faust"

    @patch("identity_get.OpenAI")
    def test_returns_faust_on_malformed_json(self, mock_openai_class, tmp_path: Path):
        """Malformed JSON from API should fall back to 'Faust'."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "not-json"
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        profile = tmp_path / "personality.md"
        profile.write_text("You are a bot named Bob.", encoding="utf-8")

        from identity_get import get_companion_identity

        name = get_companion_identity(profile)
        assert name == "Faust"

    @patch("identity_get.OpenAI")
    def test_uses_gpt_4o_mini_model(self, mock_openai_class, tmp_path: Path):
        """The extraction should use gpt-4o-mini."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"name": "Faust"})
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        profile = tmp_path / "personality.md"
        profile.write_text("You are Faust.", encoding="utf-8")

        from identity_get import get_companion_identity

        get_companion_identity(profile)

        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "gpt-4o-mini"

    @patch("identity_get.OpenAI")
    def test_result_cached(self, mock_openai_class, tmp_path: Path):
        """The @cache decorator should avoid duplicate API calls for the same file."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"name": "Faust"})
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        profile = tmp_path / "personality.md"
        profile.write_text("You are Faust.", encoding="utf-8")

        from identity_get import get_companion_identity

        # First call
        get_companion_identity(profile)
        # Second call should hit cache
        get_companion_identity(profile)

        # Should only have been called once
        assert mock_client.chat.completions.create.call_count == 1
