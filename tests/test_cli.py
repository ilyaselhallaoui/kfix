"""Tests for CLI module."""

import json
from unittest.mock import Mock

from typer.testing import CliRunner

from kfix.cli import app, apply_fixes, extract_kubectl_commands

runner = CliRunner()


class TestCLI:
    """Test suite for CLI commands."""

    def test_version_command(self):
        """Test version command."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "kfix version" in result.stdout

    def test_config_set_api_key(self, tmp_path, monkeypatch):
        """Test setting API key via CLI."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = runner.invoke(app, ["config", "set", "api-key", "test-key"])

        assert result.exit_code == 0
        assert "API key saved" in result.stdout

    def test_config_set_unknown_key(self):
        """Test setting unknown config key."""
        result = runner.invoke(app, ["config", "set", "unknown-key", "value"])

        assert result.exit_code == 1
        assert "Unknown config key" in result.stdout

    def test_diagnose_pod_no_api_key(self, tmp_path, monkeypatch):
        """Test diagnosing pod without API key configured."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        result = runner.invoke(app, ["diagnose", "pod", "test-pod"])

        assert result.exit_code == 1
        assert "No API key configured" in result.stdout

    def test_diagnose_pod_no_cluster_access(self, tmp_path, monkeypatch, mocker):
        """Test diagnosing pod without cluster access."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mocker.patch("kfix.kubectl.Kubectl.check_cluster_access", return_value=False)

        result = runner.invoke(app, ["diagnose", "pod", "test-pod"])

        assert result.exit_code == 1
        assert "Cannot access Kubernetes cluster" in result.stdout

    def test_diagnose_pod_success(self, tmp_path, monkeypatch, mocker):
        """Test successful pod diagnosis."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mocker.patch("kfix.kubectl.Kubectl.check_cluster_access", return_value=True)
        mocker.patch(
            "kfix.kubectl.Kubectl.gather_pod_diagnostics",
            return_value={"describe": "test", "logs": "test", "events": "test", "yaml": "test"},
        )
        mocker.patch("kfix.ai.Diagnostician.diagnose_pod", return_value="Test diagnosis")

        result = runner.invoke(app, ["diagnose", "pod", "test-pod", "-n", "default"])

        assert result.exit_code == 0
        assert "test-pod" in result.stdout

    def test_diagnose_node_success(self, tmp_path, monkeypatch, mocker):
        """Test successful node diagnosis."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mocker.patch("kfix.kubectl.Kubectl.check_cluster_access", return_value=True)
        mocker.patch(
            "kfix.kubectl.Kubectl.gather_node_diagnostics",
            return_value={"describe": "test", "events": "test"},
        )
        mocker.patch("kfix.ai.Diagnostician.diagnose_node", return_value="Test diagnosis")

        result = runner.invoke(app, ["diagnose", "node", "test-node"])

        assert result.exit_code == 0
        assert "test-node" in result.stdout

    def test_diagnose_deployment_success(self, tmp_path, monkeypatch, mocker):
        """Test successful deployment diagnosis."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mocker.patch("kfix.kubectl.Kubectl.check_cluster_access", return_value=True)
        mocker.patch(
            "kfix.kubectl.Kubectl.gather_deployment_diagnostics",
            return_value={"describe": "test", "events": "test"},
        )
        mocker.patch("kfix.ai.Diagnostician.diagnose_deployment", return_value="Test diagnosis")

        result = runner.invoke(app, ["diagnose", "deployment", "test-deployment"])

        assert result.exit_code == 0
        assert "test-deployment" in result.stdout

    def test_diagnose_service_success(self, tmp_path, monkeypatch, mocker):
        """Test successful service diagnosis."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mocker.patch("kfix.kubectl.Kubectl.check_cluster_access", return_value=True)
        mocker.patch(
            "kfix.kubectl.Kubectl.gather_service_diagnostics",
            return_value={"describe": "test", "endpoints": "test"},
        )
        mocker.patch("kfix.ai.Diagnostician.diagnose_service", return_value="Test diagnosis")

        result = runner.invoke(app, ["diagnose", "service", "test-service"])

        assert result.exit_code == 0
        assert "test-service" in result.stdout

    def test_explain_command(self, tmp_path, monkeypatch, mocker):
        """Test explain command."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mocker.patch("kfix.ai.Diagnostician.explain_error", return_value="Test explanation")

        result = runner.invoke(app, ["explain", "CrashLoopBackOff"])

        assert result.exit_code == 0
        assert "Error Explanation" in result.stdout

    def test_kubectl_error_handling(self, tmp_path, monkeypatch, mocker):
        """Test handling of kubectl errors."""
        from pathlib import Path

        from kfix.kubectl import KubectlError

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mocker.patch("kfix.kubectl.Kubectl.check_cluster_access", return_value=True)
        mocker.patch(
            "kfix.kubectl.Kubectl.gather_pod_diagnostics",
            side_effect=KubectlError("Pod not found"),
        )

        result = runner.invoke(app, ["diagnose", "pod", "missing-pod"])

        assert result.exit_code == 1
        assert "Pod not found" in result.stdout

    def test_ai_error_handling(self, tmp_path, monkeypatch, mocker):
        """Test handling of AI API errors."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mocker.patch("kfix.kubectl.Kubectl.check_cluster_access", return_value=True)
        mocker.patch(
            "kfix.kubectl.Kubectl.gather_pod_diagnostics",
            return_value={"describe": "test"},
        )
        mocker.patch(
            "kfix.ai.Diagnostician.diagnose_pod",
            side_effect=Exception("API Error"),
        )

        result = runner.invoke(app, ["diagnose", "pod", "test-pod"])

        assert result.exit_code == 1
        assert "Failed to get AI diagnosis" in result.stdout


