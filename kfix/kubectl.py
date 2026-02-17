"""Kubectl wrapper for gathering Kubernetes diagnostics."""

import subprocess
from typing import Dict, Tuple


class KubectlError(Exception):
    """Raised when kubectl command fails."""

    pass


class Kubectl:
    """Wrapper for kubectl commands to interact with Kubernetes clusters.

    This class provides methods to gather diagnostic information from
    Kubernetes resources using kubectl commands.
    """

    def _run(self, args: list[str], check: bool = True) -> Tuple[str, str, int]:
        """Run a kubectl command and return its output.

        Args:
            args: List of arguments to pass to kubectl.
            check: If True, raise KubectlError on non-zero exit code.

        Returns:
            A tuple of (stdout, stderr, returncode).

        Raises:
            KubectlError: If kubectl command fails or times out.

        Example:
            >>> kubectl = Kubectl()
            >>> stdout, stderr, code = kubectl._run(["get", "pods"])
        """
        try:
            result = subprocess.run(["kubectl"] + args, capture_output=True, text=True, timeout=30)
            if check and result.returncode != 0:
                raise KubectlError(f"kubectl failed: {result.stderr}")
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            raise KubectlError("kubectl command timed out")
        except FileNotFoundError:
            raise KubectlError("kubectl not found. Please install kubectl.")

    def check_cluster_access(self) -> bool:
        """Check if we can access the Kubernetes cluster.

        Returns:
            True if cluster is accessible, False otherwise.

        Example:
            >>> kubectl = Kubectl()
            >>> if kubectl.check_cluster_access():
            ...     print("Cluster is accessible")
        """
        try:
            self._run(["cluster-info"], check=False)
            return True
        except KubectlError:
            return False

    def get_pod_logs(self, pod_name: str, namespace: str = "default", tail: int = 100) -> str:
        """Get logs for a pod.

        Args:
            pod_name: Name of the pod.
            namespace: Kubernetes namespace. Defaults to "default".
            tail: Number of lines to retrieve from the end. Defaults to 100.

        Returns:
            Pod logs as a string, or empty string if logs unavailable.

        Example:
            >>> kubectl = Kubectl()
            >>> logs = kubectl.get_pod_logs("my-app", namespace="production")
        """
        try:
            stdout, _, _ = self._run(
                ["logs", pod_name, "-n", namespace, "--tail", str(tail)], check=False
            )
            return stdout
        except KubectlError:
            return ""

    def describe_pod(self, pod_name: str, namespace: str = "default") -> str:
        """Get detailed description of a pod.

        Args:
            pod_name: Name of the pod.
            namespace: Kubernetes namespace. Defaults to "default".

        Returns:
            Detailed pod description as a string.

        Raises:
            KubectlError: If the pod doesn't exist or kubectl fails.
        """
        stdout, _, _ = self._run(["describe", "pod", pod_name, "-n", namespace])
        return stdout

    def get_pod_events(self, pod_name: str, namespace: str = "default") -> str:
        """Get events related to a pod.

        Args:
            pod_name: Name of the pod.
            namespace: Kubernetes namespace. Defaults to "default".

        Returns:
            Events as a string, or empty string if no events found.

        Example:
            >>> kubectl = Kubectl()
            >>> events = kubectl.get_pod_events("failing-pod")
        """
        try:
            stdout, _, _ = self._run(
                [
                    "get",
                    "events",
                    "-n",
                    namespace,
                    "--field-selector",
                    f"involvedObject.name={pod_name}",
                    "--sort-by",
                    ".lastTimestamp",
                ],
                check=False,
            )
            return stdout
        except KubectlError:
            return ""

    def get_pod_yaml(self, pod_name: str, namespace: str = "default") -> str:
        """Get pod YAML configuration.

        Args:
            pod_name: Name of the pod.
            namespace: Kubernetes namespace. Defaults to "default".

        Returns:
            Pod YAML as a string, or empty string if unavailable.
        """
        try:
            stdout, _, _ = self._run(["get", "pod", pod_name, "-n", namespace, "-o", "yaml"])
            return stdout
        except KubectlError:
            return ""

    def describe_node(self, node_name: str) -> str:
        """Get detailed description of a node.

        Args:
            node_name: Name of the node.

        Returns:
            Detailed node description as a string.

        Raises:
            KubectlError: If the node doesn't exist or kubectl fails.
        """
        stdout, _, _ = self._run(["describe", "node", node_name])
        return stdout

    def get_node_events(self, node_name: str) -> str:
        """Get events related to a node.

        Args:
            node_name: Name of the node.

        Returns:
            Events as a string, or empty string if no events found.
        """
        try:
            stdout, _, _ = self._run(
                [
                    "get",
                    "events",
                    "--all-namespaces",
                    "--field-selector",
                    f"involvedObject.name={node_name}",
                    "--sort-by",
                    ".lastTimestamp",
                ],
                check=False,
            )
            return stdout
        except KubectlError:
            return ""

    def describe_deployment(self, deployment_name: str, namespace: str = "default") -> str:
        """Get detailed description of a deployment.

        Args:
            deployment_name: Name of the deployment.
            namespace: Kubernetes namespace. Defaults to "default".

        Returns:
            Detailed deployment description as a string.

        Raises:
            KubectlError: If the deployment doesn't exist or kubectl fails.
        """
        stdout, _, _ = self._run(["describe", "deployment", deployment_name, "-n", namespace])
        return stdout

    def get_deployment_events(self, deployment_name: str, namespace: str = "default") -> str:
        """Get events related to a deployment.

        Args:
            deployment_name: Name of the deployment.
            namespace: Kubernetes namespace. Defaults to "default".

        Returns:
            Events as a string, or empty string if no events found.
        """
        try:
            stdout, _, _ = self._run(
                [
                    "get",
                    "events",
                    "-n",
                    namespace,
                    "--field-selector",
                    f"involvedObject.name={deployment_name}",
                    "--sort-by",
                    ".lastTimestamp",
                ],
                check=False,
            )
            return stdout
        except KubectlError:
            return ""

    def describe_service(self, service_name: str, namespace: str = "default") -> str:
        """Get detailed description of a service.

        Args:
            service_name: Name of the service.
            namespace: Kubernetes namespace. Defaults to "default".

        Returns:
            Detailed service description as a string.

        Raises:
            KubectlError: If the service doesn't exist or kubectl fails.
        """
        stdout, _, _ = self._run(["describe", "service", service_name, "-n", namespace])
        return stdout

    def get_service_endpoints(self, service_name: str, namespace: str = "default") -> str:
        """Get endpoints for a service.

        Args:
            service_name: Name of the service.
            namespace: Kubernetes namespace. Defaults to "default".

        Returns:
            Service endpoints as a string.
        """
        try:
            stdout, _, _ = self._run(
                ["get", "endpoints", service_name, "-n", namespace, "-o", "wide"], check=False
            )
            return stdout
        except KubectlError:
            return ""

    def gather_pod_diagnostics(self, pod_name: str, namespace: str = "default") -> Dict[str, str]:
        """Gather all diagnostic information for a pod.

        Args:
            pod_name: Name of the pod.
            namespace: Kubernetes namespace. Defaults to "default".

        Returns:
            Dictionary containing pod diagnostics with keys:
            'describe', 'logs', 'events', 'yaml'.

        Raises:
            KubectlError: If critical kubectl commands fail.

        Example:
            >>> kubectl = Kubectl()
            >>> diagnostics = kubectl.gather_pod_diagnostics("my-app")
            >>> print(diagnostics['describe'])
        """
        return {
            "describe": self.describe_pod(pod_name, namespace),
            "logs": self.get_pod_logs(pod_name, namespace),
            "events": self.get_pod_events(pod_name, namespace),
            "yaml": self.get_pod_yaml(pod_name, namespace),
        }

    def gather_node_diagnostics(self, node_name: str) -> Dict[str, str]:
        """Gather all diagnostic information for a node.

        Args:
            node_name: Name of the node.

        Returns:
            Dictionary containing node diagnostics with keys:
            'describe', 'events'.

        Raises:
            KubectlError: If critical kubectl commands fail.
        """
        return {
            "describe": self.describe_node(node_name),
            "events": self.get_node_events(node_name),
        }

    def gather_deployment_diagnostics(
        self, deployment_name: str, namespace: str = "default"
    ) -> Dict[str, str]:
        """Gather all diagnostic information for a deployment.

        Args:
            deployment_name: Name of the deployment.
            namespace: Kubernetes namespace. Defaults to "default".

        Returns:
            Dictionary containing deployment diagnostics with keys:
            'describe', 'events'.

        Raises:
            KubectlError: If critical kubectl commands fail.
        """
        return {
            "describe": self.describe_deployment(deployment_name, namespace),
            "events": self.get_deployment_events(deployment_name, namespace),
        }

    def gather_service_diagnostics(
        self, service_name: str, namespace: str = "default"
    ) -> Dict[str, str]:
        """Gather all diagnostic information for a service.

        Args:
            service_name: Name of the service.
            namespace: Kubernetes namespace. Defaults to "default".

        Returns:
            Dictionary containing service diagnostics with keys:
            'describe', 'endpoints'.

        Raises:
            KubectlError: If critical kubectl commands fail.
        """
        return {
            "describe": self.describe_service(service_name, namespace),
            "endpoints": self.get_service_endpoints(service_name, namespace),
        }
