"""AI-powered diagnosis using Claude."""

from typing import Dict, Iterator, Optional, Tuple, NamedTuple, Union

from anthropic import Anthropic, APIError, RateLimitError, APITimeoutError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging

logger = logging.getLogger(__name__)


class TokenUsage(NamedTuple):
    """Token usage information from API response.

    Attributes:
        input_tokens: Number of input tokens.
        output_tokens: Number of output tokens.
        model: Model name used.
    """

    input_tokens: int
    output_tokens: int
    model: str

    def total_tokens(self) -> int:
        """Get total token count."""
        return self.input_tokens + self.output_tokens

    def estimated_cost(self) -> float:
        """Calculate estimated cost in USD.

        Returns:
            Estimated cost in dollars.
        """
        # Pricing per million tokens (as of Jan 2025)
        pricing = {
            "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
            "claude-opus-4-6": {"input": 15.0, "output": 75.0},
            "claude-haiku-4-5-20251001": {"input": 0.25, "output": 1.25},
        }

        if self.model not in pricing:
            return 0.0

        model_pricing = pricing[self.model]
        input_cost = (self.input_tokens / 1_000_000) * model_pricing["input"]
        output_cost = (self.output_tokens / 1_000_000) * model_pricing["output"]

        return input_cost + output_cost


