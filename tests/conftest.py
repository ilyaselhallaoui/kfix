"""Pytest configuration and fixtures."""

import subprocess
from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_subprocess_success(mocker):
    """Mock successful subprocess.run call."""
    mock_result = Mock()
    mock_result.stdout = "Success output"
    mock_result.stderr = ""
    mock_result.returncode = 0
    return mocker.patch("subprocess.run", return_value=mock_result)


@pytest.fixture
def mock_subprocess_failure(mocker):
    """Mock failed subprocess.run call."""
    mock_result = Mock()
    mock_result.stdout = ""
    mock_result.stderr = "Error: resource not found"
    mock_result.returncode = 1
    return mocker.patch("subprocess.run", return_value=mock_result)


@pytest.fixture
def mock_anthropic_response(mocker):
    """Mock Anthropic API response."""
    mock_content = Mock()
    mock_content.text = "This is a test diagnosis"

    mock_response = Mock()
    mock_response.content = [mock_content]

    # Mock the entire Anthropic client
    mock_messages = Mock()
    mock_messages.create = Mock(return_value=mock_response)

    mock_client = Mock()
    mock_client.messages = mock_messages

    mocker.patch("kfix.ai.Anthropic", return_value=mock_client)
    return mock_messages.create


@pytest.fixture
def sample_pod_diagnostics():
    """Sample pod diagnostics data."""
    return {
        "describe": "Name: test-pod\nStatus: Running\n",
        "logs": "Application started successfully\n",
        "events": "Normal  Started  pod/test-pod\n",
        "yaml": "apiVersion: v1\nkind: Pod\n",
    }


@pytest.fixture
def sample_node_diagnostics():
    """Sample node diagnostics data."""
    return {
        "describe": "Name: test-node\nStatus: Ready\n",
        "events": "Normal  NodeReady  node/test-node\n",
    }


@pytest.fixture
def sample_deployment_diagnostics():
    """Sample deployment diagnostics data."""
    return {
        "describe": "Name: test-deployment\nReplicas: 3 desired | 3 updated | 3 total | 3 available\n",
        "events": "Normal  ScalingReplicaSet  deployment/test-deployment\n",
    }


@pytest.fixture
def sample_service_diagnostics():
    """Sample service diagnostics data."""
    return {
        "describe": "Name: test-service\nType: ClusterIP\nPort: 80/TCP\n",
        "endpoints": "test-service   10.0.0.1:80,10.0.0.2:80\n",
    }
