"""CLI interface for kfix."""

import json
import re
import subprocess
from datetime import datetime
from typing import Iterator, NoReturn, Dict, Any, List

import typer
from rich import print as rprint
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm

from kfix.ai import Diagnostician, TokenUsage
from kfix.config import Config
from kfix.kubectl import Kubectl, KubectlError

app = typer.Typer(help="AI-powered Kubernetes troubleshooter CLI")
config_app = typer.Typer(help="Configuration commands")
diagnose_app = typer.Typer(help="Diagnose Kubernetes resources")

app.add_typer(config_app, name="config")
app.add_typer(diagnose_app, name="diagnose")

console = Console()


def stream_diagnosis(
    stream: Iterator[str], title: str, resource_name: str
) -> str:
    """Stream and display AI diagnosis in real-time.

    Args:
        stream: Iterator yielding text chunks from AI.
        title: Title prefix for the panel (e.g., "pod", "node").
        resource_name: Name of the resource being diagnosed.

    Returns:
        Complete diagnosis text.
    """
    full_text = ""
    console.print()

    with Live(
        Panel(
            Markdown(""),
            title=f"[bold cyan]Diagnosis for {title} '{resource_name}'[/bold cyan]",
            border_style="cyan",
        ),
        console=console,
        refresh_per_second=10,
    ) as live:
        for chunk in stream:
            full_text += chunk
            live.update(
                Panel(
                    Markdown(full_text),
                    title=f"[bold cyan]Diagnosis for {title} '{resource_name}'[/bold cyan]",
                    border_style="cyan",
                )
            )

    return full_text


def extract_kubectl_commands(diagnosis: str) -> List[str]:
    """Extract kubectl commands from diagnosis text.

    Args:
        diagnosis: AI diagnosis text (markdown).

    Returns:
        List of kubectl commands found in code blocks.
    """
    commands = []

    # Match code blocks with kubectl commands
    # Pattern: ```bash\nkubectl ... \n``` or just kubectl ... in backticks
    code_block_pattern = r"```(?:bash|sh)?\s*(kubectl[^\n]+(?:\n(?!```).*)*)\s*```"
    inline_pattern = r"`(kubectl[^`]+)`"

    # Find code blocks
    for match in re.finditer(code_block_pattern, diagnosis, re.MULTILINE | re.DOTALL):
        block = match.group(1).strip()
        # Split by newlines and filter kubectl commands
        for line in block.split("\n"):
            line = line.strip()
            if line.startswith("kubectl") and not line.startswith("#"):
                commands.append(line)

    # Find inline commands if no code blocks found
    if not commands:
        for match in re.finditer(inline_pattern, diagnosis):
            cmd = match.group(1).strip()
            if cmd.startswith("kubectl"):
                commands.append(cmd)

    return commands


def apply_fixes(
    commands: List[str], auto_yes: bool = False, dry_run: bool = False
) -> None:
    """Apply kubectl fix commands with user confirmation.

    Args:
        commands: List of kubectl commands to execute.
        auto_yes: If True, skip confirmation prompts.
        dry_run: If True, only show commands without executing.
    """
    if not commands:
        console.print("[yellow]No kubectl commands found in diagnosis.[/yellow]")
        return

    console.print("\n[bold cyan]Found the following fix commands:[/bold cyan]")
    for i, cmd in enumerate(commands, 1):
        console.print(f"  {i}. [green]{cmd}[/green]")

    if dry_run:
        console.print("\n[yellow]Dry run mode - commands not executed.[/yellow]")
        return

    console.print()

    # Ask for global confirmation or individual
    if len(commands) > 1 and not auto_yes:
        apply_all = Confirm.ask("Apply all commands?", default=False)
    else:
        apply_all = auto_yes

    for i, cmd in enumerate(commands, 1):
        # Individual confirmation if not applying all
        if not apply_all and not auto_yes:
            if not Confirm.ask(f"Execute command {i}?", default=False):
                console.print(f"[yellow]Skipped command {i}[/yellow]")
                continue

        console.print(f"\n[cyan]Executing:[/cyan] {cmd}")

        try:
            # Execute the command
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=60
            )

            if result.returncode == 0:
                console.print(f"[green]✓ Command {i} executed successfully[/green]")
                if result.stdout.strip():
                    console.print(f"[dim]{result.stdout.strip()}[/dim]")
            else:
                console.print(f"[red]✗ Command {i} failed[/red]")
                if result.stderr.strip():
                    console.print(f"[red]{result.stderr.strip()}[/red]")

        except subprocess.TimeoutExpired:
            console.print(f"[red]✗ Command {i} timed out[/red]")
        except Exception as e:
            console.print(f"[red]✗ Command {i} failed: {e}[/red]")