class TestContextFlag:
    """Tests for --context flag passthrough."""

    def test_diagnose_pod_with_context(self, tmp_path, monkeypatch, mocker):
        """Test --context flag is passed to Kubectl."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mock_kubectl_cls = mocker.patch("kfix.cli.Kubectl")
        mock_kubectl = Mock()
        mock_kubectl.check_cluster_access.return_value = True
        mock_kubectl.gather_pod_diagnostics.return_value = {
            "describe": "test", "logs": "test", "events": "test", "yaml": "test",
        }
        mock_kubectl_cls.return_value = mock_kubectl

        mocker.patch("kfix.ai.Diagnostician.diagnose_pod", return_value="Test diagnosis")

        result = runner.invoke(
            app, ["diagnose", "pod", "test-pod", "--context", "my-cluster"]
        )

        assert result.exit_code == 0
        mock_kubectl_cls.assert_called_once_with(use_cache=True, context="my-cluster")

    def test_diagnose_node_with_context(self, tmp_path, monkeypatch, mocker):
        """Test --context flag on node diagnosis."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mock_kubectl_cls = mocker.patch("kfix.cli.Kubectl")
        mock_kubectl = Mock()
        mock_kubectl.check_cluster_access.return_value = True
        mock_kubectl.gather_node_diagnostics.return_value = {
            "describe": "test", "events": "test",
        }
        mock_kubectl_cls.return_value = mock_kubectl

        mocker.patch("kfix.ai.Diagnostician.diagnose_node", return_value="Test diagnosis")

        result = runner.invoke(
            app, ["diagnose", "node", "test-node", "--context", "staging"]
        )

        assert result.exit_code == 0
        mock_kubectl_cls.assert_called_once_with(use_cache=True, context="staging")


