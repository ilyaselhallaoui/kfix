"""CLI interface for kfix."""

from typing import NoReturn

import typer
from rich import print as rprint
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from kfix.ai import Diagnostician
from kfix.config import Config
from kfix.kubectl import Kubectl, KubectlError

app = typer.Typer(help="AI-powered Kubernetes troubleshooter CLI")
config_app = typer.Typer(help="Configuration commands")
diagnose_app = typer.Typer(help="Diagnose Kubernetes resources")

app.add_typer(config_app, name="config")
app.add_typer(diagnose_app, name="diagnose")

console = Console()


def get_diagnostician() -> Diagnostician:
    """Get or create diagnostician with API key.

    Returns:
        Initialized Diagnostician instance.

    Raises:
        typer.Exit: If no API key is configured.
    """
    config = Config()
    api_key = config.get_api_key()

    if not api_key:
        console.print("[red]Error: No API key configured.[/red]")
        console.print("\nSet your Anthropic API key with:")
        console.print("  [cyan]kfix config set api-key YOUR_API_KEY[/cyan]")
        raise typer.Exit(1)

    return Diagnostician(api_key)


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
) -> None:
    """Diagnose a pod issue.

    Gathers diagnostic information about a pod and uses AI to analyze
    the data and provide actionable insights.

    Args:
        pod_name: Name of the pod to diagnose.
        namespace: Kubernetes namespace where the pod is located.

    Example:
        $ kfix diagnose pod my-app -n production
    """
    # Check cluster access
    kubectl = Kubectl()
    if not kubectl.check_cluster_access():
        console.print("[red]Error: Cannot access Kubernetes cluster.[/red]")
        console.print("\nMake sure:")
        console.print("  • kubectl is installed")
        console.print("  • You have a valid kubeconfig")
        console.print("  • The cluster is running")
        raise typer.Exit(1)

    # Get diagnostician
    diagnostician = get_diagnostician()

    # Gather diagnostics
    with console.status(f"[cyan]Gathering diagnostics for pod '{pod_name}'...[/cyan]"):
        try:
            diagnostics = kubectl.gather_pod_diagnostics(pod_name, namespace)
        except KubectlError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

    # Analyze with AI
    with console.status("[cyan]Analyzing with AI...[/cyan]"):
        try:
            diagnosis = diagnostician.diagnose_pod(pod_name, diagnostics)
        except Exception as e:
            console.print(f"[red]Error: Failed to get AI diagnosis: {e}[/red]")
            raise typer.Exit(1)

    # Display results
    console.print()
    console.print(
        Panel(
            Markdown(diagnosis),
            title=f"[bold cyan]Diagnosis for pod '{pod_name}'[/bold cyan]",
            border_style="cyan",
        )
    )


@diagnose_app.command("node")
def diagnose_node(
    node_name: str = typer.Argument(..., help="Name of the node to diagnose")
) -> None:
    """Diagnose a node issue.

    Gathers diagnostic information about a node and uses AI to analyze
    the data and provide actionable insights.

    Args:
        node_name: Name of the node to diagnose.

    Example:
        $ kfix diagnose node worker-1
    """
    # Check cluster access
    kubectl = Kubectl()
    if not kubectl.check_cluster_access():
        console.print("[red]Error: Cannot access Kubernetes cluster.[/red]")
        console.print("\nMake sure:")
        console.print("  • kubectl is installed")
        console.print("  • You have a valid kubeconfig")
        console.print("  • The cluster is running")
        raise typer.Exit(1)

    # Get diagnostician
    diagnostician = get_diagnostician()

    # Gather diagnostics
    with console.status(f"[cyan]Gathering diagnostics for node '{node_name}'...[/cyan]"):
        try:
            diagnostics = kubectl.gather_node_diagnostics(node_name)
        except KubectlError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

    # Analyze with AI
    with console.status("[cyan]Analyzing with AI...[/cyan]"):
        try:
            diagnosis = diagnostician.diagnose_node(node_name, diagnostics)
        except Exception as e:
            console.print(f"[red]Error: Failed to get AI diagnosis: {e}[/red]")
            raise typer.Exit(1)

    # Display results
    console.print()
    console.print(
        Panel(
            Markdown(diagnosis),
            title=f"[bold cyan]Diagnosis for node '{node_name}'[/bold cyan]",
            border_style="cyan",
        )
    )