def display_token_usage(token_usage: TokenUsage | None, show_cost: bool = True) -> None:
    """Display token usage information.

    Args:
        token_usage: Token usage information from the API.
        show_cost: Whether to show cost estimate.
    """
    if not token_usage:
        return

    console.print()
    usage_text = (
        f"[dim]Used {token_usage.total_tokens():,} tokens "
        f"({token_usage.input_tokens:,} in, {token_usage.output_tokens:,} out)[/dim]"
    )

    if show_cost:
        cost = token_usage.estimated_cost()
        usage_text += f" [dim]~ ${cost:.4f}[/dim]"

    console.print(usage_text)


def output_json(
    resource_type: str,
    resource_name: str,
    namespace: str | None,
    diagnosis: str,
    diagnostics: Dict[str, str] | None = None,
    token_usage: TokenUsage | None = None,
) -> None:
    """Output diagnosis as JSON.

    Args:
        resource_type: Type of resource (pod, node, deployment, service).
        resource_name: Name of the resource.
        namespace: Kubernetes namespace (None for cluster-scoped resources).
        diagnosis: AI diagnosis text.
        diagnostics: Optional raw diagnostic data.
        token_usage: Optional token usage information.
    """
    output: Dict[str, Any] = {
        "resource_type": resource_type,
        "resource_name": resource_name,
        "diagnosis": diagnosis,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    if namespace:
        output["namespace"] = namespace

    if diagnostics:
        output["raw_diagnostics"] = diagnostics

    if token_usage:
        output["token_usage"] = {
            "input_tokens": token_usage.input_tokens,
            "output_tokens": token_usage.output_tokens,
            "total_tokens": token_usage.total_tokens(),
            "estimated_cost_usd": round(token_usage.estimated_cost(), 6),
            "model": token_usage.model,
        }

    print(json.dumps(output, indent=2))


def get_diagnostician(model: str = "sonnet") -> Diagnostician:
    """Get or create diagnostician with API key and model.

    Args:
        model: Model to use (sonnet, opus, haiku).

    Returns:
        Initialized Diagnostician instance.

    Raises:
        typer.Exit: If no API key is configured or model is invalid.
    """
    config = Config()
    api_key = config.get_api_key()

    if not api_key:
        console.print("[red]Error: No API key configured.[/red]")
        console.print("\nSet your Anthropic API key with:")
        console.print("  [cyan]kfix config set api-key YOUR_API_KEY[/cyan]")
        raise typer.Exit(1)

    try:
        return Diagnostician(api_key, model=model)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Configuration key (e.g., api-key)"),
    value: str = typer.Argument(..., help="Configuration value"),
) -> None:
    """Set a configuration value.

    Args:
        key: Configuration key to set (currently only 'api-key' is supported).
        value: Value to set for the configuration key.

    Example:
        $ kfix config set api-key sk-ant-api03-...
    """
    config = Config()

    if key == "api-key":
        config.set_api_key(value)
        console.print(f"[green]✓[/green] API key saved to {config.config_file}")
    else:
        console.print(f"[red]Error: Unknown config key '{key}'[/red]")
        raise typer.Exit(1)