class TestScanCommand:
    """Tests for the kfix scan command."""

    def test_scan_no_unhealthy(self, tmp_path, monkeypatch, mocker):
        """Test scan when no unhealthy resources found."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mocker.patch("kfix.kubectl.Kubectl.check_cluster_access", return_value=True)
        mocker.patch("kfix.kubectl.Kubectl.scan_namespace", return_value=[])

        result = runner.invoke(app, ["scan", "-n", "default"])

        assert result.exit_code == 0
        assert "No unhealthy resources found" in result.stdout

    def test_scan_with_unhealthy_pod(self, tmp_path, monkeypatch, mocker):
        """Test scan finds and diagnoses unhealthy pods."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mocker.patch("kfix.kubectl.Kubectl.check_cluster_access", return_value=True)
        mocker.patch("kfix.kubectl.Kubectl.scan_namespace", return_value=[
            {
                "kind": "pod",
                "name": "broken-pod",
                "namespace": "default",
                "status": "CrashLoopBackOff",
                "reason": "CrashLoopBackOff",
            },
        ])
        mocker.patch(
            "kfix.kubectl.Kubectl.gather_pod_diagnostics",
            return_value={"describe": "test", "logs": "error", "events": "crash", "yaml": ""},
        )
        mocker.patch("kfix.ai.Diagnostician.diagnose_pod", return_value="Fix: restart the pod")
        mocker.patch("kfix.ai.Diagnostician.get_token_usage", return_value=None)

        result = runner.invoke(app, ["scan", "-n", "default"])

        assert result.exit_code == 0
        assert "broken-pod" in result.stdout
        assert "Unhealthy Resources" in result.stdout

    def test_scan_json_output(self, tmp_path, monkeypatch, mocker):
        """Test scan with JSON output format."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mocker.patch("kfix.kubectl.Kubectl.check_cluster_access", return_value=True)
        mocker.patch("kfix.kubectl.Kubectl.scan_namespace", return_value=[])

        result = runner.invoke(app, ["scan", "-n", "default", "-o", "json"])

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["resources"] == []
        assert output["total"] == 0

    def test_scan_all_namespaces(self, tmp_path, monkeypatch, mocker):
        """Test scan with --all-namespaces flag."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mocker.patch("kfix.kubectl.Kubectl.check_cluster_access", return_value=True)
        mocker.patch("kfix.kubectl.Kubectl.scan_all_namespaces", return_value=[])

        result = runner.invoke(app, ["scan", "--all-namespaces"])

        assert result.exit_code == 0

    def test_scan_no_cluster_access(self, tmp_path, monkeypatch, mocker):
        """Test scan without cluster access."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mocker.patch("kfix.kubectl.Kubectl.check_cluster_access", return_value=False)

        result = runner.invoke(app, ["scan"])

        assert result.exit_code == 1
        assert "Cannot access Kubernetes cluster" in result.stdout

    def test_scan_with_context(self, tmp_path, monkeypatch, mocker):
        """Test scan with --context flag."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mock_kubectl_cls = mocker.patch("kfix.cli.Kubectl")
        mock_kubectl = Mock()
        mock_kubectl.check_cluster_access.return_value = True
        mock_kubectl.scan_namespace.return_value = []
        mock_kubectl_cls.return_value = mock_kubectl

        result = runner.invoke(app, ["scan", "-n", "prod", "--context", "my-cluster"])

        assert result.exit_code == 0
        mock_kubectl_cls.assert_called_once_with(context="my-cluster")


class TestExtractKubectlCommands:
    """Tests for kubectl command extraction."""

    def test_extract_from_code_block(self):
        """Test extracting commands from markdown code blocks."""
        diagnosis = """## Fix
```bash
kubectl rollout restart deployment/my-app -n production
kubectl get pods -n production
```"""
        commands = extract_kubectl_commands(diagnosis)
        assert len(commands) == 2
        assert "kubectl rollout restart" in commands[0]

    def test_extract_from_inline(self):
        """Test extracting commands from inline backticks."""
        diagnosis = "Run `kubectl delete pod broken-pod` to fix."
        commands = extract_kubectl_commands(diagnosis)
        assert len(commands) == 1
        assert "kubectl delete pod broken-pod" in commands[0]

    def test_no_commands(self):
        """Test when no kubectl commands are present."""
        diagnosis = "Everything looks fine."
        commands = extract_kubectl_commands(diagnosis)
        assert commands == []


class TestAutoFixPolicy:
    """Tests for auto-fix safety policy handling."""

    def test_safe_policy_blocks_delete(self, mocker):
        """Test safe policy does not execute risky commands."""
        run_mock = mocker.patch("subprocess.run")
        apply_fixes(["kubectl delete pod bad-pod -n default"], auto_yes=True, policy="safe")
        run_mock.assert_not_called()
