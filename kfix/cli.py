"""CLI interface for kfix."""

import json
import re
import shlex
import subprocess
from datetime import datetime
from typing import Callable, Dict, Any, Iterator, List, Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

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
    commands: List[str] = []

    # Match code blocks with kubectl commands
    code_block_pattern = r"```(?:bash|sh)?\s*(kubectl[^\n]+(?:\n(?!```).*)*)\s*```"
    inline_pattern = r"`(kubectl[^`]+)`"

    # Find code blocks
    for match in re.finditer(code_block_pattern, diagnosis, re.MULTILINE | re.DOTALL):
        block = match.group(1).strip()
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
            result = subprocess.run(
                shlex.split(cmd), capture_output=True, text=True, timeout=60
            )

            if result.returncode == 0:
                console.print(f"[green]\u2713 Command {i} executed successfully[/green]")
                if result.stdout.strip():
                    console.print(f"[dim]{result.stdout.strip()}[/dim]")
            else:
                console.print(f"[red]\u2717 Command {i} failed[/red]")
                if result.stderr.strip():
                    console.print(f"[red]{result.stderr.strip()}[/red]")

        except subprocess.TimeoutExpired:
            console.print(f"[red]\u2717 Command {i} timed out[/red]")
        except Exception as e:
            console.print(f"[red]\u2717 Command {i} failed: {e}[/red]")


def display_token_usage(token_usage: Optional[TokenUsage], show_cost: bool = True) -> None:
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
    namespace: Optional[str],
    diagnosis: str,
    diagnostics: Optional[Dict[str, str]] = None,
    token_usage: Optional[TokenUsage] = None,
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


def _diagnose_resource(
    resource_type: str,
    resource_name: str,
    namespace: Optional[str],
    gather_fn: Callable[[], Dict[str, str]],
    diagnose_fn: Callable[..., Any],
    diagnostician: Diagnostician,
    kubectl: Kubectl,
    output_format: str = "rich",
    auto_fix: bool = False,
    yes: bool = False,
) -> None:
    """Generic diagnosis flow for any Kubernetes resource.

    Args:
        resource_type: Type of resource (pod, node, deployment, service).
        resource_name: Name of the resource.
        namespace: Kubernetes namespace (None for cluster-scoped resources).
        gather_fn: Callable that gathers diagnostics (no args, already bound).
        diagnose_fn: Diagnostician method to call (e.g. diagnostician.diagnose_pod).
        diagnostician: Diagnostician instance.
        kubectl: Kubectl instance.
        output_format: Output format (rich or json).
        auto_fix: If True, automatically apply suggested fixes.
        yes: If True, skip confirmation prompts for fixes.
    """
    # Gather diagnostics
    label = f"{resource_type} '{resource_name}'"
    with console.status(f"[cyan]Gathering diagnostics for {label}...[/cyan]"):
        try:
            diagnostics = gather_fn()
        except KubectlError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

    # Analyze with AI
    try:
        diagnosis: str
        if output_format == "json":
            diagnosis = diagnose_fn(resource_name, diagnostics, stream=False)
            token_usage = diagnostician.get_token_usage()
            output_json(resource_type, resource_name, namespace, diagnosis, diagnostics, token_usage)
        else:
            console.print("[cyan]Analyzing with AI...[/cyan]")
            if auto_fix:
                diagnosis = diagnose_fn(resource_name, diagnostics, stream=False)
                console.print()
                console.print(
                    Panel(
                        Markdown(diagnosis),
                        title=f"[bold cyan]Diagnosis for {label}[/bold cyan]",
                        border_style="cyan",
                    )
                )
            else:
                diagnosis_stream = diagnose_fn(resource_name, diagnostics, stream=True)
                stream_diagnosis(diagnosis_stream, resource_type, resource_name)

            token_usage = diagnostician.get_token_usage()
            display_token_usage(token_usage)

            if auto_fix:
                commands = extract_kubectl_commands(diagnosis)
                apply_fixes(commands, auto_yes=yes)

    except typer.Exit:
        raise
    except Exception as e:
        if output_format == "json":
            error_output: Dict[str, Any] = {
                "error": str(e),
                "resource_type": resource_type,
                "resource_name": resource_name,
            }
            if namespace:
                error_output["namespace"] = namespace
            print(json.dumps(error_output, indent=2))
        else:
            console.print(f"[red]Error: Failed to get AI diagnosis: {e}[/red]")
        raise typer.Exit(1)


