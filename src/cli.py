"""CLI display functions using Rich library."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from typing import Dict

console = Console()


def print_header(message: str):
    """Print section header."""
    console.print(f"\n[bold cyan]{message}[/bold cyan]")


def print_success(message: str):
    """Print success message."""
    console.print(f"[green][OK][/green] {message}")


def print_error(message: str):
    """Print error message."""
    console.print(f"[bold red][ERROR]:[/bold red] {message}")


def print_info(message: str):
    """Print info message."""
    console.print(f"[dim]{message}[/dim]")


def display_results(solution: Dict):
    """Display optimization results in rich tables.

    Args:
        solution: Solution dictionary from solver
    """
    console.print()

    # Facility location panel
    console.print(Panel.fit(
        f"[bold]Optimal Facility Location:[/bold] [cyan]{solution['facility_location']}[/cyan]",
        border_style="green"
    ))

    console.print()

    # Production summary
    console.print(f"[bold cyan]Production Summary:[/bold cyan]")

    # Display selected port(s)
    ports = solution['selected_ports']
    if len(ports) == 1:
        console.print(f"  Selected Port: {ports[0]}")
    elif len(ports) > 1:
        console.print(f"  Selected Ports: {', '.join(ports)}")

    console.print(f"  Total Finished Product Produced: {solution['total_finished_product_tons']:,.2f} tons")
    console.print(f"  Total Raw Material Consumed: {solution['total_raw_material_tons']:,.2f} tons")
    console.print(f"  Average Yield Factor: {solution['avg_yield_factor']:.2%}")

    console.print()

    # Cost breakdown table
    table = Table(title="Cost Breakdown", show_header=True, title_style="bold cyan")
    table.add_column("Component", style="cyan")
    table.add_column("Total ($)", justify="right")
    table.add_column("Per Ton ($/t)", justify="right")
    table.add_column("% of Total", justify="right")

    costs = solution['costs']
    total_cost = costs['total_cost']

    table.add_row(
        "Raw Materials (avg)",
        f"${costs['raw_material_total']:,.2f}",
        f"${costs['raw_material_per_ton']:.2f}",
        f"{costs['raw_material_total']/total_cost*100:.1f}%"
    )
    table.add_row(
        "Inbound Freight",
        f"${costs['inbound_freight_total']:,.2f}",
        f"${costs['inbound_freight_per_ton']:.2f}",
        f"{costs['inbound_freight_total']/total_cost*100:.1f}%"
    )
    table.add_row(
        "Outbound Freight",
        f"${costs['outbound_freight_total']:,.2f}",
        f"${costs['outbound_freight_per_ton']:.2f}",
        f"{costs['outbound_freight_total']/total_cost*100:.1f}%"
    )
    table.add_row(
        "Port Operations",
        f"${costs['port_operational_total']:,.2f}",
        f"${costs['port_operational_per_ton']:.2f}",
        f"{costs['port_operational_total']/total_cost*100:.1f}%"
    )
    table.add_row(
        "Sea Freight",
        f"${costs['sea_freight_total']:,.2f}",
        f"${costs['sea_freight_per_ton']:.2f}",
        f"{costs['sea_freight_total']/total_cost*100:.1f}%"
    )
    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]${total_cost:,.2f}[/bold]",
        f"[bold]${total_cost/solution['total_finished_product_tons']:.2f}[/bold]",
        "[bold]100.0%[/bold]"
    )

    console.print(table)
    console.print()

    # Combined sourcing breakdown matrix
    sourcing_table = Table(title="Raw Material Sourcing Breakdown", show_header=True, title_style="bold cyan")
    sourcing_table.add_column("Collection Point", style="cyan", no_wrap=True)
    sourcing_table.add_column("Total (t)", justify="right")
    sourcing_table.add_column("Mat A", justify="right")
    sourcing_table.add_column("Mat B", justify="right")
    sourcing_table.add_column("Mat C", justify="right")
    sourcing_table.add_column("Mat D", justify="right")
    sourcing_table.add_column("Mat E", justify="right")
    sourcing_table.add_column("% Total", justify="right")

    # Build source-by-material matrix from procurement details
    facility = solution['facility_location']
    source_material_matrix = {}

    for (s1, s2, m), qty in solution['procurement_details'].items():
        if s2 == facility:  # Only materials going to the facility
            if s1 not in source_material_matrix:
                source_material_matrix[s1] = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'total': 0}
            source_material_matrix[s1][m] += qty
            source_material_matrix[s1]['total'] += qty

    # Sort sources by total volume
    sorted_sources = sorted(
        source_material_matrix.items(),
        key=lambda x: x[1]['total'],
        reverse=True
    )

    total_raw = solution['total_raw_material_tons']

    # Add rows for each source
    for source, materials in sorted_sources:
        source_total = materials['total']
        source_pct = (source_total / total_raw * 100) if total_raw > 0 else 0

        sourcing_table.add_row(
            source,
            f"{source_total:,.0f}",
            f"{materials['A']:,.0f}" if materials['A'] > 0.5 else "-",
            f"{materials['B']:,.0f}" if materials['B'] > 0.5 else "-",
            f"{materials['C']:,.0f}" if materials['C'] > 0.5 else "-",
            f"{materials['D']:,.0f}" if materials['D'] > 0.5 else "-",
            f"{materials['E']:,.0f}" if materials['E'] > 0.5 else "-",
            f"{source_pct:.1f}%"
        )

    # Add separator and totals row
    sourcing_table.add_section()

    # Calculate totals by material type
    totals_by_type = {
        'A': solution['raw_material_by_type'].get('RawMaterialA', 0),
        'B': solution['raw_material_by_type'].get('RawMaterialB', 0),
        'C': solution['raw_material_by_type'].get('RawMaterialC', 0),
        'D': solution['raw_material_by_type'].get('RawMaterialD', 0),
        'E': solution['raw_material_by_type'].get('RawMaterialE', 0)
    }

    sourcing_table.add_row(
        "[bold]TOTAL BY TYPE[/bold]",
        f"[bold]{total_raw:,.0f}[/bold]",
        f"[bold]{totals_by_type['A']:,.0f}[/bold]",
        f"[bold]{totals_by_type['B']:,.0f}[/bold]",
        f"[bold]{totals_by_type['C']:,.0f}[/bold]",
        f"[bold]{totals_by_type['D']:,.0f}[/bold]",
        f"[bold]{totals_by_type['E']:,.0f}[/bold]",
        "[bold]100.0%[/bold]"
    )

    # Add percentage row
    sourcing_table.add_row(
        "[dim]% of Total[/dim]",
        "[dim]100.0%[/dim]",
        f"[dim]{totals_by_type['A']/total_raw*100:.1f}%[/dim]" if total_raw > 0 else "[dim]0.0%[/dim]",
        f"[dim]{totals_by_type['B']/total_raw*100:.1f}%[/dim]" if total_raw > 0 else "[dim]0.0%[/dim]",
        f"[dim]{totals_by_type['C']/total_raw*100:.1f}%[/dim]" if total_raw > 0 else "[dim]0.0%[/dim]",
        f"[dim]{totals_by_type['D']/total_raw*100:.1f}%[/dim]" if total_raw > 0 else "[dim]0.0%[/dim]",
        f"[dim]{totals_by_type['E']/total_raw*100:.1f}%[/dim]" if total_raw > 0 else "[dim]0.0%[/dim]",
        ""
    )

    console.print(sourcing_table)
    console.print()

    # Solver performance
    console.print(f"[dim]Solve Time: {solution['solve_time_seconds']:.2f} seconds[/dim]")
    console.print()


def show_welcome() -> None:
    """Display welcome banner with project branding."""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]🌲 LOGISTICS OPTIMIZER[/bold cyan]\n\n"
        "This tool will find the optimal facility location to minimize\n"
        "total logistics costs for finished product production.",
        border_style="cyan"
    ))
    console.print()


def confirm_start() -> bool:
    """
    Interactive prompt: Ask user if ready to start optimization.

    Returns:
        True if user confirms, False otherwise
    """
    return Confirm.ask(
        "📊 [bold]Ready to load data and begin optimization?[/bold]",
        default=True
    )


def confirm_solve() -> bool:
    """
    Interactive prompt: Ask user if ready to solve optimization model.

    Returns:
        True if user confirms, False otherwise
    """
    return Confirm.ask(
        "🚀 [bold]Ready to solve optimization problem?[/bold]",
        default=True
    )


def show_problem_summary(data) -> None:
    """
    Display problem summary parameters before optimization.

    Args:
        data: OptimizationData object with loaded parameters
    """
    console.print("\n[bold]Problem Summary:[/bold]\n")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan")
    table.add_column()

    table.add_row("• Collection Points:", f"{len(data.collection_points)}")
    table.add_row("• Material Types:", "5 (A, B, C, D, E)")
    table.add_row("• Production Target:", f"{data.production_params.target_tons:,.2f} tons")
    table.add_row("• Export Ports:", f"{len(data.ports)}")

    # Show max consumption limits
    max_cons_str = ", ".join([f"{k}:{v:.0%}" for k, v in data.production_params.max_consumption.items()])
    table.add_row("• Max Consumption Limits:", max_cons_str)

    console.print(table)
    console.print()


def show_cancellation() -> None:
    """Display user cancellation message."""
    console.print("\n[yellow]Optimization cancelled by user.[/yellow]\n")


def show_whatif_prompt() -> bool:
    """
    Prompt user to enter what-if scenario analysis mode.

    Returns:
        True if user wants to run what-if scenarios
    """
    console.print()
    console.print("[bold cyan]🎯 What-If Scenario Analysis[/bold cyan]")
    console.print("You can now explore alternative scenarios using natural language questions.\n")

    return Confirm.ask(
        "Would you like to run what-if scenarios?",
        default=True
    )
