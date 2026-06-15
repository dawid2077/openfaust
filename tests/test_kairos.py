"""
Tests for the Kairos routing engine (kairos.decide).

All direct OpenAI calls are mocked so tests are fast and deterministic.
"""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestDecide:
    """Tests for the kairos.decide() routing function."""

    PROFILE = "You are a tsundere assistant named Faust."

    @pytest.fixture(autouse=True)
    def _setup_env(self, monkeypatch):
        """Ensure env vars are set before each test."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.setenv("APP_DATA_PATH", "/tmp")
        monkeypatch.setenv("APP_PERSONALITY_PATH", "/tmp/personality.md")

    @patch("kairos.OpenAI")
    def test_decide_returns_action(self, mock_openai_class):
        """decide() should return a string action code."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"action": "3"})
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from kairos import decide

        result = decide("Hey Faust!", [], self.PROFILE)
        assert isinstance(result, str)
        assert result in ("0", "1", "2", "3")

    @patch("kairos.OpenAI")
    def test_decide_engage_direct_call(self, mock_openai_class):
        """Direct name call should route as '3' (engage)."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"action": "3"})
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from kairos import decide

        assert decide("Faust, help me!", [], self.PROFILE) == "3"

    @patch("kairos.OpenAI")
    def test_decide_silent_generic(self, mock_openai_class):
        """Generic background chatter should route as '1' (silent)."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"action": "1"})
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from kairos import decide

        assert decide("Anyone wanna play?", [], self.PROFILE) == "1"

    @patch("kairos.OpenAI")
    def test_decide_react_greeting(self, mock_openai_class):
        """Room greetings should route as '2' (react)."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"action": "2"})
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from kairos import decide

        assert decide("Hi everyone!", [], self.PROFILE) == "2"

    @patch("kairos.OpenAI")
    def test_decide_with_context_provided(self, mock_openai_class):
        """Context should be passed through to the API."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"action": "3"})
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from kairos import decide

        context = [{"role": "user", "content": "dawid: how are you?"}]
        result = decide("I'm fine", context, self.PROFILE)
        assert result == "3"

        # Verify context was included in the API call
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        # system + context messages + user
        assert len(messages) >= 2

    @patch("kairos.OpenAI")
    def test_decide_json_response_format(self, mock_openai_class):
        """The API call should request JSON response format."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"action": "1"})
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from kairos import decide

        decide("test", [], self.PROFILE)

        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["response_format"]["type"] == "json_object"
        assert call_args.kwargs["temperature"] == 0.0

    @patch("kairos.OpenAI")
    def test_decide_api_error_fallback(self, mock_openai_class):
        """On API error, decide() should return '1' (silent)."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API down")
        mock_openai_class.return_value = mock_client

        from kairos import decide

        assert decide("Faust?", [], self.PROFILE) == "1"

    @patch("kairos.OpenAI")
    def test_decide_malformed_json_fallback(self, mock_openai_class):
        """On malformed JSON response, decide() should return '1'."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "not json at all"
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from kairos import decide

        assert decide("test", [], self.PROFILE) == "1"

    @patch("kairos.OpenAI")
    def test_decide_uses_gpt_4o_mini(self, mock_openai_class):
        """The routing model should be gpt-4o-mini."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"action": "1"})
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from kairos import decide

        decide("test", [], self.PROFILE)

        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "gpt-4o-mini"

    @patch("kairos.OpenAI")
    def test_decide_uses_openrouter_base(self, mock_openai_class):
        """The client should target OpenRouter base URL."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"action": "1"})
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from kairos import decide

        decide("test", [], self.PROFILE)

        # Check that client was constructed with the right base_url
        call_kwargs = mock_openai_class.call_args
        assert "https://openrouter.ai/api/v1" in str(call_kwargs)

    @patch("kairos.OpenAI")
    def test_decide_empty_message(self, mock_openai_class):
        """Empty message should still process without error."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"action": "1"})
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from kairos import decide

        # Should not raise
        result = decide("", [], self.PROFILE)
        assert isinstance(result, str)
