"""
Tests for identity_get.py — extracting the companion's name from a personality file.

get_companion_identity() reads a Markdown personality profile and uses a
fast LLM call to extract the companion's name.  Falls back to 'Faust' on
any error.
"""

import os
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Use the conftest's sys.path setup so we can import project modules
from identity_get import get_companion_identity


# ──────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────

class TestGetCompanionIdentity:
    """get_companion_identity() should extract or default to 'Faust'."""

    def test_returns_faust_for_missing_file(self, tmp_path):
        """If the personality file doesn't exist, fall back to 'Faust'."""
        missing_path = tmp_path / "nonexistent.md"
        assert not missing_path.exists()
        result = get_companion_identity(missing_path)
        assert result == "Faust"

    def test_returns_faust_for_empty_file(self, tmp_path):
        """If the personality file is empty, fall back to 'Faust'."""
        empty_path = tmp_path / "empty.md"
        empty_path.write_text("")
        result = get_companion_identity(empty_path)
        assert result == "Faust"

    @patch("identity_get.OpenAI")
    @patch("identity_get.open", create=True)
    def test_api_extracts_name_successfully(self, mock_open, mock_openai, tmp_path):
        """When the API works, return the extracted name."""
        pers_path = tmp_path / "personality.md"
        pers_path.write_text(
            "You are Mephistopheles, an overly polite demonic butler."
        )

        # Mock the file reading (identity_get uses Path.read_text, not open)
        # Actually we need to mock OpenAI, not the file system
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({"name": "Mephistopheles"})
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        result = get_companion_identity(pers_path)
        assert result == "Mephistopheles", f"Expected Mephistopheles, got {result!r}"

    @patch("identity_get.OpenAI")
    def test_api_failure_falls_back_to_faust(self, mock_openai, tmp_path):
        """If the API call fails, fall back to 'Faust'."""
        pers_path = tmp_path / "personality.md"
        pers_path.write_text(
            "You are a helpful tsundere assistant named Faust."
        )

        mock_openai.return_value.chat.completions.create.side_effect = \
            Exception("API timeout")

        result = get_companion_identity(pers_path)
        assert result == "Faust", f"Expected 'Faust' on API failure, got {result!r}"

    @patch("identity_get.OpenAI")
    def test_malformed_api_response_falls_back_to_faust(
        self, mock_openai, tmp_path
    ):
        """If the API returns invalid JSON, fall back to 'Faust'."""
        pers_path = tmp_path / "personality.md"
        pers_path.write_text("You are Faust.")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="Not valid JSON at all"
                )
            )
        ]
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        result = get_companion_identity(pers_path)
        assert result == "Faust", f"Expected 'Faust' on bad JSON, got {result!r}"

    @patch("identity_get.OpenAI")
    def test_api_returns_no_name_key(self, mock_openai, tmp_path):
        """If the JSON response lacks a 'name' key, default to 'Faust'."""
        pers_path = tmp_path / "personality.md"
        pers_path.write_text("Some random profile.")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({"unknown_key": "some_value"})
                )
            )
        ]
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        result = get_companion_identity(pers_path)
        assert result == "Faust", f"Expected 'Faust' when name key missing, got {result!r}"

    def test_accepts_string_path(self, tmp_path):
        """get_companion_identity should accept a string path as well."""
        pers_path = tmp_path / "str_test.md"
        pers_path.write_text("")
        result = get_companion_identity(str(pers_path))
        assert result == "Faust"

    def test_function_is_cached(self, tmp_path):
        """get_companion_identity should use @cache (no side effects test)."""
        from functools import cache
        assert hasattr(get_companion_identity, "cache_info")
        # Just verify cache info works (the @cache decorator adds this)


class TestIdentityGetModule:
    """Structural tests for identity_get."""

    def test_function_exists(self):
        """get_companion_identity should be importable."""
        from identity_get import get_companion_identity
        assert callable(get_companion_identity)
