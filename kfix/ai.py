"""AI-powered diagnosis using Claude."""

from anthropic import Anthropic
from typing import Dict


class Diagnostician:
    """AI diagnostician using Claude."""

    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)

    def diagnose_pod(self, pod_name: str, diagnostics: Dict[str, str]) -> str:
        """Diagnose pod issues using AI."""

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
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return response.content[0].text

    def diagnose_node(self, node_name: str, diagnostics: Dict[str, str]) -> str:
        """Diagnose node issues using AI."""

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
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return response.content[0].text

    def explain_error(self, error: str) -> str:
        """Explain a Kubernetes error in plain English."""

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
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return response.content[0].text