class Diagnostician:
    """AI diagnostician using Claude for Kubernetes troubleshooting.

    This class uses Anthropic's Claude API to analyze Kubernetes
    diagnostics and provide actionable insights and fixes.

    Attributes:
        client: Anthropic API client.
        model: Claude model to use for diagnosis.
    """

    # Model ID mappings
    MODELS = {
        "sonnet": "claude-sonnet-4-5-20250929",
        "opus": "claude-opus-4-6",
        "haiku": "claude-haiku-4-5-20251001",
    }

    # Prompt templates for different resource types
    _PROMPT_TEMPLATES = {
        "pod": """You are a Kubernetes expert. Analyze the following diagnostics for pod '{resource_name}' and provide a concise diagnosis.

POD DESCRIPTION:
{describe}

POD LOGS (last 100 lines):
{logs}

EVENTS:
{events}

Provide:
1. A clear diagnosis of the issue (2-3 sentences)
2. The root cause
3. A specific fix with copy-paste ready kubectl commands
4. A link to relevant Kubernetes documentation

Keep your response under 300 words. Be specific and actionable.""",
        "node": """You are a Kubernetes expert. Analyze the following diagnostics for node '{resource_name}' and provide a concise diagnosis.

NODE DESCRIPTION:
{describe}

EVENTS:
{events}

Provide:
1. A clear diagnosis of the issue (2-3 sentences)
2. The root cause
3. A specific fix with copy-paste ready kubectl commands or system commands
4. A link to relevant Kubernetes documentation

Keep your response under 300 words. Be specific and actionable.""",
        "deployment": """You are a Kubernetes expert. Analyze the following diagnostics for deployment '{resource_name}' and provide a concise diagnosis.

DEPLOYMENT DESCRIPTION:
{describe}

EVENTS:
{events}

Provide:
1. A clear diagnosis of the issue (2-3 sentences)
2. The root cause
3. A specific fix with copy-paste ready kubectl commands
4. A link to relevant Kubernetes documentation

Keep your response under 300 words. Be specific and actionable.""",
        "service": """You are a Kubernetes expert. Analyze the following diagnostics for service '{resource_name}' and provide a concise diagnosis.

SERVICE DESCRIPTION:
{describe}

SERVICE ENDPOINTS:
{endpoints}

Provide:
1. A clear diagnosis of the issue (2-3 sentences)
2. The root cause (focus on connectivity, selectors, ports)
3. A specific fix with copy-paste ready kubectl commands
4. A link to relevant Kubernetes documentation

Keep your response under 300 words. Be specific and actionable.""",
    }

    def __init__(self, api_key: str, model: str = "sonnet") -> None:
        """Initialize the diagnostician with an API key and model.

        Args:
            api_key: Anthropic API key for Claude access.
            model: Model to use (sonnet, opus, haiku). Defaults to sonnet.

        Raises:
            ValueError: If model is not recognized.

        Example:
            >>> diagnostician = Diagnostician("sk-ant-api03-...", model="opus")
        """
        self.client = Anthropic(api_key=api_key)

        if model not in self.MODELS:
            raise ValueError(
                f"Unknown model: {model}. " f"Available models: {', '.join(self.MODELS.keys())}"
            )

        self.model = self.MODELS[model]
        self.model_name = model
        self.last_token_usage: Optional[TokenUsage] = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _make_api_call(self, prompt: str, stream: bool = False) -> Union[str, Iterator[str]]:
        """Make API call to Claude with retry logic.

        Args:
            prompt: The prompt to send to Claude.
            stream: If True, return streaming response.

        Returns:
            API response text or streaming iterator.

        Raises:
            RateLimitError: If rate limit is exceeded after retries.
            APITimeoutError: If API timeout occurs after retries.
            APIError: If API call fails after retries.
        """
        if stream:
            return self._stream_response(prompt)
        else:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            # Track token usage
            self.last_token_usage = TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                model=self.model,
            )

            return response.content[0].text

    def _diagnose(
        self,
        resource_type: str,
        resource_name: str,
        diagnostics: Dict[str, str],
        stream: bool = False,
    ) -> Union[str, Iterator[str]]:
        """Generic diagnosis method for any Kubernetes resource type.

        Args:
            resource_type: Type of resource (pod, node, deployment, service).
            resource_name: Name of the resource being diagnosed.
            diagnostics: Dictionary containing diagnostic data.
            stream: If True, return an iterator that yields text chunks as they arrive.

        Returns:
            If stream=False: Markdown-formatted diagnosis string.
            If stream=True: Iterator yielding text chunks as they arrive.

        Raises:
            ValueError: If resource_type is not supported.
            RateLimitError: If rate limit is exceeded after retries.
            APITimeoutError: If API timeout occurs after retries.
            APIError: If API call fails after retries.
        """
        if resource_type not in self._PROMPT_TEMPLATES:
            raise ValueError(
                f"Unsupported resource type: {resource_type}. "
                f"Supported types: {', '.join(self._PROMPT_TEMPLATES.keys())}"
            )

        # Format the prompt template with diagnostics data
        template = self._PROMPT_TEMPLATES[resource_type]
        prompt = template.format(resource_name=resource_name, **diagnostics)

        # Make API call with retry logic
        try:
            return self._make_api_call(prompt, stream=stream)
        except RateLimitError:
            raise Exception(
                "Rate limit exceeded. Please wait a moment and try again. "
                "Consider using a different model with --model flag."
            )
        except APITimeoutError:
            raise Exception(
                "API request timed out after multiple attempts. "
                "Please check your internet connection and try again."
            )
        except APIError as e:
            raise Exception(f"API error: {e}. Please try again later.")

    def _stream_response(self, prompt: str) -> Iterator[str]:
        """Stream response from Claude API.

        Args:
            prompt: The prompt to send to Claude.

        Yields:
            Text chunks as they arrive from the API.
        """
        with self.client.messages.stream(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield text

            # Get final message to track token usage
            final_message = stream.get_final_message()
            self.last_token_usage = TokenUsage(
                input_tokens=final_message.usage.input_tokens,
                output_tokens=final_message.usage.output_tokens,
                model=self.model,
            )

    def diagnose_pod(
        self, pod_name: str, diagnostics: Dict[str, str], stream: bool = False
    ) -> Union[str, Iterator[str]]:
        """Diagnose pod issues using AI analysis.

        Analyzes pod diagnostics including description, logs, events,
        and YAML configuration to identify issues and provide fixes.

        Args:
            pod_name: Name of the pod being diagnosed.
            diagnostics: Dictionary containing diagnostic data with keys:
                'describe', 'logs', 'events', 'yaml'.
            stream: If True, return an iterator that yields text chunks as they arrive.

        Returns:
            If stream=False: Markdown-formatted diagnosis string.
            If stream=True: Iterator yielding text chunks as they arrive.

        Raises:
            Exception: If the AI API call fails.

        Example:
            >>> diagnostician = Diagnostician(api_key)
            >>> diagnostics = kubectl.gather_pod_diagnostics("my-app")
            >>> diagnosis = diagnostician.diagnose_pod("my-app", diagnostics)
        """
        # Add 'N/A' defaults for missing keys
        diagnostics_with_defaults = {
            key: diagnostics.get(key, "N/A") for key in ["describe", "logs", "events"]
        }
        return self._diagnose("pod", pod_name, diagnostics_with_defaults, stream=stream)

    def diagnose_node(
        self, node_name: str, diagnostics: Dict[str, str], stream: bool = False
    ) -> Union[str, Iterator[str]]:
        """Diagnose node issues using AI analysis.

        Analyzes node diagnostics including description and events
        to identify health issues, resource pressure, and configuration problems.

        Args:
            node_name: Name of the node being diagnosed.
            diagnostics: Dictionary containing diagnostic data with keys:
                'describe', 'events'.
            stream: If True, return an iterator that yields text chunks as they arrive.

        Returns:
            If stream=False: Markdown-formatted diagnosis string.
            If stream=True: Iterator yielding text chunks as they arrive.

        Raises:
            Exception: If the AI API call fails.
        """
        diagnostics_with_defaults = {
            key: diagnostics.get(key, "N/A") for key in ["describe", "events"]
        }
        return self._diagnose("node", node_name, diagnostics_with_defaults, stream=stream)

    def diagnose_deployment(
        self, deployment_name: str, diagnostics: Dict[str, str], stream: bool = False
    ) -> Union[str, Iterator[str]]:
        """Diagnose deployment issues using AI analysis.

        Analyzes deployment diagnostics including description and events
        to identify rollout issues, replica problems, and configuration errors.

        Args:
            deployment_name: Name of the deployment being diagnosed.
            diagnostics: Dictionary containing diagnostic data with keys:
                'describe', 'events'.
            stream: If True, return an iterator that yields text chunks as they arrive.

        Returns:
            If stream=False: Markdown-formatted diagnosis string.
            If stream=True: Iterator yielding text chunks as they arrive.

        Raises:
            Exception: If the AI API call fails.
        """
        diagnostics_with_defaults = {
            key: diagnostics.get(key, "N/A") for key in ["describe", "events"]
        }
        return self._diagnose("deployment", deployment_name, diagnostics_with_defaults, stream=stream)

    def diagnose_service(
        self, service_name: str, diagnostics: Dict[str, str], stream: bool = False
    ) -> Union[str, Iterator[str]]:
        """Diagnose service issues using AI analysis.

        Analyzes service diagnostics including description and endpoints
        to identify connectivity issues, selector problems, and port misconfigurations.

        Args:
            service_name: Name of the service being diagnosed.
            diagnostics: Dictionary containing diagnostic data with keys:
                'describe', 'endpoints'.
            stream: If True, return an iterator that yields text chunks as they arrive.

        Returns:
            If stream=False: Markdown-formatted diagnosis string.
            If stream=True: Iterator yielding text chunks as they arrive.

        Raises:
            Exception: If the AI API call fails.
        """
        diagnostics_with_defaults = {
            key: diagnostics.get(key, "N/A") for key in ["describe", "endpoints"]
        }
        return self._diagnose("service", service_name, diagnostics_with_defaults, stream=stream)

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

        try:
            return self._make_api_call(prompt, stream=False)
        except RateLimitError:
            raise Exception(
                "Rate limit exceeded. Please wait a moment and try again. "
                "Consider using a different model with --model flag."
            )
        except APITimeoutError:
            raise Exception(
                "API request timed out after multiple attempts. "
                "Please check your internet connection and try again."
            )
        except APIError as e:
            raise Exception(f"API error: {e}. Please try again later.")

    def get_token_usage(self) -> Optional[TokenUsage]:
        """Get token usage from the last API call.

        Returns:
            TokenUsage object or None if no API call has been made yet.
        """
        return self.last_token_usage
