"""Kubectl wrapper for gathering Kubernetes diagnostics."""

import subprocess
import json
from typing import Dict, Any, Optional


class KubectlError(Exception):
    """Raised when kubectl command fails."""
    pass


class Kubectl:
    """Wrapper for kubectl commands."""

    def _run(self, args: list[str], check: bool = True) -> tuple[str, str, int]:
        """Run kubectl command and return stdout, stderr, returncode."""
        try:
            result = subprocess.run(
                ["kubectl"] + args,
                capture_output=True,
                text=True,
                timeout=30
            )
            if check and result.returncode != 0:
                raise KubectlError(f"kubectl failed: {result.stderr}")
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            raise KubectlError("kubectl command timed out")
        except FileNotFoundError:
            raise KubectlError("kubectl not found. Please install kubectl.")

    def check_cluster_access(self) -> bool:
        """Check if we can access the cluster."""
        try:
            self._run(["cluster-info"], check=False)
            return True
        except KubectlError:
            return False

    def get_pod_logs(self, pod_name: str, namespace: str = "default", tail: int = 100) -> str:
        """Get logs for a pod."""
        try:
            stdout, _, _ = self._run([
                "logs", pod_name,
                "-n", namespace,
                "--tail", str(tail)
            ], check=False)
            return stdout
        except KubectlError:
            return ""

    def describe_pod(self, pod_name: str, namespace: str = "default") -> str:
        """Get detailed description of a pod."""
        stdout, _, _ = self._run(["describe", "pod", pod_name, "-n", namespace])
        return stdout

    def get_pod_events(self, pod_name: str, namespace: str = "default") -> str:
        """Get events related to a pod."""
        try:
            stdout, _, _ = self._run([
                "get", "events",
                "-n", namespace,
                "--field-selector", f"involvedObject.name={pod_name}",
                "--sort-by", ".lastTimestamp"
            ], check=False)
            return stdout
        except KubectlError:
            return ""

    def get_pod_yaml(self, pod_name: str, namespace: str = "default") -> str:
        """Get pod YAML."""
        try:
            stdout, _, _ = self._run([
                "get", "pod", pod_name,
                "-n", namespace,
                "-o", "yaml"
            ])
            return stdout
        except KubectlError:
            return ""

    def describe_node(self, node_name: str) -> str:
        """Get detailed description of a node."""
        stdout, _, _ = self._run(["describe", "node", node_name])
        return stdout

    def get_node_events(self, node_name: str) -> str:
        """Get events related to a node."""
        try:
            stdout, _, _ = self._run([
                "get", "events",
                "--all-namespaces",
                "--field-selector", f"involvedObject.name={node_name}",
                "--sort-by", ".lastTimestamp"
            ], check=False)
            return stdout
        except KubectlError:
            return ""

    def gather_pod_diagnostics(self, pod_name: str, namespace: str = "default") -> Dict[str, str]:
        """Gather all diagnostic information for a pod."""
        return {
            "describe": self.describe_pod(pod_name, namespace),
            "logs": self.get_pod_logs(pod_name, namespace),
            "events": self.get_pod_events(pod_name, namespace),
            "yaml": self.get_pod_yaml(pod_name, namespace),
        }

    def gather_node_diagnostics(self, node_name: str) -> Dict[str, str]:
        """Gather all diagnostic information for a node."""
        return {
            "describe": self.describe_node(node_name),
            "events": self.get_node_events(node_name),
        }
