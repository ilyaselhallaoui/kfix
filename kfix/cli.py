"""CLI interface for kfix."""

import json
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple

import typer
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
SAFE_AUTO_FIX_PREFIXES = {
    "annotate",
    "apply",
    "label",
    "patch",
    "rollout restart",
    "scale",
    "set image",
    "set resources",
}
RISKY_AUTO_FIX_VERBS = {"delete", "drain", "replace"}


def _command_action_signature(command: str) -> str:
    """Return a normalized kubectl action signature from command text."""
    try:
        parts = shlex.split(command)
    except ValueError:
        return ""

    if len(parts) < 2 or parts[0] != "kubectl":
        return ""

    if len(parts) >= 3 and parts[1] == "rollout" and parts[2] == "restart":
        return "rollout restart"
    if len(parts) >= 3 and parts[1] == "set" and parts[2] in {"image", "resources"}:
        return f"set {parts[2]}"
    return parts[1]


def _is_risky_command(command: str) -> bool:
    """Return True for potentially destructive kubectl commands."""
    return _command_action_signature(command) in RISKY_AUTO_FIX_VERBS


def _is_safe_auto_fix_command(command: str) -> bool:
    """Return True when command is in the safe auto-fix allowlist."""
    return _command_action_signature(command) in SAFE_AUTO_FIX_PREFIXES


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
    commands: List[str],
    auto_yes: bool = False,
    dry_run: bool = False,
    policy: str = "review",
) -> None:
    """Apply kubectl fix commands with user confirmation.

    Args:
        commands: List of kubectl commands to execute.
        auto_yes: If True, skip confirmation prompts.
        dry_run: If True, only show commands without executing.
        policy: Auto-fix safety policy (off, review, safe).
    """
    if not commands:
        console.print("[yellow]No kubectl commands found in diagnosis.[/yellow]")
        return
    if policy not in {"off", "review", "safe"}:
        console.print(f"[red]Invalid auto-fix policy '{policy}'.[/red]")
        return

    console.print("\n[bold cyan]Found the following fix commands:[/bold cyan]")
    for i, cmd in enumerate(commands, 1):
        console.print(f"  {i}. [green]{cmd}[/green]")

    if policy == "off":
        console.print("\n[yellow]Auto-fix policy is 'off'; commands were not executed.[/yellow]")
        return

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
        if policy == "safe" and not _is_safe_auto_fix_command(cmd):
            console.print(f"[yellow]Skipped command {i} (blocked by safe policy).[/yellow]")
            continue

        is_risky = _is_risky_command(cmd)

        # Individual confirmation if not applying all
        if (not apply_all and not auto_yes) or (is_risky and not auto_yes):
            prompt = f"Execute command {i}?"
            if is_risky:
                prompt = f"Command {i} may be destructive. Execute anyway?"
            if not Confirm.ask(prompt, default=False):
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
        if sys.stdout.isatty():
            console.print()
            console.print(
                Panel(
                    "[bold]Welcome to kfix![/bold]\n\n"
                    "To get started, you need a free Anthropic API key.\n\n"
                    "  1. Visit [link=https://console.anthropic.com]console.anthropic.com[/link]\n"
                    "  2. Sign up (free) and go to [bold]API Keys[/bold]\n"
                    "  3. Create a new key and paste it below\n\n"
                    "[dim]Your key will be saved to ~/.kfix/config.yaml[/dim]",
                    title="[bold cyan]Setup Required[/bold cyan]",
                    border_style="cyan",
                    padding=(1, 2),
                )
            )
            api_key = typer.prompt(
                "  Anthropic API key",
                hide_input=True,
                prompt_suffix=" › ",
            ).strip()
            if api_key:
                config.set_api_key(api_key)
                console.print("[green]  ✓ API key saved — you're all set![/green]\n")
            else:
                console.print("[red]No API key provided. Exiting.[/red]")
                raise typer.Exit(1)
        else:
            console.print("[red]Error: No API key configured.[/red]")
            console.print("Set it with:  kfix config set api-key YOUR_KEY")
            console.print("Or export:    ANTHROPIC_API_KEY=YOUR_KEY")
            raise typer.Exit(1)

    try:
        return Diagnostician(api_key, model=model)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


