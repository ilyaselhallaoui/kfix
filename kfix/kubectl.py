"""Kubectl wrapper for gathering Kubernetes diagnostics."""

import json as _json
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple


class KubectlError(Exception):
    """Raised when kubectl command fails."""

    pass


class Kubectl:
    """Wrapper for kubectl commands to interact with Kubernetes clusters.

    This class provides methods to gather diagnostic information from
    Kubernetes resources using kubectl commands.

    Attributes:
        cache_ttl: Time-to-live for cache entries in seconds (default: 300 = 5 minutes).
        use_cache: Whether to use caching (default: True).
    """

    def __init__(
        self, cache_ttl: int = 300, use_cache: bool = True, context: Optional[str] = None
    ) -> None:
        """Initialize Kubectl wrapper.

        Args:
            cache_ttl: Time-to-live for cache entries in seconds.
            use_cache: Whether to enable caching.
            context: Kubernetes context to use. If None, uses current context.
        """
        self.cache_ttl = cache_ttl
        self.use_cache = use_cache
        self.context = context
        self._cache: Dict[str, Tuple[float, str, str, int]] = {}

    def _cache_key(self, args: List[str]) -> str:
        """Generate cache key from kubectl arguments.

        Args:
            args: kubectl command arguments.

        Returns:
            Cache key string.
        """
        return "|".join(args)

    def _get_cached(self, args: List[str]) -> Optional[Tuple[str, str, int]]:
        """Get cached result if available and not expired.

        Args:
            args: kubectl command arguments.

        Returns:
            Cached result tuple (stdout, stderr, returncode) or None if not cached/expired.
        """
        if not self.use_cache:
            return None

        key = self._cache_key(args)
        if key in self._cache:
            timestamp, stdout, stderr, returncode = self._cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return stdout, stderr, returncode

        return None

    def _set_cached(self, args: List[str], result: Tuple[str, str, int]) -> None:
        """Store result in cache.

        Args:
            args: kubectl command arguments.
            result: Result tuple (stdout, stderr, returncode) to cache.
        """
        if not self.use_cache:
            return

        key = self._cache_key(args)
        stdout, stderr, returncode = result
        self._cache[key] = (time.time(), stdout, stderr, returncode)

    def clear_cache(self) -> None:
        """Clear all cached results."""
        self._cache.clear()

    def _run(self, args: List[str], check: bool = True) -> Tuple[str, str, int]:
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
        # Prepend --context if set
        if self.context:
            args = ["--context", self.context] + args

        # Check cache first
        cached_result = self._get_cached(args)
        if cached_result is not None:
            return cached_result

        # Execute command
        try:
            result = subprocess.run(["kubectl"] + args, capture_output=True, text=True, timeout=30)
            output = (result.stdout, result.stderr, result.returncode)

            # Cache the result
            self._set_cached(args, output)

            if check and result.returncode != 0:
                raise KubectlError(f"kubectl failed: {result.stderr}")
            return output
        except subprocess.TimeoutExpired as e:
            raise KubectlError("kubectl command timed out") from e
        except FileNotFoundError as e:
            raise KubectlError("kubectl not found. Please install kubectl.") from e

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
            _, _, code = self._run(["cluster-info"], check=False)
            return code == 0
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

    def scan_namespace(self, namespace: str = "default") -> List[Dict[str, str]]:
        """Scan a namespace for unhealthy resources.

        Args:
            namespace: Kubernetes namespace to scan.

        Returns:
            List of dicts with keys: 'kind', 'name', 'namespace', 'status', 'reason'.
        """
        unhealthy: List[Dict[str, str]] = []

        # Scan pods
        try:
            stdout, _, _ = self._run(
                ["get", "pods", "-n", namespace, "-o", "json"], check=False
            )
            if stdout.strip():
                data = _json.loads(stdout)
                for item in data.get("items", []):
                    phase = item.get("status", {}).get("phase", "Unknown")
                    if phase not in ("Running", "Succeeded"):
                        name = item.get("metadata", {}).get("name", "unknown")
                        reason = self._pod_failure_reason(item)
                        unhealthy.append({
                            "kind": "pod",
                            "name": name,
                            "namespace": namespace,
                            "status": phase,
                            "reason": reason,
                        })
        except (KubectlError, _json.JSONDecodeError):
            pass

        # Scan deployments
        try:
            stdout, _, _ = self._run(
                ["get", "deployments", "-n", namespace, "-o", "json"], check=False
            )
            if stdout.strip():
                data = _json.loads(stdout)
                for item in data.get("items", []):
                    status = item.get("status", {})
                    desired = item.get("spec", {}).get("replicas", 0)
                    available = status.get("availableReplicas", 0) or 0
                    if available < desired:
                        name = item.get("metadata", {}).get("name", "unknown")
                        unhealthy.append({
                            "kind": "deployment",
                            "name": name,
                            "namespace": namespace,
                            "status": f"{available}/{desired} available",
                            "reason": "Insufficient replicas",
                        })
        except (KubectlError, _json.JSONDecodeError):
            pass

        # Scan services
        unhealthy.extend(self._scan_services(namespace))

        # Scan nodes once (cluster-scoped).
        unhealthy.extend(self._scan_nodes())

        return unhealthy

    def scan_all_namespaces(self) -> List[Dict[str, str]]:
        """Scan all namespaces for unhealthy resources.

        Returns:
            List of dicts with keys: 'kind', 'name', 'namespace', 'status', 'reason'.
        """
        unhealthy: List[Dict[str, str]] = []

        # Get all namespaces
        try:
            stdout, _, _ = self._run(["get", "namespaces", "-o", "json"], check=False)
            if stdout.strip():
                data = _json.loads(stdout)
                namespaces = [
                    item.get("metadata", {}).get("name", "")
                    for item in data.get("items", [])
                ]
        except (KubectlError, _json.JSONDecodeError):
            namespaces = ["default"]

        for ns in namespaces:
            # Scan pods and deployments per namespace (skip nodes, handled separately)
            try:
                stdout, _, _ = self._run(
                    ["get", "pods", "-n", ns, "-o", "json"], check=False
                )
                if stdout.strip():
                    data = _json.loads(stdout)
                    for item in data.get("items", []):
                        phase = item.get("status", {}).get("phase", "Unknown")
                        if phase not in ("Running", "Succeeded"):
                            name = item.get("metadata", {}).get("name", "unknown")
                            reason = self._pod_failure_reason(item)
                            unhealthy.append({
                                "kind": "pod",
                                "name": name,
                                "namespace": ns,
                                "status": phase,
                                "reason": reason,
                            })
            except (KubectlError, _json.JSONDecodeError):
                pass

            unhealthy.extend(self._scan_services(ns))

            try:
                stdout, _, _ = self._run(
                    ["get", "deployments", "-n", ns, "-o", "json"], check=False
                )
                if stdout.strip():
                    data = _json.loads(stdout)
                    for item in data.get("items", []):
                        status = item.get("status", {})
                        desired = item.get("spec", {}).get("replicas", 0)
                        available = status.get("availableReplicas", 0) or 0
                        if available < desired:
                            name = item.get("metadata", {}).get("name", "unknown")
                            unhealthy.append({
                                "kind": "deployment",
                                "name": name,
                                "namespace": ns,
                                "status": f"{available}/{desired} available",
                                "reason": "Insufficient replicas",
                            })
            except (KubectlError, _json.JSONDecodeError):
                pass

        # Scan nodes once (cluster-scoped)
        unhealthy.extend(self._scan_nodes())

        return unhealthy

    def _scan_services(self, namespace: str) -> List[Dict[str, str]]:
        """Scan services for missing endpoints.

        Args:
            namespace: Kubernetes namespace to scan.

        Returns:
            List of unhealthy service dicts.
        """
        unhealthy: List[Dict[str, str]] = []

        try:
            services_stdout, _, _ = self._run(
                ["get", "services", "-n", namespace, "-o", "json"], check=False
            )
            endpoints_stdout, _, _ = self._run(
                ["get", "endpoints", "-n", namespace, "-o", "json"], check=False
            )

            if not services_stdout.strip():
                return unhealthy

            services_data = _json.loads(services_stdout)
            endpoints_data = _json.loads(endpoints_stdout) if endpoints_stdout.strip() else {"items": []}

            endpoints_by_name: Dict[str, Dict[str, Any]] = {}
            for endpoint in endpoints_data.get("items", []):
                endpoint_name = endpoint.get("metadata", {}).get("name")
                if isinstance(endpoint_name, str) and endpoint_name:
                    endpoints_by_name[endpoint_name] = endpoint

            for service in services_data.get("items", []):
                metadata = service.get("metadata", {})
                spec = service.get("spec", {})

                name = metadata.get("name", "unknown")
                if not isinstance(name, str):
                    name = "unknown"

                service_type = spec.get("type", "ClusterIP")
                if service_type == "ExternalName":
                    continue

                selector = spec.get("selector") or {}
                if not selector:
                    continue

                endpoint_obj = endpoints_by_name.get(name, {})
                subsets = endpoint_obj.get("subsets") or []

                has_ready_addresses = False
                for subset in subsets:
                    addresses = subset.get("addresses") or []
                    if addresses:
                        has_ready_addresses = True
                        break

                if not has_ready_addresses:
                    unhealthy.append(
                        {
                            "kind": "service",
                            "name": name,
                            "namespace": namespace,
                            "status": "NoReadyEndpoints",
                            "reason": "No ready endpoints",
                        }
                    )
        except (KubectlError, _json.JSONDecodeError):
            pass

        return unhealthy

    def _scan_nodes(self) -> List[Dict[str, str]]:
        """Scan nodes for unhealthy status.

        Returns:
            List of unhealthy node dicts.
        """
        unhealthy: List[Dict[str, str]] = []
        try:
            stdout, _, _ = self._run(["get", "nodes", "-o", "json"], check=False)
            if stdout.strip():
                data = _json.loads(stdout)
                for item in data.get("items", []):
                    name = item.get("metadata", {}).get("name", "unknown")
                    conditions = item.get("status", {}).get("conditions", [])
                    ready = False
                    reason = "Unknown"
                    for cond in conditions:
                        if cond.get("type") == "Ready":
                            ready = cond.get("status") == "True"
                            reason = cond.get("reason", "Unknown")
                    if not ready:
                        unhealthy.append({
                            "kind": "node",
                            "name": name,
                            "namespace": "",
                            "status": "NotReady",
                            "reason": reason,
                        })
        except (KubectlError, _json.JSONDecodeError):
            pass
        return unhealthy

    @staticmethod
    def _pod_failure_reason(pod: Dict[str, Any]) -> str:
        """Extract a human-readable failure reason from a pod's status.

        Args:
            pod: Pod JSON object.

        Returns:
            Failure reason string.
        """
        status = pod.get("status", {})
        if not isinstance(status, dict):
            return "Unknown"

        container_statuses = status.get("containerStatuses", [])
        if not isinstance(container_statuses, list):
            container_statuses = []

        for cs in container_statuses:
            if not isinstance(cs, dict):
                continue
            state = cs.get("state", {})
            if not isinstance(state, dict):
                continue

            waiting = state.get("waiting", {})
            if waiting:
                reason = waiting.get("reason", "Unknown")
                return reason if isinstance(reason, str) else "Unknown"
            terminated = state.get("terminated", {})
            if terminated:
                reason = terminated.get("reason", "Unknown")
                return reason if isinstance(reason, str) else "Unknown"

        reason = status.get("reason", "Unknown")
        return reason if isinstance(reason, str) else "Unknown"
