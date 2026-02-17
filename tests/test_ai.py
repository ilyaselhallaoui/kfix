"""Tests for AI module."""

from unittest.mock import Mock

import pytest

from kfix.ai import Diagnostician


class TestDiagnostician:
    """Test suite for Diagnostician class."""

    def test_init(self):
        """Test Diagnostician initialization."""
        diagnostician = Diagnostician("test-api-key")
        assert diagnostician.client is not None

    def test_diagnose_pod(self, mock_anthropic_response, sample_pod_diagnostics):
        """Test pod diagnosis."""
        diagnostician = Diagnostician("test-api-key")
        diagnosis = diagnostician.diagnose_pod("test-pod", sample_pod_diagnostics)

        assert diagnosis == "This is a test diagnosis"
        mock_anthropic_response.assert_called_once()

        # Verify the API was called with correct parameters
        call_args = mock_anthropic_response.call_args
        assert call_args.kwargs["model"] == "claude-sonnet-4-5-20250929"
        assert call_args.kwargs["max_tokens"] == 1024
        assert "test-pod" in call_args.kwargs["messages"][0]["content"]

    def test_diagnose_node(self, mock_anthropic_response, sample_node_diagnostics):
        """Test node diagnosis."""
        diagnostician = Diagnostician("test-api-key")
        diagnosis = diagnostician.diagnose_node("test-node", sample_node_diagnostics)

        assert diagnosis == "This is a test diagnosis"
        mock_anthropic_response.assert_called_once()

        # Verify the prompt contains node name
        call_args = mock_anthropic_response.call_args
        assert "test-node" in call_args.kwargs["messages"][0]["content"]

    def test_diagnose_deployment(self, mock_anthropic_response, sample_deployment_diagnostics):
        """Test deployment diagnosis."""
        diagnostician = Diagnostician("test-api-key")
        diagnosis = diagnostician.diagnose_deployment(
            "test-deployment", sample_deployment_diagnostics
        )

        assert diagnosis == "This is a test diagnosis"
        mock_anthropic_response.assert_called_once()

        # Verify the prompt contains deployment name
        call_args = mock_anthropic_response.call_args
        assert "test-deployment" in call_args.kwargs["messages"][0]["content"]

    def test_diagnose_service(self, mock_anthropic_response, sample_service_diagnostics):
        """Test service diagnosis."""
        diagnostician = Diagnostician("test-api-key")
        diagnosis = diagnostician.diagnose_service("test-service", sample_service_diagnostics)

        assert diagnosis == "This is a test diagnosis"
        mock_anthropic_response.assert_called_once()

        # Verify the prompt contains service name
        call_args = mock_anthropic_response.call_args
        assert "test-service" in call_args.kwargs["messages"][0]["content"]

    def test_explain_error(self, mock_anthropic_response):
        """Test error explanation."""
        diagnostician = Diagnostician("test-api-key")
        explanation = diagnostician.explain_error("CrashLoopBackOff")

        assert explanation == "This is a test diagnosis"
        mock_anthropic_response.assert_called_once()

        # Verify the prompt contains the error
        call_args = mock_anthropic_response.call_args
        assert "CrashLoopBackOff" in call_args.kwargs["messages"][0]["content"]

    def test_diagnose_pod_with_missing_diagnostics(self, mock_anthropic_response):
        """Test pod diagnosis with missing diagnostic data."""
        diagnostician = Diagnostician("test-api-key")
        diagnostics = {"describe": "Some data"}  # Missing logs, events, yaml

        diagnosis = diagnostician.diagnose_pod("test-pod", diagnostics)

        assert diagnosis == "This is a test diagnosis"
        # Should handle missing keys gracefully with .get()
        call_args = mock_anthropic_response.call_args
        assert "N/A" in call_args.kwargs["messages"][0]["content"]

    def test_api_error_propagates(self, mocker):
        """Test that API errors are propagated."""
        mock_messages = Mock()
        mock_messages.create = Mock(side_effect=Exception("API Error"))

        mock_client = Mock()
        mock_client.messages = mock_messages

        mocker.patch("kfix.ai.Anthropic", return_value=mock_client)

        diagnostician = Diagnostician("test-api-key")

        with pytest.raises(Exception, match="API Error"):
            diagnostician.diagnose_pod("test-pod", {})