@diagnose_app.command("deployment")
def diagnose_deployment(
    deployment_name: str = typer.Argument(..., help="Name of the deployment to diagnose"),
    namespace: str = typer.Option("default", "-n", "--namespace", help="Kubernetes namespace"),
) -> None:
    """Diagnose a deployment issue.

    Gathers diagnostic information about a deployment and uses AI to analyze
    the data and provide actionable insights.

    Args:
        deployment_name: Name of the deployment to diagnose.
        namespace: Kubernetes namespace where the deployment is located.

    Example:
        $ kfix diagnose deployment my-app -n production
    """
    # Check cluster access
    kubectl = Kubectl()
    if not kubectl.check_cluster_access():
        console.print("[red]Error: Cannot access Kubernetes cluster.[/red]")
        console.print("\nMake sure:")
        console.print("  • kubectl is installed")
        console.print("  • You have a valid kubeconfig")
        console.print("  • The cluster is running")
        raise typer.Exit(1)

    # Get diagnostician
    diagnostician = get_diagnostician()

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
    with console.status("[cyan]Analyzing with AI...[/cyan]"):
        try:
            diagnosis = diagnostician.diagnose_deployment(deployment_name, diagnostics)
        except Exception as e:
            console.print(f"[red]Error: Failed to get AI diagnosis: {e}[/red]")
            raise typer.Exit(1)

    # Display results
    console.print()
    console.print(
        Panel(
            Markdown(diagnosis),
            title=f"[bold cyan]Diagnosis for deployment '{deployment_name}'[/bold cyan]",
            border_style="cyan",
        )
    )


@diagnose_app.command("service")
def diagnose_service(
    service_name: str = typer.Argument(..., help="Name of the service to diagnose"),
    namespace: str = typer.Option("default", "-n", "--namespace", help="Kubernetes namespace"),
) -> None:
    """Diagnose a service issue.

    Gathers diagnostic information about a service and uses AI to analyze
    the data and provide actionable insights.

    Args:
        service_name: Name of the service to diagnose.
        namespace: Kubernetes namespace where the service is located.

    Example:
        $ kfix diagnose service my-app -n production
    """
    # Check cluster access
    kubectl = Kubectl()
    if not kubectl.check_cluster_access():
        console.print("[red]Error: Cannot access Kubernetes cluster.[/red]")
        console.print("\nMake sure:")
        console.print("  • kubectl is installed")
        console.print("  • You have a valid kubeconfig")
        console.print("  • The cluster is running")
        raise typer.Exit(1)

    # Get diagnostician
    diagnostician = get_diagnostician()

    # Gather diagnostics
    with console.status(f"[cyan]Gathering diagnostics for service '{service_name}'...[/cyan]"):
        try:
            diagnostics = kubectl.gather_service_diagnostics(service_name, namespace)
        except KubectlError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

    # Analyze with AI
    with console.status("[cyan]Analyzing with AI...[/cyan]"):
        try:
            diagnosis = diagnostician.diagnose_service(service_name, diagnostics)
        except Exception as e:
            console.print(f"[red]Error: Failed to get AI diagnosis: {e}[/red]")
            raise typer.Exit(1)

    # Display results
    console.print()
    console.print(
        Panel(
            Markdown(diagnosis),
            title=f"[bold cyan]Diagnosis for service '{service_name}'[/bold cyan]",
            border_style="cyan",
        )
    )


@app.command("explain")
def explain(error: str = typer.Argument(..., help="Kubernetes error message to explain")) -> None:
    """Explain a Kubernetes error in plain English.

    Provides a detailed explanation of any Kubernetes error message,
    including common causes and how to fix it.

    Args:
        error: The Kubernetes error message to explain.

    Example:
        $ kfix explain "CrashLoopBackOff"
        $ kfix explain "ImagePullBackOff"
    """
    # Get diagnostician
    diagnostician = get_diagnostician()

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