def _diagnose_resource(
    resource_type: str,
    resource_name: str,
    namespace: Optional[str],
    gather_fn: Callable[[], Dict[str, str]],
    diagnose_fn: Callable[..., Any],
    diagnostician: Diagnostician,
    output_format: str = "rich",
    auto_fix: bool = False,
    yes: bool = False,
    auto_fix_policy: str = "review",
) -> None:
    """Generic diagnosis flow for any Kubernetes resource.

    Args:
        resource_type: Type of resource (pod, node, deployment, service).
        resource_name: Name of the resource.
        namespace: Kubernetes namespace (None for cluster-scoped resources).
        gather_fn: Callable that gathers diagnostics (no args, already bound).
        diagnose_fn: Diagnostician method to call (e.g. diagnostician.diagnose_pod).
        diagnostician: Diagnostician instance.
        output_format: Output format (rich or json).
        auto_fix: If True, automatically apply suggested fixes.
        yes: If True, skip confirmation prompts for fixes.
        auto_fix_policy: Auto-fix safety policy (off, review, safe).
    """
    # Gather diagnostics
    label = f"{resource_type} '{resource_name}'"
    with console.status(f"[cyan]Gathering diagnostics for {label}...[/cyan]"):
        try:
            diagnostics = gather_fn()
        except KubectlError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1) from e

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
                diagnosis = stream_diagnosis(diagnosis_stream, resource_type, resource_name)

            token_usage = diagnostician.get_token_usage()
            display_token_usage(token_usage)

            if auto_fix:
                commands = extract_kubectl_commands(diagnosis)
                apply_fixes(commands, auto_yes=yes, policy=auto_fix_policy)

        # Save to history (best-effort)
        try:
            Config().save_to_history(
                resource_type=resource_type,
                resource_name=resource_name,
                namespace=namespace,
                diagnosis=diagnosis,
                model=diagnostician.model_name,
            )
        except Exception:
            pass

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
        raise typer.Exit(1) from e


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
    auto_fix_policy: str = typer.Option(
        "review",
        "--auto-fix-policy",
        help="Auto-fix safety policy: off, review, safe",
    ),
) -> None:
    """Diagnose a pod issue."""
    kubectl = Kubectl(use_cache=not no_cache, context=context)
    diagnostician = get_diagnostician(model=model)
    _check_cluster(kubectl)
    _diagnose_resource(
        resource_type="pod",
        resource_name=pod_name,
        namespace=namespace,
        gather_fn=lambda: kubectl.gather_pod_diagnostics(pod_name, namespace),
        diagnose_fn=diagnostician.diagnose_pod,
        diagnostician=diagnostician,
        output_format=output_format,
        auto_fix=auto_fix,
        yes=yes,
        auto_fix_policy=auto_fix_policy,
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
    auto_fix_policy: str = typer.Option(
        "review",
        "--auto-fix-policy",
        help="Auto-fix safety policy: off, review, safe",
    ),
) -> None:
    """Diagnose a node issue."""
    kubectl = Kubectl(use_cache=not no_cache, context=context)
    diagnostician = get_diagnostician(model=model)
    _check_cluster(kubectl)
    _diagnose_resource(
        resource_type="node",
        resource_name=node_name,
        namespace=None,
        gather_fn=lambda: kubectl.gather_node_diagnostics(node_name),
        diagnose_fn=diagnostician.diagnose_node,
        diagnostician=diagnostician,
        output_format=output_format,
        auto_fix=auto_fix,
        yes=yes,
        auto_fix_policy=auto_fix_policy,
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
    auto_fix_policy: str = typer.Option(
        "review",
        "--auto-fix-policy",
        help="Auto-fix safety policy: off, review, safe",
    ),
) -> None:
    """Diagnose a deployment issue."""
    kubectl = Kubectl(use_cache=not no_cache, context=context)
    diagnostician = get_diagnostician(model=model)
    _check_cluster(kubectl)
    _diagnose_resource(
        resource_type="deployment",
        resource_name=deployment_name,
        namespace=namespace,
        gather_fn=lambda: kubectl.gather_deployment_diagnostics(deployment_name, namespace),
        diagnose_fn=diagnostician.diagnose_deployment,
        diagnostician=diagnostician,
        output_format=output_format,
        auto_fix=auto_fix,
        yes=yes,
        auto_fix_policy=auto_fix_policy,
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
    auto_fix_policy: str = typer.Option(
        "review",
        "--auto-fix-policy",
        help="Auto-fix safety policy: off, review, safe",
    ),
) -> None:
    """Diagnose a service issue."""
    kubectl = Kubectl(use_cache=not no_cache, context=context)
    diagnostician = get_diagnostician(model=model)
    _check_cluster(kubectl)
    _diagnose_resource(
        resource_type="service",
        resource_name=service_name,
        namespace=namespace,
        gather_fn=lambda: kubectl.gather_service_diagnostics(service_name, namespace),
        diagnose_fn=diagnostician.diagnose_service,
        diagnostician=diagnostician,
        output_format=output_format,
        auto_fix=auto_fix,
        yes=yes,
        auto_fix_policy=auto_fix_policy,
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
        table.add_column("Kind", style="cyan", no_wrap=True)
        table.add_column("Name", style="bold", min_width=30, overflow="fold")
        table.add_column("Namespace", style="dim", no_wrap=True)
        table.add_column("Status", style="yellow", no_wrap=True)
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
            diagnostics = gather_fn(name) if kind == "node" else gather_fn(name, ns)

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


@app.command("watch")
def watch(
    namespace: Optional[str] = typer.Option(
        None, "-n", "--namespace", help="Namespace to watch (default: default)"
    ),
    all_namespaces: bool = typer.Option(
        False, "-A", "--all-namespaces", help="Watch all namespaces"
    ),
    context: Optional[str] = typer.Option(None, "--context", help="Kubernetes context to use"),
    interval: int = typer.Option(30, "--interval", help="Scan interval in seconds"),
) -> None:
    """Continuously monitor for unhealthy resources. Press Ctrl+C to stop.

    Example:
        $ kfix watch -n production
        $ kfix watch --all-namespaces --interval 60
    """
    kubectl = Kubectl(context=context, use_cache=False)
    _check_cluster(kubectl)

    known_keys: Set[Tuple[str, str, Optional[str]]] = set()
    first_run = True

    console.print(
        f"[bold cyan]kfix watch[/bold cyan] — scanning every [bold]{interval}s[/bold]. "
        "Press [bold]Ctrl+C[/bold] to stop.\n"
    )

    try:
        while True:
            scan_time = datetime.now().strftime("%H:%M:%S")

            if all_namespaces:
                unhealthy = kubectl.scan_all_namespaces()
            else:
                ns = namespace or "default"
                unhealthy = kubectl.scan_namespace(ns)

            current_keys: Set[Tuple[str, str, Optional[str]]] = {
                (r["kind"], r["name"], r["namespace"]) for r in unhealthy
            }
            new_keys = current_keys - known_keys
            resolved_keys = known_keys - current_keys

            # Build table
            table = Table(
                title=f"Unhealthy Resources  [{scan_time}]",
                border_style="red" if unhealthy else "green",
                show_lines=False,
            )
            table.add_column("Kind", style="cyan", no_wrap=True)
            table.add_column("Name", style="bold", min_width=30, overflow="fold")
            table.add_column("Namespace", style="dim", no_wrap=True)
            table.add_column("Status", style="yellow", no_wrap=True)
            table.add_column("Reason", style="red")

            for r in unhealthy:
                key = (r["kind"], r["name"], r["namespace"])
                name_display = (
                    f"[bold green]{r['name']} ✦[/bold green]"
                    if key in new_keys
                    else r["name"]
                )
                table.add_row(
                    r["kind"],
                    name_display,
                    r["namespace"] or "-",
                    r["status"],
                    r["reason"],
                )

            console.clear()
            if unhealthy:
                console.print(table)
                console.print(
                    f"\n[bold red]  {len(unhealthy)} unhealthy resource(s)[/bold red]",
                    end="",
                )
            else:
                console.print(f"[green]  ✓ All resources healthy  [{scan_time}][/green]")

            if not first_run:
                if new_keys:
                    console.print(
                        f"\n\n[bold yellow]  ⚠  {len(new_keys)} new issue(s)![/bold yellow]"
                    )
                    for kind, name, ns in sorted(new_keys):
                        ns_flag = f" -n {ns}" if ns else ""
                        console.print(
                            f"     → [cyan]kfix diagnose {kind} {name}{ns_flag}[/cyan]"
                        )
                if resolved_keys:
                    console.print(
                        f"\n[green]  ✓ {len(resolved_keys)} issue(s) resolved[/green]"
                    )

            console.print(
                f"\n[dim]  Next scan in {interval}s — Ctrl+C to stop[/dim]"
            )

            known_keys = current_keys
            first_run = False
            time.sleep(interval)

    except KeyboardInterrupt:
        console.print("\n\n[dim]Watch stopped.[/dim]")


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
            raise typer.Exit(1) from e

    console.print()
    console.print(
        Panel(
            Markdown(explanation),
            title="[bold cyan]Error Explanation[/bold cyan]",
            border_style="cyan",
        )
    )


history_app = typer.Typer(help="Diagnosis history commands")
app.add_typer(history_app, name="history")


@history_app.callback(invoke_without_command=True)
def history_list(
    ctx: typer.Context,
    limit: int = typer.Option(20, "-n", "--limit", help="Number of entries to show"),
) -> None:
    """Show recent diagnosis history.

    Example:
        $ kfix history
        $ kfix history -n 50
        $ kfix history clear
    """
    if ctx.invoked_subcommand is not None:
        return

    config = Config()
    entries = config.get_history(limit=limit)

    if not entries:
        console.print("[dim]No diagnosis history yet.[/dim]")
        console.print("Run [cyan]kfix diagnose pod <name>[/cyan] to create your first entry.")
        return

    table = Table(title=f"Diagnosis History (last {len(entries)})", border_style="cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Time", style="dim", no_wrap=True)
    table.add_column("Resource", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold", min_width=20, overflow="fold")
    table.add_column("Namespace", style="dim")
    table.add_column("Model", style="dim")

    for i, entry in enumerate(entries, 1):
        # Parse timestamp
        try:
            ts = datetime.fromisoformat(entry["timestamp"].rstrip("Z"))
            time_str = ts.strftime("%m-%d %H:%M")
        except (ValueError, KeyError):
            time_str = "—"

        table.add_row(
            str(i),
            time_str,
            entry.get("resource_type", "—"),
            entry.get("resource_name", "—"),
            entry.get("namespace") or "—",
            entry.get("model", "—"),
        )

    console.print()
    console.print(table)
    console.print(
        "\n[dim]Tip: Diagnoses are saved automatically after each kfix diagnose run.[/dim]"
    )


@history_app.command("clear")
def history_clear(
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation"),
) -> None:
    """Clear all diagnosis history."""
    if not yes:
        confirmed = Confirm.ask("Clear all diagnosis history?", default=False)
        if not confirmed:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)

    Config().clear_history()
    console.print("[green]✓ History cleared.[/green]")


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
