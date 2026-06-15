"""
Tests for the Kairos semantic routing engine.

Kairos is the decision engine that classifies incoming messages:
  "1" = SILENT (ignore), "2" = REACT (casual), "3" = ENGAGE (full response)

These tests verify the routing logic with mocked API calls so they
run quickly and deterministically without external dependencies.
"""

import os
import sys
import json
from unittest.mock import patch, MagicMock
from pathlib import Path

import pytest

from kairos import decide


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def faust_profile():
    """Standard Faust tsundere personality profile."""
    return (
        "You are a helpful tsundere assistant named Faust who acts sharp, impatient, "
        "and playfully insulting as a defensive mask, but always provides the help the "
        "user needs; if the user is kind or clever, show a brief, reluctant hint of warmth "
        "before deflecting back to your sharp persona; always reply in the user's language "
        "or English, never use roleplay asterisks or describe physical actions, never start "
        "your message with a name tag, and talk directly to the user in text chat format."
    )


@pytest.fixture
def empty_context():
    """Empty conversation context."""
    return []


@pytest.fixture
def mock_openai_response():
    """Helper to create a mock OpenAI chat completion response."""
    def _make_response(action: str) -> MagicMock:
        mock = MagicMock()
        mock.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({"action": action})
                )
            )
        ]
        return mock
    return _make_response


# ──────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────

class TestDecideDirectResponseRouting:
    """Tests for decide() behaviour across different input types."""

    @patch("kairos.OpenAI")
    def test_direct_mention_returns_3(self, mock_openai, mock_openai_response, faust_profile, empty_context):
        """A message containing the companion's name should route as ENGAGE (3)."""
        mock_openai.return_value.chat.completions.create.return_value = mock_openai_response("3")
        result = decide("Hey Faust, can you help me?", empty_context, faust_profile)
        assert result == "3", f"Expected '3' for direct mention, got {result!r}"

    @patch("kairos.OpenAI")
    def test_greeting_returns_2(self, mock_openai, mock_openai_response, faust_profile, empty_context):
        """A casual greeting to the room should route as REACT (2)."""
        mock_openai.return_value.chat.completions.create.return_value = mock_openai_response("2")
        result = decide("Good morning everyone!", empty_context, faust_profile)
        assert result == "2", f"Expected '2' for greeting, got {result!r}"

    @patch("kairos.OpenAI")
    def test_user_to_user_chatter_returns_1(self, mock_openai, mock_openai_response, faust_profile, empty_context):
        """User-to-user chatter (not directed at companion) should route as SILENT (1)."""
        mock_openai.return_value.chat.completions.create.return_value = mock_openai_response("1")
        result = decide("Hey Mark, did you finish that report?", empty_context, faust_profile)
        assert result == "1", f"Expected '1' for user chatter, got {result!r}"

    @patch("kairos.OpenAI")
    def test_direct_question_returns_3(self, mock_openai, mock_openai_response, faust_profile, empty_context):
        """A direct question to the companion should route as ENGAGE (3)."""
        mock_openai.return_value.chat.completions.create.return_value = mock_openai_response("3")
        result = decide("Why are you always so mean to everyone?", empty_context, faust_profile)
        assert result == "3", f"Expected '3' for direct question, got {result!r}"


class TestDecideWithContext:
    """Tests with populated conversation context."""

    @patch("kairos.OpenAI")
    def test_with_populated_context(
        self, mock_openai, mock_openai_response, faust_profile
    ):
        """Decide should work correctly even with a full context list."""
        mock_openai.return_value.chat.completions.create.return_value = mock_openai_response("1")
        context = [
            {"role": "user", "content": "Alice: Hey guys"},
            {"role": "assistant", "content": "Oh, wonderful... humans."},
            {"role": "user", "content": "Bob: Anyone seen the new movie?"},
        ]
        result = decide("I think it was pretty good", context, faust_profile)
        assert result in ("1", "2", "3"), f"Unexpected routing result: {result!r}"


class TestDecideErrorHandling:
    """Tests for graceful degradation when API calls fail."""

    @patch("kairos.OpenAI")
    def test_api_failure_returns_1(self, mock_openai, faust_profile, empty_context):
        """When the API call fails, decide() should default to SILENT (1)."""
        mock_openai.return_value.chat.completions.create.side_effect = Exception("API timeout")
        result = decide("Hello?", empty_context, faust_profile)
        assert result == "1", f"Expected '1' on API failure, got {result!r}"

    @patch("kairos.OpenAI")
    def test_malformed_json_response(self, mock_openai, faust_profile, empty_context):
        """Non-JSON API responses should be handled safely."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content="Not JSON at all")
            )
        ]
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        result = decide("Hello?", empty_context, faust_profile)
        assert result == "1", f"Expected '1' on malformed JSON, got {result!r}"


class TestDecideProfileIndependence:
    """Kairos should be agnostic to the personality profile used."""

    @patch("kairos.OpenAI")
    def test_works_with_mephisto_profile(
        self, mock_openai, mock_openai_response, empty_context
    ):
        """Different character profiles should not break the router."""
        mephisto_profile = (
            "You are Mephistopheles, an overly polite, formal, and slightly "
            "sinister demonic butler."
        )
        mock_openai.return_value.chat.completions.create.return_value = mock_openai_response("2")
        result = decide("Good evening", empty_context, mephisto_profile)
        assert result == "2", f"Expected '2', got {result!r}"


class TestDecideModuleImport:
    """Structural tests for the kairos module."""

    def test_decide_function_exists(self):
        """The decide function should be importable."""
        from kairos import decide
        assert callable(decide)