def _check_cluster(kubectl: Kubectl) -> None:
    """Check cluster access and exit if unavailable."""
    if not kubectl.check_cluster_access():
        console.print("[red]Error: Cannot access Kubernetes cluster.[/red]")
        console.print("\nMake sure:")
        console.print("  \u2022 kubectl is installed")
        console.print("  \u2022 You have a valid kubeconfig")
        console.print("  \u2022 The cluster is running")
        raise typer.Exit(1)


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Configuration key (e.g., api-key)"),
    value: str = typer.Argument(..., help="Configuration value"),
) -> None:
    """Set a configuration value.

    Example:
        $ kfix config set api-key sk-ant-api03-...
    """
    config = Config()

    if key == "api-key":
        config.set_api_key(value)
        console.print(f"[green]\u2713[/green] API key saved to {config.config_file}")
    else:
        console.print(f"[red]Error: Unknown config key '{key}'[/red]")
        raise typer.Exit(1)


@diagnose_app.command("pod")
def diagnose_pod(
    pod_name: str = typer.Argument(..., help="Name of the pod to diagnose"),
    namespace: str = typer.Option("default", "-n", "--namespace", help="Kubernetes namespace"),
    context: Optional[str] = typer.Option(None, "--context", help="Kubernetes context to use"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable kubectl result caching"),
    output_format: str = typer.Option("rich", "-o", "--output", help="Output format (rich or json)"),
    model: str = typer.Option(
        "sonnet", "--model", help="Claude model to use (sonnet, opus, haiku)"
    ),
    auto_fix: bool = typer.Option(False, "--auto-fix", help="Automatically apply suggested fixes"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompts for fixes"),
) -> None:
    """Diagnose a pod issue."""
    kubectl = Kubectl(use_cache=not no_cache, context=context)
    _check_cluster(kubectl)
    diagnostician = get_diagnostician(model=model)
    _diagnose_resource(
        resource_type="pod",
        resource_name=pod_name,
        namespace=namespace,
        gather_fn=lambda: kubectl.gather_pod_diagnostics(pod_name, namespace),
        diagnose_fn=diagnostician.diagnose_pod,
        diagnostician=diagnostician,
        kubectl=kubectl,
        output_format=output_format,
        auto_fix=auto_fix,
        yes=yes,
    )


@diagnose_app.command("node")
def diagnose_node(
    node_name: str = typer.Argument(..., help="Name of the node to diagnose"),
    context: Optional[str] = typer.Option(None, "--context", help="Kubernetes context to use"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable kubectl result caching"),
    output_format: str = typer.Option("rich", "-o", "--output", help="Output format (rich or json)"),
    model: str = typer.Option(
        "sonnet", "--model", help="Claude model to use (sonnet, opus, haiku)"
    ),
    auto_fix: bool = typer.Option(False, "--auto-fix", help="Automatically apply suggested fixes"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompts for fixes"),
) -> None:
    """Diagnose a node issue."""
    kubectl = Kubectl(use_cache=not no_cache, context=context)
    _check_cluster(kubectl)
    diagnostician = get_diagnostician(model=model)
    _diagnose_resource(
        resource_type="node",
        resource_name=node_name,
        namespace=None,
        gather_fn=lambda: kubectl.gather_node_diagnostics(node_name),
        diagnose_fn=diagnostician.diagnose_node,
        diagnostician=diagnostician,
        kubectl=kubectl,
        output_format=output_format,
        auto_fix=auto_fix,
        yes=yes,
    )


@diagnose_app.command("deployment")
def diagnose_deployment(
    deployment_name: str = typer.Argument(..., help="Name of the deployment to diagnose"),
    namespace: str = typer.Option("default", "-n", "--namespace", help="Kubernetes namespace"),
    context: Optional[str] = typer.Option(None, "--context", help="Kubernetes context to use"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable kubectl result caching"),
    output_format: str = typer.Option("rich", "-o", "--output", help="Output format (rich or json)"),
    model: str = typer.Option(
        "sonnet", "--model", help="Claude model to use (sonnet, opus, haiku)"
    ),
    auto_fix: bool = typer.Option(False, "--auto-fix", help="Automatically apply suggested fixes"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompts for fixes"),
) -> None:
    """Diagnose a deployment issue."""
    kubectl = Kubectl(use_cache=not no_cache, context=context)
    _check_cluster(kubectl)
    diagnostician = get_diagnostician(model=model)
    _diagnose_resource(
        resource_type="deployment",
        resource_name=deployment_name,
        namespace=namespace,
        gather_fn=lambda: kubectl.gather_deployment_diagnostics(deployment_name, namespace),
        diagnose_fn=diagnostician.diagnose_deployment,
        diagnostician=diagnostician,
        kubectl=kubectl,
        output_format=output_format,
        auto_fix=auto_fix,
        yes=yes,
    )


@diagnose_app.command("service")
def diagnose_service(
    service_name: str = typer.Argument(..., help="Name of the service to diagnose"),
    namespace: str = typer.Option("default", "-n", "--namespace", help="Kubernetes namespace"),
    context: Optional[str] = typer.Option(None, "--context", help="Kubernetes context to use"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable kubectl result caching"),
    output_format: str = typer.Option("rich", "-o", "--output", help="Output format (rich or json)"),
    model: str = typer.Option(
        "sonnet", "--model", help="Claude model to use (sonnet, opus, haiku)"
    ),
    auto_fix: bool = typer.Option(False, "--auto-fix", help="Automatically apply suggested fixes"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompts for fixes"),
) -> None:
    """Diagnose a service issue."""
    kubectl = Kubectl(use_cache=not no_cache, context=context)
    _check_cluster(kubectl)
    diagnostician = get_diagnostician(model=model)
    _diagnose_resource(
        resource_type="service",
        resource_name=service_name,
        namespace=namespace,
        gather_fn=lambda: kubectl.gather_service_diagnostics(service_name, namespace),
        diagnose_fn=diagnostician.diagnose_service,
        diagnostician=diagnostician,
        kubectl=kubectl,
        output_format=output_format,
        auto_fix=auto_fix,
        yes=yes,
    )


@app.command("scan")
def scan(
    namespace: Optional[str] = typer.Option(
        None, "-n", "--namespace", help="Kubernetes namespace to scan"
    ),
    all_namespaces: bool = typer.Option(
        False, "-A", "--all-namespaces", help="Scan all namespaces"
    ),
    context: Optional[str] = typer.Option(None, "--context", help="Kubernetes context to use"),
    model: str = typer.Option(
        "sonnet", "--model", help="Claude model to use (sonnet, opus, haiku)"
    ),
    output_format: str = typer.Option("rich", "-o", "--output", help="Output format (rich or json)"),
) -> None:
    """Scan for unhealthy resources in a namespace or across all namespaces.

    Example:
        $ kfix scan -n production
        $ kfix scan --all-namespaces
        $ kfix scan --context my-cluster
    """
    kubectl = Kubectl(context=context)
    _check_cluster(kubectl)

    # Scan for unhealthy resources
    with console.status("[cyan]Scanning for unhealthy resources...[/cyan]"):
        if all_namespaces:
            unhealthy = kubectl.scan_all_namespaces()
        else:
            ns = namespace or "default"
            unhealthy = kubectl.scan_namespace(ns)

    if not unhealthy:
        if output_format == "json":
            print(json.dumps({"resources": [], "total": 0}, indent=2))
        else:
            console.print("[green]\u2713 No unhealthy resources found.[/green]")
        return

    # Display summary table
    if output_format != "json":
        table = Table(title="Unhealthy Resources", border_style="red")
        table.add_column("Kind", style="cyan")
        table.add_column("Name", style="bold")
        table.add_column("Namespace", style="dim")
        table.add_column("Status", style="yellow")
        table.add_column("Reason", style="red")

        for r in unhealthy:
            table.add_row(r["kind"], r["name"], r["namespace"] or "-", r["status"], r["reason"])

        console.print()
        console.print(table)
        console.print(f"\n[bold red]Found {len(unhealthy)} unhealthy resource(s).[/bold red]")

    # Diagnose each with AI
    diagnostician = get_diagnostician(model=model)

    # Map resource types to their gather and diagnose functions
    gather_map: Dict[str, Callable[..., Dict[str, str]]] = {
        "pod": kubectl.gather_pod_diagnostics,
        "node": kubectl.gather_node_diagnostics,
        "deployment": kubectl.gather_deployment_diagnostics,
        "service": kubectl.gather_service_diagnostics,
    }
    diagnose_map: Dict[str, Callable[..., Any]] = {
        "pod": diagnostician.diagnose_pod,
        "node": diagnostician.diagnose_node,
        "deployment": diagnostician.diagnose_deployment,
        "service": diagnostician.diagnose_service,
    }

    results: List[Dict[str, Any]] = []

    for i, resource in enumerate(unhealthy):
        kind = resource["kind"]
        name = resource["name"]
        ns = resource["namespace"]
        label = f"{kind}/{name}" + (f" ({ns})" if ns else "")

        if output_format != "json":
            console.print(f"\n[cyan]({i + 1}/{len(unhealthy)}) Diagnosing {label}...[/cyan]")

        gather_fn = gather_map.get(kind)
        diagnose_fn = diagnose_map.get(kind)

        if not gather_fn or not diagnose_fn:
            continue

        try:
            # Gather diagnostics
            if kind == "node":
                diagnostics = gather_fn(name)
            else:
                diagnostics = gather_fn(name, ns)

            # Get AI diagnosis (non-streaming for scan)
            diagnosis = diagnose_fn(name, diagnostics, stream=False)

            if output_format == "json":
                results.append({
                    "kind": kind,
                    "name": name,
                    "namespace": ns,
                    "status": resource["status"],
                    "reason": resource["reason"],
                    "diagnosis": diagnosis,
                })
            else:
                console.print(
                    Panel(
                        Markdown(diagnosis),
                        title=f"[bold cyan]Diagnosis for {label}[/bold cyan]",
                        border_style="cyan",
                    )
                )
                display_token_usage(diagnostician.get_token_usage())

        except Exception as e:
            if output_format == "json":
                results.append({
                    "kind": kind,
                    "name": name,
                    "namespace": ns,
                    "error": str(e),
                })
            else:
                console.print(f"[red]Failed to diagnose {label}: {e}[/red]")

    if output_format == "json":
        print(json.dumps({"resources": results, "total": len(unhealthy)}, indent=2))


@app.command("explain")
def explain(
    error: str = typer.Argument(..., help="Kubernetes error message to explain"),
    model: str = typer.Option(
        "sonnet", "--model", help="Claude model to use (sonnet, opus, haiku)"
    ),
) -> None:
    """Explain a Kubernetes error in plain English.

    Example:
        $ kfix explain "CrashLoopBackOff"
        $ kfix explain "ImagePullBackOff"
        $ kfix explain "OOMKilled" --model opus
    """
    diagnostician = get_diagnostician(model=model)

    with console.status("[cyan]Getting explanation...[/cyan]"):
        try:
            explanation = diagnostician.explain_error(error)
        except Exception as e:
            console.print(f"[red]Error: Failed to get explanation: {e}[/red]")
            raise typer.Exit(1)

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
