"""Tests for kubectl module."""

import json
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

        mocker.patch.object(kubectl, "describe_node", return_value="describe output")
        mocker.patch.object(kubectl, "get_node_events", return_value="events output")

        diagnostics = kubectl.gather_node_diagnostics("test-node")

        assert diagnostics["describe"] == "describe output"
        assert diagnostics["events"] == "events output"

    def test_gather_deployment_diagnostics(self, mocker):
        """Test gathering all deployment diagnostics."""
        kubectl = Kubectl()

        mocker.patch.object(kubectl, "describe_deployment", return_value="describe output")
        mocker.patch.object(kubectl, "get_deployment_events", return_value="events output")

        diagnostics = kubectl.gather_deployment_diagnostics("test-deployment", "default")

        assert diagnostics["describe"] == "describe output"
        assert diagnostics["events"] == "events output"

    def test_gather_service_diagnostics(self, mocker):
        """Test gathering all service diagnostics."""
        kubectl = Kubectl()

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


class TestKubectlContext:
    """Tests for --context support in Kubectl."""

    def test_context_prepended_to_args(self, mocker):
        """Test that --context is prepended to kubectl args."""
        mock_result = Mock()
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run = mocker.patch("subprocess.run", return_value=mock_result)

        kubectl = Kubectl(context="my-cluster")
        kubectl._run(["get", "pods"], check=False)

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["kubectl", "--context", "my-cluster", "get", "pods"]

    def test_no_context_no_extra_args(self, mocker):
        """Test that no --context means no extra args."""
        mock_result = Mock()
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run = mocker.patch("subprocess.run", return_value=mock_result)

        kubectl = Kubectl()
        kubectl._run(["get", "pods"], check=False)

        args = mock_run.call_args[0][0]
        assert args == ["kubectl", "get", "pods"]


class TestScanNamespace:
    """Tests for scan_namespace and scan_all_namespaces."""

    def test_scan_namespace_unhealthy_pod(self, mocker):
        """Test scanning namespace finds unhealthy pods."""
        pods_json = json.dumps({
            "items": [
                {
                    "metadata": {"name": "healthy-pod"},
                    "status": {"phase": "Running"},
                },
                {
                    "metadata": {"name": "broken-pod"},
                    "status": {
                        "phase": "Pending",
                        "containerStatuses": [
                            {"state": {"waiting": {"reason": "ImagePullBackOff"}}}
                        ],
                    },
                },
            ]
        })
        deployments_json = json.dumps({"items": []})
        nodes_json = json.dumps({"items": []})

        def mock_run(args, **kwargs):
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stderr = ""
            cmd = " ".join(args)
            if "get pods" in cmd or "get,pods" in cmd:
                mock_result.stdout = pods_json
            elif "get deployments" in cmd:
                mock_result.stdout = deployments_json
            elif "get nodes" in cmd:
                mock_result.stdout = nodes_json
            else:
                mock_result.stdout = ""
            return mock_result

        mocker.patch("subprocess.run", side_effect=mock_run)

        kubectl = Kubectl(use_cache=False)
        results = kubectl.scan_namespace("default")

        pod_results = [r for r in results if r["kind"] == "pod"]
        assert len(pod_results) == 1
        assert pod_results[0]["name"] == "broken-pod"
        assert pod_results[0]["reason"] == "ImagePullBackOff"

    def test_scan_namespace_unhealthy_deployment(self, mocker):
        """Test scanning namespace finds unhealthy deployments."""
        pods_json = json.dumps({"items": []})
        deployments_json = json.dumps({
            "items": [
                {
                    "metadata": {"name": "broken-deploy"},
                    "spec": {"replicas": 3},
                    "status": {"availableReplicas": 1},
                },
            ]
        })
        nodes_json = json.dumps({"items": []})

        def mock_run(args, **kwargs):
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stderr = ""
            cmd = " ".join(args)
            if "get pods" in cmd:
                mock_result.stdout = pods_json
            elif "get deployments" in cmd:
                mock_result.stdout = deployments_json
            elif "get nodes" in cmd:
                mock_result.stdout = nodes_json
            else:
                mock_result.stdout = ""
            return mock_result

        mocker.patch("subprocess.run", side_effect=mock_run)

        kubectl = Kubectl(use_cache=False)
        results = kubectl.scan_namespace("default")

        deploy_results = [r for r in results if r["kind"] == "deployment"]
        assert len(deploy_results) == 1
        assert deploy_results[0]["name"] == "broken-deploy"
        assert "1/3" in deploy_results[0]["status"]

    def test_scan_namespace_all_healthy(self, mocker):
        """Test scanning namespace with all healthy resources."""
        pods_json = json.dumps({
            "items": [
                {"metadata": {"name": "good-pod"}, "status": {"phase": "Running"}},
            ]
        })
        deployments_json = json.dumps({
            "items": [
                {
                    "metadata": {"name": "good-deploy"},
                    "spec": {"replicas": 2},
                    "status": {"availableReplicas": 2},
                },
            ]
        })
        nodes_json = json.dumps({
            "items": [
                {
                    "metadata": {"name": "good-node"},
                    "status": {
                        "conditions": [{"type": "Ready", "status": "True", "reason": "KubeletReady"}]
                    },
                },
            ]
        })

        def mock_run(args, **kwargs):
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stderr = ""
            cmd = " ".join(args)
            if "get pods" in cmd:
                mock_result.stdout = pods_json
            elif "get deployments" in cmd:
                mock_result.stdout = deployments_json
            elif "get nodes" in cmd:
                mock_result.stdout = nodes_json
            else:
                mock_result.stdout = ""
            return mock_result

        mocker.patch("subprocess.run", side_effect=mock_run)

        kubectl = Kubectl(use_cache=False)
        results = kubectl.scan_namespace("default")

        assert len(results) == 0

    def test_pod_failure_reason_waiting(self):
        """Test extracting failure reason from waiting container."""
        pod = {
            "status": {
                "containerStatuses": [
                    {"state": {"waiting": {"reason": "CrashLoopBackOff"}}}
                ]
            }
        }
        assert Kubectl._pod_failure_reason(pod) == "CrashLoopBackOff"

    def test_pod_failure_reason_terminated(self):
        """Test extracting failure reason from terminated container."""
        pod = {
            "status": {
                "containerStatuses": [
                    {"state": {"terminated": {"reason": "OOMKilled"}}}
                ]
            }
        }
        assert Kubectl._pod_failure_reason(pod) == "OOMKilled"

    def test_pod_failure_reason_unknown(self):
        """Test extracting failure reason when status is unknown."""
        pod = {"status": {}}
        assert Kubectl._pod_failure_reason(pod) == "Unknown"
