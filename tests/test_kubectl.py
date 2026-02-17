"""Tests for kubectl module."""

import subprocess
from unittest.mock import Mock

import pytest

from kfix.kubectl import Kubectl, KubectlError


class TestKubectl:
    """Test suite for Kubectl class."""

    def test_check_cluster_access_success(self, mock_subprocess_success):
        """Test successful cluster access check."""
        kubectl = Kubectl()
        assert kubectl.check_cluster_access() is True
        mock_subprocess_success.assert_called_once()

    def test_check_cluster_access_failure(self, mocker):
        """Test failed cluster access check."""
        # Mock subprocess to raise an error
        mocker.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("kubectl", 30))

        kubectl = Kubectl()
        assert kubectl.check_cluster_access() is False

    def test_get_pod_logs_success(self, mock_subprocess_success):
        """Test getting pod logs successfully."""
        kubectl = Kubectl()
        logs = kubectl.get_pod_logs("test-pod", "default")
        assert logs == "Success output"
        mock_subprocess_success.assert_called_once()

    def test_get_pod_logs_failure(self, mocker):
        """Test getting pod logs failure returns empty string."""
        mocker.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("kubectl", 30))
        kubectl = Kubectl()
        logs = kubectl.get_pod_logs("test-pod", "default")
        assert logs == ""

    def test_describe_pod_success(self, mock_subprocess_success):
        """Test describing a pod successfully."""
        kubectl = Kubectl()
        description = kubectl.describe_pod("test-pod", "default")
        assert description == "Success output"

    def test_describe_pod_failure(self, mock_subprocess_failure):
        """Test describing a non-existent pod raises error."""
        kubectl = Kubectl()
        with pytest.raises(KubectlError):
            kubectl.describe_pod("non-existent-pod", "default")

    def test_get_pod_events(self, mock_subprocess_success):
        """Test getting pod events."""
        kubectl = Kubectl()
        events = kubectl.get_pod_events("test-pod", "default")
        assert events == "Success output"

    def test_get_pod_yaml(self, mock_subprocess_success):
        """Test getting pod YAML."""
        kubectl = Kubectl()
        yaml_output = kubectl.get_pod_yaml("test-pod", "default")
        assert yaml_output == "Success output"

    def test_describe_node_success(self, mock_subprocess_success):
        """Test describing a node successfully."""
        kubectl = Kubectl()
        description = kubectl.describe_node("test-node")
        assert description == "Success output"

    def test_get_node_events(self, mock_subprocess_success):
        """Test getting node events."""
        kubectl = Kubectl()
        events = kubectl.get_node_events("test-node")
        assert events == "Success output"

    def test_describe_deployment_success(self, mock_subprocess_success):
        """Test describing a deployment successfully."""
        kubectl = Kubectl()
        description = kubectl.describe_deployment("test-deployment", "default")
        assert description == "Success output"

    def test_get_deployment_events(self, mock_subprocess_success):
        """Test getting deployment events."""
        kubectl = Kubectl()
        events = kubectl.get_deployment_events("test-deployment", "default")
        assert events == "Success output"

    def test_describe_service_success(self, mock_subprocess_success):
        """Test describing a service successfully."""
        kubectl = Kubectl()
        description = kubectl.describe_service("test-service", "default")
        assert description == "Success output"

    def test_get_service_endpoints(self, mock_subprocess_success):
        """Test getting service endpoints."""
        kubectl = Kubectl()
        endpoints = kubectl.get_service_endpoints("test-service", "default")
        assert endpoints == "Success output"

    def test_gather_pod_diagnostics(self, mocker):
        """Test gathering all pod diagnostics."""
        kubectl = Kubectl()

        # Mock all methods
        mocker.patch.object(kubectl, "describe_pod", return_value="describe output")
        mocker.patch.object(kubectl, "get_pod_logs", return_value="logs output")
        mocker.patch.object(kubectl, "get_pod_events", return_value="events output")
        mocker.patch.object(kubectl, "get_pod_yaml", return_value="yaml output")

        diagnostics = kubectl.gather_pod_diagnostics("test-pod", "default")

        assert diagnostics["describe"] == "describe output"
        assert diagnostics["logs"] == "logs output"
        assert diagnostics["events"] == "events output"
        assert diagnostics["yaml"] == "yaml output"

    def test_gather_node_diagnostics(self, mocker):
        """Test gathering all node diagnostics."""
        kubectl = Kubectl()

        # Mock all methods
        mocker.patch.object(kubectl, "describe_node", return_value="describe output")
        mocker.patch.object(kubectl, "get_node_events", return_value="events output")

        diagnostics = kubectl.gather_node_diagnostics("test-node")

        assert diagnostics["describe"] == "describe output"
        assert diagnostics["events"] == "events output"

    def test_gather_deployment_diagnostics(self, mocker):
        """Test gathering all deployment diagnostics."""
        kubectl = Kubectl()

        # Mock all methods
        mocker.patch.object(kubectl, "describe_deployment", return_value="describe output")
        mocker.patch.object(kubectl, "get_deployment_events", return_value="events output")

        diagnostics = kubectl.gather_deployment_diagnostics("test-deployment", "default")

        assert diagnostics["describe"] == "describe output"
        assert diagnostics["events"] == "events output"

    def test_gather_service_diagnostics(self, mocker):
        """Test gathering all service diagnostics."""
        kubectl = Kubectl()

        # Mock all methods
        mocker.patch.object(kubectl, "describe_service", return_value="describe output")
        mocker.patch.object(kubectl, "get_service_endpoints", return_value="endpoints output")

        diagnostics = kubectl.gather_service_diagnostics("test-service", "default")

        assert diagnostics["describe"] == "describe output"
        assert diagnostics["endpoints"] == "endpoints output"

    def test_kubectl_timeout(self, mocker):
        """Test kubectl command timeout."""
        mocker.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("kubectl", 30))
        kubectl = Kubectl()

        with pytest.raises(KubectlError, match="timed out"):
            kubectl._run(["get", "pods"])

    def test_kubectl_not_found(self, mocker):
        """Test kubectl not installed."""
        mocker.patch("subprocess.run", side_effect=FileNotFoundError())
        kubectl = Kubectl()

        with pytest.raises(KubectlError, match="kubectl not found"):
            kubectl._run(["get", "pods"])
