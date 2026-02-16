"""CLI interface for kfix."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich import print as rprint

from kfix.config import Config
from kfix.kubectl import Kubectl, KubectlError
from kfix.ai import Diagnostician

app = typer.Typer(help="AI-powered Kubernetes troubleshooter CLI")
config_app = typer.Typer(help="Configuration commands")
diagnose_app = typer.Typer(help="Diagnose Kubernetes resources")

app.add_typer(config_app, name="config")
app.add_typer(diagnose_app, name="diagnose")

console = Console()


def get_diagnostician() -> Diagnostician:
    """Get or create diagnostician with API key."""
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
    value: str = typer.Argument(..., help="Configuration value")
):
    """Set a configuration value."""
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
    namespace: str = typer.Option("default", "-n", "--namespace", help="Kubernetes namespace")
):
    """Diagnose a pod issue."""

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
    console.print(Panel(
        Markdown(diagnosis),
        title=f"[bold cyan]Diagnosis for pod '{pod_name}'[/bold cyan]",
        border_style="cyan"
    ))


@diagnose_app.command("node")
def diagnose_node(
    node_name: str = typer.Argument(..., help="Name of the node to diagnose")
):
    """Diagnose a node issue."""

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
    console.print(Panel(
        Markdown(diagnosis),
        title=f"[bold cyan]Diagnosis for node '{node_name}'[/bold cyan]",
        border_style="cyan"
    ))


@app.command("explain")
def explain(
    error: str = typer.Argument(..., help="Kubernetes error message to explain")
):
    """Explain a Kubernetes error in plain English."""

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
    console.print(Panel(
        Markdown(explanation),
        title="[bold cyan]Error Explanation[/bold cyan]",
        border_style="cyan"
    ))


@app.command("version")
def version():
    """Show kfix version."""
    from kfix import __version__
    console.print(f"kfix version {__version__}")


if __name__ == "__main__":
    app()
