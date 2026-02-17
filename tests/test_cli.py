"""Tests for CLI module."""

from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from kfix.cli import app

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

        # Mock kubectl to fail
        mocker.patch("kfix.kubectl.Kubectl.check_cluster_access", return_value=False)

        result = runner.invoke(app, ["diagnose", "pod", "test-pod"])

        assert result.exit_code == 1
        assert "Cannot access Kubernetes cluster" in result.stdout

    def test_diagnose_pod_success(self, tmp_path, monkeypatch, mocker):
        """Test successful pod diagnosis."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        # Mock kubectl
        mocker.patch("kfix.kubectl.Kubectl.check_cluster_access", return_value=True)
        mocker.patch(
            "kfix.kubectl.Kubectl.gather_pod_diagnostics",
            return_value={"describe": "test", "logs": "test", "events": "test", "yaml": "test"},
        )

        # Mock AI
        mocker.patch("kfix.ai.Diagnostician.diagnose_pod", return_value="Test diagnosis")

        result = runner.invoke(app, ["diagnose", "pod", "test-pod", "-n", "default"])

        assert result.exit_code == 0
        assert "test-pod" in result.stdout

    def test_diagnose_node_success(self, tmp_path, monkeypatch, mocker):
        """Test successful node diagnosis."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        # Mock kubectl
        mocker.patch("kfix.kubectl.Kubectl.check_cluster_access", return_value=True)
        mocker.patch(
            "kfix.kubectl.Kubectl.gather_node_diagnostics",
            return_value={"describe": "test", "events": "test"},
        )

        # Mock AI
        mocker.patch("kfix.ai.Diagnostician.diagnose_node", return_value="Test diagnosis")

        result = runner.invoke(app, ["diagnose", "node", "test-node"])

        assert result.exit_code == 0
        assert "test-node" in result.stdout

    def test_diagnose_deployment_success(self, tmp_path, monkeypatch, mocker):
        """Test successful deployment diagnosis."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        # Mock kubectl
        mocker.patch("kfix.kubectl.Kubectl.check_cluster_access", return_value=True)
        mocker.patch(
            "kfix.kubectl.Kubectl.gather_deployment_diagnostics",
            return_value={"describe": "test", "events": "test"},
        )

        # Mock AI
        mocker.patch("kfix.ai.Diagnostician.diagnose_deployment", return_value="Test diagnosis")

        result = runner.invoke(app, ["diagnose", "deployment", "test-deployment"])

        assert result.exit_code == 0
        assert "test-deployment" in result.stdout

    def test_diagnose_service_success(self, tmp_path, monkeypatch, mocker):
        """Test successful service diagnosis."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        # Mock kubectl
        mocker.patch("kfix.kubectl.Kubectl.check_cluster_access", return_value=True)
        mocker.patch(
            "kfix.kubectl.Kubectl.gather_service_diagnostics",
            return_value={"describe": "test", "endpoints": "test"},
        )

        # Mock AI
        mocker.patch("kfix.ai.Diagnostician.diagnose_service", return_value="Test diagnosis")

        result = runner.invoke(app, ["diagnose", "service", "test-service"])

        assert result.exit_code == 0
        assert "test-service" in result.stdout

    def test_explain_command(self, tmp_path, monkeypatch, mocker):
        """Test explain command."""
        from pathlib import Path

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        # Mock AI
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

        # Mock kubectl to raise error
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

        # Mock kubectl
        mocker.patch("kfix.kubectl.Kubectl.check_cluster_access", return_value=True)
        mocker.patch(
            "kfix.kubectl.Kubectl.gather_pod_diagnostics",
            return_value={"describe": "test"},
        )

        # Mock AI to raise error
        mocker.patch(
            "kfix.ai.Diagnostician.diagnose_pod",
            side_effect=Exception("API Error"),
        )

        result = runner.invoke(app, ["diagnose", "pod", "test-pod"])

        assert result.exit_code == 1
        assert "Failed to get AI diagnosis" in result.stdout
