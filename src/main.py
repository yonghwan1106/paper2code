#!/usr/bin/env python3
"""
Paper2Code - Convert Scientific Papers to Executable Python Code

A multi-agent AI system that automatically converts algorithms described
in scientific papers into runnable Python implementations.

Usage:
    python -m src.main --input paper.pdf --output ./output
    python -m src.main paper.pdf -o ./output -v

Author: Paper2Code Team
"""

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .agents import Paper2CodeOrchestrator
from .config import get_config


console = Console()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="paper2code",
        description="Convert scientific papers to executable Python code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic usage
    python -m src.main --input paper.pdf --output ./output

    # With verbose output
    python -m src.main paper.pdf -o ./output -v

    # Specify max debug attempts
    python -m src.main paper.pdf -o ./output --max-retries 3

    # Without Docker (use subprocess)
    python -m src.main paper.pdf -o ./output --no-docker
        """,
    )

    parser.add_argument(
        "input",
        nargs="?",
        help="Path to input PDF file",
    )

    parser.add_argument(
        "--input", "-i",
        dest="input_flag",
        help="Path to input PDF file (alternative)",
    )

    parser.add_argument(
        "--output", "-o",
        default="./output",
        help="Output directory for generated code (default: ./output)",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--no-docker",
        action="store_true",
        help="Disable Docker execution (use subprocess instead)",
    )

    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Maximum debug/retry attempts (default: 2)",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="Paper2Code v0.1.0 (MVP)",
    )

    return parser.parse_args()


def print_banner():
    """Print welcome banner."""
    banner = """
+===============================================================+
|                         Paper2Code                             |
|        Scientific Paper -> Executable Python Code              |
|                                                                 |
|                        MVP v0.1.0                               |
+===============================================================+
"""
    console.print(banner, style="bold blue")


def print_step(step: str, status: str = "running"):
    """Print a workflow step with status."""
    icons = {
        "running": "[yellow]...[/yellow]",
        "success": "[green][OK][/green]",
        "failed": "[red][X][/red]",
    }
    icon = icons.get(status, "-")
    console.print(f"  {icon} {step}")


def print_summary(final_state: dict):
    """Print execution summary as a table."""
    console.print("\n")

    # Create summary table
    table = Table(title="Execution Summary", show_header=True, header_style="bold magenta")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    # Status
    status = final_state.get("status", "unknown")
    status_style = "green" if status == "success" else "red"
    table.add_row("Status", f"[{status_style}]{status}[/{status_style}]")

    # Paper info
    if final_state.get("paper_summary"):
        summary = final_state["paper_summary"]
        table.add_row("Paper Title", summary.get("title", "N/A")[:50])
        table.add_row("Sections", str(summary.get("section_count", 0)))

    # Algorithm info
    if final_state.get("main_algorithm"):
        algo = final_state["main_algorithm"]
        table.add_row("Algorithm", algo.get("name", "N/A"))

    # Results
    if final_state.get("final_output"):
        output = final_state["final_output"]
        table.add_row("Files Generated", str(output.get("file_count", 0)))
        table.add_row("Debug Attempts", str(output.get("debug_attempts", 0)))
        table.add_row("Tokens Used", str(output.get("total_tokens", 0)))

        if output.get("output_path"):
            table.add_row("Output Path", output["output_path"])

    console.print(table)

    # Print execution output if available
    if final_state.get("execution_result"):
        result = final_state["execution_result"]
        if result.get("stdout"):
            console.print("\n[bold]Execution Output:[/bold]")
            console.print(Panel(result["stdout"][:1000], title="stdout"))

        if result.get("stderr") and final_state.get("status") != "success":
            console.print("\n[bold red]Errors:[/bold red]")
            console.print(Panel(result["stderr"][:500], title="stderr", border_style="red"))


def run_pipeline(
    input_path: str,
    output_dir: str,
    use_docker: bool = True,
    max_retries: int = 2,
    verbose: bool = False,
):
    """
    Run the Paper2Code pipeline.

    Args:
        input_path: Path to input PDF
        output_dir: Output directory
        use_docker: Whether to use Docker
        max_retries: Max debug attempts
        verbose: Verbose output
    """
    # Validate input
    input_path = Path(input_path)
    if not input_path.exists():
        console.print(f"[red]Error: Input file not found: {input_path}[/red]")
        sys.exit(1)

    if not input_path.suffix.lower() == ".pdf":
        console.print(f"[red]Error: Input must be a PDF file, got: {input_path.suffix}[/red]")
        sys.exit(1)

    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold]Input:[/bold] {input_path}")
    console.print(f"[bold]Output:[/bold] {output_dir}")
    console.print(f"[bold]Docker:[/bold] {'Enabled' if use_docker else 'Disabled'}")
    console.print(f"[bold]Max Retries:[/bold] {max_retries}\n")

    # Initialize orchestrator
    try:
        orchestrator = Paper2CodeOrchestrator(
            use_docker=use_docker,
            max_debug_attempts=max_retries,
        )
    except Exception as e:
        console.print(f"[red]Error initializing orchestrator: {e}[/red]")
        console.print("[yellow]Tip: Make sure ANTHROPIC_API_KEY is set in .env file[/yellow]")
        sys.exit(1)

    # Run pipeline with progress
    if verbose:
        # Streaming mode - show each step
        console.print("[bold]Running pipeline:[/bold]\n")

        final_state = None
        for state_update in orchestrator.run_step_by_step(
            paper_path=str(input_path),
            output_dir=str(output_dir),
        ):
            # Get the node name and state
            for node_name, state in state_update.items():
                if state is None:
                    continue
                if isinstance(state, dict):
                    final_state = state  # Keep track of last valid state
                    step = state.get("current_step", node_name)
                    status = state.get("status", "")

                    if status == "failed":
                        print_step(step, "failed")
                    elif "success" in step.lower() or "complete" in step.lower():
                        print_step(step, "success")
                    else:
                        print_step(step, "running")

    else:
        # Simple mode without unicode spinner
        console.print("[cyan]Processing paper...[/cyan]")

        final_state = orchestrator.run(
            paper_path=str(input_path),
            output_dir=str(output_dir),
            verbose=False,
        )

        console.print("[cyan]Processing complete.[/cyan]")

    # Print summary
    if final_state is None:
        console.print("\n[bold red]Pipeline failed - no result returned[/bold red]")
        return 1

    print_summary(final_state)

    # Exit with appropriate code
    if final_state.get("status") == "success":
        console.print("\n[bold green]Pipeline completed successfully![/bold green]")
        return 0
    else:
        console.print("\n[bold red]Pipeline failed.[/bold red]")
        if final_state.get("error_message"):
            console.print(f"[red]Error: {final_state['error_message']}[/red]")
        return 1


def main():
    """Main entry point."""
    args = parse_args()

    # Get input path
    input_path = args.input or args.input_flag
    if not input_path:
        console.print("[red]Error: Input PDF file is required[/red]")
        console.print("Usage: python -m src.main --input paper.pdf --output ./output")
        sys.exit(1)

    # Print banner
    print_banner()

    # Check config
    try:
        config = get_config()
        if not config.llm.api_key:
            console.print("[red]Error: ANTHROPIC_API_KEY not set[/red]")
            console.print("[yellow]Please set ANTHROPIC_API_KEY in your .env file[/yellow]")
            sys.exit(1)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not load config: {e}[/yellow]")

    # Run pipeline
    exit_code = run_pipeline(
        input_path=input_path,
        output_dir=args.output,
        use_docker=not args.no_docker,
        max_retries=args.max_retries,
        verbose=args.verbose,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