@diagnose_app.command("pod")
def diagnose_pod(
    pod_name: str = typer.Argument(..., help="Name of the pod to diagnose"),
    namespace: str = typer.Option("default", "-n", "--namespace", help="Kubernetes namespace"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable kubectl result caching"),
    output_format: str = typer.Option("rich", "-o", "--output", help="Output format (rich or json)"),
    model: str = typer.Option(
        "sonnet", "--model", help="Claude model to use (sonnet, opus, haiku)"
    ),
    auto_fix: bool = typer.Option(False, "--auto-fix", help="Automatically apply suggested fixes"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompts for fixes"),
) -> None:
    """Diagnose a pod issue.

    Gathers diagnostic information about a pod and uses AI to analyze
    the data and provide actionable insights.

    Args:
        pod_name: Name of the pod to diagnose.
        namespace: Kubernetes namespace where the pod is located.
        no_cache: If True, disable kubectl result caching.
        output_format: Output format (rich or json).
        model: Claude model to use.
        auto_fix: If True, automatically apply suggested fixes.
        yes: If True, skip confirmation prompts when applying fixes.

    Example:
        $ kfix diagnose pod my-app -n production
        $ kfix diagnose pod my-app --no-cache
        $ kfix diagnose pod my-app -o json
        $ kfix diagnose pod my-app --model opus
        $ kfix diagnose pod my-app --auto-fix
        $ kfix diagnose pod my-app --auto-fix --yes
    """
    # Check cluster access
    kubectl = Kubectl(use_cache=not no_cache)
    if not kubectl.check_cluster_access():
        console.print("[red]Error: Cannot access Kubernetes cluster.[/red]")
        console.print("\nMake sure:")
        console.print("  • kubectl is installed")
        console.print("  • You have a valid kubeconfig")
        console.print("  • The cluster is running")
        raise typer.Exit(1)

    # Get diagnostician
    diagnostician = get_diagnostician(model=model)

    # Gather diagnostics
    with console.status(f"[cyan]Gathering diagnostics for pod '{pod_name}'...[/cyan]"):
        try:
            diagnostics = kubectl.gather_pod_diagnostics(pod_name, namespace)
        except KubectlError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

    # Analyze with AI
    try:
        diagnosis: str
        if output_format == "json":
            # Non-streaming for JSON output
            diagnosis = diagnostician.diagnose_pod(pod_name, diagnostics, stream=False)
            token_usage = diagnostician.get_token_usage()
            output_json("pod", pod_name, namespace, diagnosis, diagnostics, token_usage)
        else:
            # Streaming for rich output
            console.print("[cyan]Analyzing with AI...[/cyan]")
            if auto_fix:
                # Need non-streaming for auto-fix to extract commands
                diagnosis = diagnostician.diagnose_pod(pod_name, diagnostics, stream=False)
                console.print()
                console.print(
                    Panel(
                        Markdown(diagnosis),
                        title=f"[bold cyan]Diagnosis for pod '{pod_name}'[/bold cyan]",
                        border_style="cyan",
                    )
                )
            else:
                # Stream output normally
                diagnosis_stream = diagnostician.diagnose_pod(pod_name, diagnostics, stream=True)
                stream_diagnosis(diagnosis_stream, "pod", pod_name)

            # Display token usage
            token_usage = diagnostician.get_token_usage()
            display_token_usage(token_usage)

            # Apply fixes if requested
            if auto_fix:
                commands = extract_kubectl_commands(diagnosis)
                apply_fixes(commands, auto_yes=yes)

    except Exception as e:
        if output_format == "json":
            error_output = {
                "error": str(e),
                "resource_type": "pod",
                "resource_name": pod_name,
                "namespace": namespace,
            }
            print(json.dumps(error_output, indent=2))
        else:
            console.print(f"[red]Error: Failed to get AI diagnosis: {e}[/red]")
        raise typer.Exit(1)


@diagnose_app.command("node")
def diagnose_node(
    node_name: str = typer.Argument(..., help="Name of the node to diagnose"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable kubectl result caching"),
    output_format: str = typer.Option("rich", "-o", "--output", help="Output format (rich or json)"),
    model: str = typer.Option(
        "sonnet", "--model", help="Claude model to use (sonnet, opus, haiku)"
    ),
    auto_fix: bool = typer.Option(False, "--auto-fix", help="Automatically apply suggested fixes"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompts for fixes"),
) -> None:
    """Diagnose a node issue.

    Gathers diagnostic information about a node and uses AI to analyze
    the data and provide actionable insights.

    Args:
        node_name: Name of the node to diagnose.
        no_cache: If True, disable kubectl result caching.
        output_format: Output format (rich or json).
        model: Claude model to use.
        auto_fix: If True, automatically apply suggested fixes.
        yes: If True, skip confirmation prompts when applying fixes.

    Example:
        $ kfix diagnose node worker-1
        $ kfix diagnose node worker-1 --no-cache
        $ kfix diagnose node worker-1 -o json
        $ kfix diagnose node worker-1 --model opus
        $ kfix diagnose node worker-1 --auto-fix
    """
    # Check cluster access
    kubectl = Kubectl(use_cache=not no_cache)
    if not kubectl.check_cluster_access():
        console.print("[red]Error: Cannot access Kubernetes cluster.[/red]")
        console.print("\nMake sure:")
        console.print("  • kubectl is installed")
        console.print("  • You have a valid kubeconfig")
        console.print("  • The cluster is running")
        raise typer.Exit(1)

    # Get diagnostician
    diagnostician = get_diagnostician(model=model)

    # Gather diagnostics
    with console.status(f"[cyan]Gathering diagnostics for node '{node_name}'...[/cyan]"):
        try:
            diagnostics = kubectl.gather_node_diagnostics(node_name)
        except KubectlError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

    # Analyze with AI
    try:
        diagnosis: str
        if output_format == "json":
            diagnosis = diagnostician.diagnose_node(node_name, diagnostics, stream=False)
            token_usage = diagnostician.get_token_usage()
            output_json("node", node_name, None, diagnosis, diagnostics, token_usage)
        else:
            console.print("[cyan]Analyzing with AI...[/cyan]")
            if auto_fix:
                diagnosis = diagnostician.diagnose_node(node_name, diagnostics, stream=False)
                console.print()
                console.print(
                    Panel(
                        Markdown(diagnosis),
                        title=f"[bold cyan]Diagnosis for node '{node_name}'[/bold cyan]",
                        border_style="cyan",
                    )
                )
            else:
                diagnosis_stream = diagnostician.diagnose_node(node_name, diagnostics, stream=True)
                stream_diagnosis(diagnosis_stream, "node", node_name)
            token_usage = diagnostician.get_token_usage()
            display_token_usage(token_usage)

            if auto_fix:
                commands = extract_kubectl_commands(diagnosis)
                apply_fixes(commands, auto_yes=yes)

    except Exception as e:
        if output_format == "json":
            error_output = {
                "error": str(e),
                "resource_type": "node",
                "resource_name": node_name,
            }
            print(json.dumps(error_output, indent=2))
        else:
            console.print(f"[red]Error: Failed to get AI diagnosis: {e}[/red]")
        raise typer.Exit(1)


@diagnose_app.command("deployment")
def diagnose_deployment(
    deployment_name: str = typer.Argument(..., help="Name of the deployment to diagnose"),
    namespace: str = typer.Option("default", "-n", "--namespace", help="Kubernetes namespace"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable kubectl result caching"),
    output_format: str = typer.Option("rich", "-o", "--output", help="Output format (rich or json)"),
    model: str = typer.Option(
        "sonnet", "--model", help="Claude model to use (sonnet, opus, haiku)"
    ),
    auto_fix: bool = typer.Option(False, "--auto-fix", help="Automatically apply suggested fixes"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompts for fixes"),
) -> None:
    """Diagnose a deployment issue.

    Gathers diagnostic information about a deployment and uses AI to analyze
    the data and provide actionable insights.

    Args:
        deployment_name: Name of the deployment to diagnose.
        namespace: Kubernetes namespace where the deployment is located.
        no_cache: If True, disable kubectl result caching.
        output_format: Output format (rich or json).
        model: Claude model to use.
        auto_fix: If True, automatically apply suggested fixes.
        yes: If True, skip confirmation prompts when applying fixes.

    Example:
        $ kfix diagnose deployment my-app -n production
        $ kfix diagnose deployment my-app --no-cache
        $ kfix diagnose deployment my-app -o json
        $ kfix diagnose deployment my-app --model opus
        $ kfix diagnose deployment my-app --auto-fix
    """
    # Check cluster access
    kubectl = Kubectl(use_cache=not no_cache)
    if not kubectl.check_cluster_access():
        console.print("[red]Error: Cannot access Kubernetes cluster.[/red]")
        console.print("\nMake sure:")
        console.print("  • kubectl is installed")
        console.print("  • You have a valid kubeconfig")
        console.print("  • The cluster is running")
        raise typer.Exit(1)

    # Get diagnostician
    diagnostician = get_diagnostician(model=model)

    # Gather diagnostics
    with console.status(
        f"[cyan]Gathering diagnostics for deployment '{deployment_name}'...[/cyan]"
    ):
        try:
            diagnostics = kubectl.gather_deployment_diagnostics(deployment_name, namespace)
        except KubectlError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

    # Analyze with AI
    try:
        diagnosis: str
        if output_format == "json":
            diagnosis = diagnostician.diagnose_deployment(
                deployment_name, diagnostics, stream=False
            )
            token_usage = diagnostician.get_token_usage()
            output_json("deployment", deployment_name, namespace, diagnosis, diagnostics, token_usage)
        else:
            console.print("[cyan]Analyzing with AI...[/cyan]")
            if auto_fix:
                diagnosis = diagnostician.diagnose_deployment(
                    deployment_name, diagnostics, stream=False
                )
                console.print()
                console.print(
                    Panel(
                        Markdown(diagnosis),
                        title=f"[bold cyan]Diagnosis for deployment '{deployment_name}'[/bold cyan]",
                        border_style="cyan",
                    )
                )
            else:
                diagnosis_stream = diagnostician.diagnose_deployment(
                    deployment_name, diagnostics, stream=True
                )
                stream_diagnosis(diagnosis_stream, "deployment", deployment_name)
            token_usage = diagnostician.get_token_usage()
            display_token_usage(token_usage)

            if auto_fix:
                commands = extract_kubectl_commands(diagnosis)
                apply_fixes(commands, auto_yes=yes)

    except Exception as e:
        if output_format == "json":
            error_output = {
                "error": str(e),
                "resource_type": "deployment",
                "resource_name": deployment_name,
                "namespace": namespace,
            }
            print(json.dumps(error_output, indent=2))
        else:
            console.print(f"[red]Error: Failed to get AI diagnosis: {e}[/red]")
        raise typer.Exit(1)


@diagnose_app.command("service")
def diagnose_service(
    service_name: str = typer.Argument(..., help="Name of the service to diagnose"),
    namespace: str = typer.Option("default", "-n", "--namespace", help="Kubernetes namespace"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable kubectl result caching"),
    output_format: str = typer.Option("rich", "-o", "--output", help="Output format (rich or json)"),
    model: str = typer.Option(
        "sonnet", "--model", help="Claude model to use (sonnet, opus, haiku)"
    ),
    auto_fix: bool = typer.Option(False, "--auto-fix", help="Automatically apply suggested fixes"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompts for fixes"),
) -> None:
    """Diagnose a service issue.

    Gathers diagnostic information about a service and uses AI to analyze
    the data and provide actionable insights.

    Args:
        service_name: Name of the service to diagnose.
        namespace: Kubernetes namespace where the service is located.
        no_cache: If True, disable kubectl result caching.
        output_format: Output format (rich or json).
        model: Claude model to use.
        auto_fix: If True, automatically apply suggested fixes.
        yes: If True, skip confirmation prompts when applying fixes.

    Example:
        $ kfix diagnose service my-app -n production
        $ kfix diagnose service my-app --no-cache
        $ kfix diagnose service my-app -o json
        $ kfix diagnose service my-app --model opus
        $ kfix diagnose service my-app --auto-fix
    """
    # Check cluster access
    kubectl = Kubectl(use_cache=not no_cache)
    if not kubectl.check_cluster_access():
        console.print("[red]Error: Cannot access Kubernetes cluster.[/red]")
        console.print("\nMake sure:")
        console.print("  • kubectl is installed")
        console.print("  • You have a valid kubeconfig")
        console.print("  • The cluster is running")
        raise typer.Exit(1)

    # Get diagnostician
    diagnostician = get_diagnostician(model=model)

    # Gather diagnostics
    with console.status(f"[cyan]Gathering diagnostics for service '{service_name}'...[/cyan]"):
        try:
            diagnostics = kubectl.gather_service_diagnostics(service_name, namespace)
        except KubectlError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

    # Analyze with AI
    try:
        diagnosis: str
        if output_format == "json":
            diagnosis = diagnostician.diagnose_service(service_name, diagnostics, stream=False)
            token_usage = diagnostician.get_token_usage()
            output_json("service", service_name, namespace, diagnosis, diagnostics, token_usage)
        else:
            console.print("[cyan]Analyzing with AI...[/cyan]")
            if auto_fix:
                diagnosis = diagnostician.diagnose_service(service_name, diagnostics, stream=False)
                console.print()
                console.print(
                    Panel(
                        Markdown(diagnosis),
                        title=f"[bold cyan]Diagnosis for service '{service_name}'[/bold cyan]",
                        border_style="cyan",
                    )
                )
            else:
                diagnosis_stream = diagnostician.diagnose_service(
                    service_name, diagnostics, stream=True
                )
                stream_diagnosis(diagnosis_stream, "service", service_name)
            token_usage = diagnostician.get_token_usage()
            display_token_usage(token_usage)

            if auto_fix:
                commands = extract_kubectl_commands(diagnosis)
                apply_fixes(commands, auto_yes=yes)

    except Exception as e:
        if output_format == "json":
            error_output = {
                "error": str(e),
                "resource_type": "service",
                "resource_name": service_name,
                "namespace": namespace,
            }
            print(json.dumps(error_output, indent=2))
        else:
            console.print(f"[red]Error: Failed to get AI diagnosis: {e}[/red]")
        raise typer.Exit(1)


@app.command("explain")
def explain(
    error: str = typer.Argument(..., help="Kubernetes error message to explain"),
    model: str = typer.Option(
        "sonnet", "--model", help="Claude model to use (sonnet, opus, haiku)"
    ),
) -> None:
    """Explain a Kubernetes error in plain English.

    Provides a detailed explanation of any Kubernetes error message,
    including common causes and how to fix it.

    Args:
        error: The Kubernetes error message to explain.
        model: Claude model to use.

    Example:
        $ kfix explain "CrashLoopBackOff"
        $ kfix explain "ImagePullBackOff"
        $ kfix explain "OOMKilled" --model opus
    """
    # Get diagnostician
    diagnostician = get_diagnostician(model=model)

    # Get explanation
    with console.status("[cyan]Getting explanation...[/cyan]"):
        try:
            explanation = diagnostician.explain_error(error)
        except Exception as e:
            console.print(f"[red]Error: Failed to get explanation: {e}[/red]")
            raise typer.Exit(1)

    # Display results
    console.print()
    console.print(
        Panel(
            Markdown(explanation),
            title="[bold cyan]Error Explanation[/bold cyan]",
            border_style="cyan",
        )
    )


@app.command("version")
def version() -> None:
    """Show kfix version.

    Example:
        $ kfix version
    """
    from kfix import __version__

    console.print(f"kfix version {__version__}")


if __name__ == "__main__":
    app()
