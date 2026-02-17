"""AI-powered diagnosis using Claude."""

from typing import Dict

from anthropic import Anthropic


class Diagnostician:
    """AI diagnostician using Claude for Kubernetes troubleshooting.

    This class uses Anthropic's Claude API to analyze Kubernetes
    diagnostics and provide actionable insights and fixes.

    Attributes:
        client: Anthropic API client.
    """

    def __init__(self, api_key: str) -> None:
        """Initialize the diagnostician with an API key.

        Args:
            api_key: Anthropic API key for Claude access.

        Example:
            >>> diagnostician = Diagnostician("sk-ant-api03-...")
        """
        self.client = Anthropic(api_key=api_key)

    def diagnose_pod(self, pod_name: str, diagnostics: Dict[str, str]) -> str:
        """Diagnose pod issues using AI analysis.

        Analyzes pod diagnostics including description, logs, events,
        and YAML configuration to identify issues and provide fixes.

        Args:
            pod_name: Name of the pod being diagnosed.
            diagnostics: Dictionary containing diagnostic data with keys:
                'describe', 'logs', 'events', 'yaml'.

        Returns:
            Markdown-formatted diagnosis with problem description,
            root cause, fix commands, and documentation links.

        Raises:
            Exception: If the AI API call fails.

        Example:
            >>> diagnostician = Diagnostician(api_key)
            >>> diagnostics = kubectl.gather_pod_diagnostics("my-app")
            >>> diagnosis = diagnostician.diagnose_pod("my-app", diagnostics)
        """
        prompt = f"""You are a Kubernetes expert. Analyze the following diagnostics for pod '{pod_name}' and provide a concise diagnosis.

POD DESCRIPTION:
{diagnostics.get('describe', 'N/A')}

POD LOGS (last 100 lines):
{diagnostics.get('logs', 'N/A')}

EVENTS:
{diagnostics.get('events', 'N/A')}

Provide:
1. A clear diagnosis of the issue (2-3 sentences)
2. The root cause
3. A specific fix with copy-paste ready kubectl commands
4. A link to relevant Kubernetes documentation

Keep your response under 300 words. Be specific and actionable."""

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    def diagnose_node(self, node_name: str, diagnostics: Dict[str, str]) -> str:
        """Diagnose node issues using AI analysis.

        Analyzes node diagnostics including description and events
        to identify health issues, resource pressure, and configuration problems.

        Args:
            node_name: Name of the node being diagnosed.
            diagnostics: Dictionary containing diagnostic data with keys:
                'describe', 'events'.

        Returns:
            Markdown-formatted diagnosis with problem description,
            root cause, fix commands, and documentation links.

        Raises:
            Exception: If the AI API call fails.
        """
        prompt = f"""You are a Kubernetes expert. Analyze the following diagnostics for node '{node_name}' and provide a concise diagnosis.

NODE DESCRIPTION:
{diagnostics.get('describe', 'N/A')}

EVENTS:
{diagnostics.get('events', 'N/A')}

Provide:
1. A clear diagnosis of the issue (2-3 sentences)
2. The root cause
3. A specific fix with copy-paste ready kubectl commands or system commands
4. A link to relevant Kubernetes documentation

Keep your response under 300 words. Be specific and actionable."""

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    def diagnose_deployment(self, deployment_name: str, diagnostics: Dict[str, str]) -> str:
        """Diagnose deployment issues using AI analysis.

        Analyzes deployment diagnostics including description and events
        to identify rollout issues, replica problems, and configuration errors.

        Args:
            deployment_name: Name of the deployment being diagnosed.
            diagnostics: Dictionary containing diagnostic data with keys:
                'describe', 'events'.

        Returns:
            Markdown-formatted diagnosis with problem description,
            root cause, fix commands, and documentation links.

        Raises:
            Exception: If the AI API call fails.
        """
        prompt = f"""You are a Kubernetes expert. Analyze the following diagnostics for deployment '{deployment_name}' and provide a concise diagnosis.

DEPLOYMENT DESCRIPTION:
{diagnostics.get('describe', 'N/A')}

EVENTS:
{diagnostics.get('events', 'N/A')}

Provide:
1. A clear diagnosis of the issue (2-3 sentences)
2. The root cause
3. A specific fix with copy-paste ready kubectl commands
4. A link to relevant Kubernetes documentation

Keep your response under 300 words. Be specific and actionable."""

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    def diagnose_service(self, service_name: str, diagnostics: Dict[str, str]) -> str:
        """Diagnose service issues using AI analysis.

        Analyzes service diagnostics including description and endpoints
        to identify connectivity issues, selector problems, and port misconfigurations.

        Args:
            service_name: Name of the service being diagnosed.
            diagnostics: Dictionary containing diagnostic data with keys:
                'describe', 'endpoints'.

        Returns:
            Markdown-formatted diagnosis with problem description,
            root cause, fix commands, and documentation links.

        Raises:
            Exception: If the AI API call fails.
        """
        prompt = f"""You are a Kubernetes expert. Analyze the following diagnostics for service '{service_name}' and provide a concise diagnosis.

SERVICE DESCRIPTION:
{diagnostics.get('describe', 'N/A')}

SERVICE ENDPOINTS:
{diagnostics.get('endpoints', 'N/A')}

Provide:
1. A clear diagnosis of the issue (2-3 sentences)
2. The root cause (focus on connectivity, selectors, ports)
3. A specific fix with copy-paste ready kubectl commands
4. A link to relevant Kubernetes documentation

Keep your response under 300 words. Be specific and actionable."""

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    def explain_error(self, error: str) -> str:
        """Explain a Kubernetes error in plain English.

        Provides a detailed explanation of any Kubernetes error message,
        including common causes and how to fix it.

        Args:
            error: The Kubernetes error message to explain.

        Returns:
            Markdown-formatted explanation with meaning, common causes,
            fix commands, and documentation links.

        Raises:
            Exception: If the AI API call fails.

        Example:
            >>> diagnostician = Diagnostician(api_key)
            >>> explanation = diagnostician.explain_error("CrashLoopBackOff")
        """
        prompt = f"""You are a Kubernetes expert. Explain this Kubernetes error in plain English:

"{error}"

Provide:
1. What this error means in simple terms
2. Common causes
3. How to fix it (with specific kubectl commands if applicable)
4. A link to relevant Kubernetes documentation

Keep your response under 300 words. Be clear and actionable."""

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text
