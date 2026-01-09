# CLI Architecture Documentation

## Overview

This document provides a complete specification of the **Logistics Optimizer CLI** - an interactive command-line interface built with Python's `rich` library for enhanced terminal UI and `rich.prompt` for user interactions. This architecture can be replicated with 100% accuracy in future applications.

## Technology Stack

### Core Dependencies

```python
# Terminal UI and formatting
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

# Standard library
from typing import Dict
import sys
from pathlib import Path
```

### Package Requirements

```
rich>=13.0.0      # Terminal UI (tables, panels, colored output)
typer>=0.9.0      # CLI framework (not directly used, but available)
pandas>=2.0.0     # Data manipulation
pyomo>=6.7.0      # Optimization modeling
highspy>=1.5.0    # MILP solver
pydantic>=2.0.0   # Data validation
```

## Architecture Pattern

### 1. Module Structure

```
src/
├── cli.py              # UI/presentation layer (180 lines)
├── data_loader.py      # Data acquisition layer
├── model_builder.py    # Business logic layer
├── solver.py           # Computation layer
├── reporter.py         # Report generation layer
└── nl_interface.py     # Natural language interaction layer (optional)

main.py                 # Orchestration entry point (157 lines)
```

### 2. Separation of Concerns

The CLI follows **strict separation of concerns**:

- **cli.py**: ONLY handles presentation (display, user input) - NO business logic
- **main.py**: Orchestrates workflow, error handling, and calls CLI functions
- **Business modules**: Return data structures, never directly print to console

## CLI Module (src/cli.py)

### Global Console Instance

```python
from rich.console import Console

console = Console()
```

**Pattern**: Single global `Console` instance shared across all functions for consistent formatting.

### Function Catalog

#### 1. Welcome Banner

```python
def show_welcome() -> None:
    """Display welcome banner."""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]🌲 LOGISTICS OPTIMIZER[/bold cyan]\n\n"
        "This tool will find the optimal facility location to minimize\n"
        "total logistics costs for finished product production.",
        border_style="cyan"
    ))
    console.print()
```

**Components**:
- `Panel.fit()`: Auto-sized panel with border
- `[bold cyan]`: Rich markup for bold cyan text
- Emoji: `🌲` for visual appeal
- `border_style="cyan"`: Consistent cyan theme
- Blank lines before/after for spacing

#### 2. Confirmation Prompts

```python
def confirm_start() -> bool:
    """
    Interactive prompt: Ask user if ready to start.

    Returns:
        True if user confirms, False otherwise
    """
    return Confirm.ask(
        "📊 [bold]We understood the problem, we have all data ready, let's start?[/bold]",
        default=True
    )
```

**Pattern**:
- `Confirm.ask()`: Returns boolean (Y/n prompt)
- `default=True`: Press Enter accepts default
- Emoji prefix for visual context
- `[bold]` markup for emphasis

**Variant** (for solve confirmation):

```python
def confirm_solve() -> bool:
    """Interactive prompt: Ask user if ready to solve."""
    return Confirm.ask(
        "🚀 [bold]Ready to solve optimization?[/bold]",
        default=True
    )
```

#### 3. Problem Summary Display

```python
def show_problem_summary(data: Dict) -> None:
    """
    Display problem summary to user.

    Args:
        data: Loaded data dictionary
    """
    console.print("\n[bold]Problem Summary:[/bold]\n")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan")
    table.add_column()

    table.add_row("• Collection Points:", f"{len(data['collection_points'])}")
    table.add_row("• Raw material Types:", f"{len(data['raw_material_types'])}")
    table.add_row("• Target Production:", f"{data['target']:,.2f} tons")
    table.add_row("• Export Ports:", f"{len(data['ports'])}")
    table.add_row("• Max Consumption Limits:", f"{data['max_consumption']}")

    console.print(table)
    console.print()
```

**Table Pattern**:
- `show_header=False`: No column headers (label-value pairs)
- `box=None`: No border lines (clean look)
- `padding=(0, 2)`: No vertical padding, 2 spaces horizontal
- First column: Labels with bullet points, cyan style
- Second column: Values with number formatting
- `{value:,.2f}`: Comma thousands separator, 2 decimals
- `{value:.0%}`: Percentage with 0 decimals (50% not 0.50)

#### 4. Results Summary Display

```python
def show_results_summary(solution: Dict) -> None:
    """
    Display optimization results summary.

    Args:
        solution: Solution dictionary from solver
    """
    console.print("\n[bold green]✓ Optimization Complete![/bold green]\n")

    # Main results table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()

    table.add_row(
        "Optimal Facility Location:",
        f"[cyan]{solution['facility_location']}[/cyan]"
    )
    table.add_row(
        "Total Cost:",
        f"[green]${solution['total_cost']:,.2f}[/green]"
    )
    table.add_row(
        "Cost per Ton:",
        f"${solution['total_cost']/solution['total_finished_product']:.2f}/ton"
    )
    table.add_row(
        "Solve Time:",
        f"{solution['solve_time']:.2f} seconds"
    )

    console.print(table)
    console.print()

    # Cost breakdown
    console.print("[bold]Cost Breakdown:[/bold]\n")

    breakdown_table = Table(show_header=True, box=None, padding=(0, 2))
    breakdown_table.add_column("Component", style="cyan")
    breakdown_table.add_column("Amount", justify="right")
    breakdown_table.add_column("% of Total", justify="right")

    components = [
        ("Raw material Purchase", solution['raw_material_cost']),
        ("Inbound Logistics", solution['inbound_freight']),
        ("Outbound Logistics", solution['outbound_freight']),
        ("Port Operations", solution['port_cost']),
    ]

    for name, amount in components:
        pct = (amount / solution['total_cost'] * 100) if solution['total_cost'] > 0 else 0
        breakdown_table.add_row(
            name,
            f"${amount:,.2f}",
            f"{pct:.1f}%"
        )

    console.print(breakdown_table)
    console.print()

    # Raw material usage
    console.print("[bold]Raw material Consumption:[/bold]\n")

    raw_material_table = Table(show_header=True, box=None, padding=(0, 2))
    raw_material_table.add_column("Type", style="cyan")
    raw_material_table.add_column("Tons", justify="right")
    raw_material_table.add_column("% of Total", justify="right")

    sorted_raw_material = sorted(
        solution['raw_material_by_type'].items(),
        key=lambda x: x[1],
        reverse=True
    )

    for raw_material_type, tons in sorted_raw_material:
        if tons > 0.01:  # Filter out negligible amounts
            pct = (tons / solution['total_raw material'] * 100) if solution['total_raw material'] > 0 else 0
            raw_material_table.add_row(
                raw_material_type,
                f"{tons:,.2f}",
                f"{pct:.1f}%"
            )

    console.print(raw_material_table)
    console.print()
```

**Multi-Table Pattern**:
- **Section 1**: Main results (no header, label-value pairs)
- **Section 2**: Cost breakdown (with headers, 3 columns, right-justified numbers)
- **Section 3**: Raw material consumption (with headers, sorted by volume, filtered >0.01)
- `justify="right"`: Align numbers to the right
- Defensive division: `if solution['total_cost'] > 0 else 0`
- Filtering: `if tons > 0.01` removes noise from output

#### 5. Error Display

```python
def show_error(error_message: str) -> None:
    """
    Display error message to user.

    Args:
        error_message: Error message to display
    """
    console.print(f"\n[bold red]✗ Error:[/bold red] {error_message}\n")
```

**Pattern**:
- `[bold red]`: Red for errors
- `✗` symbol: Visual error indicator
- Blank lines for spacing

#### 6. Cancellation Message

```python
def show_cancellation() -> None:
    """Display cancellation message."""
    console.print("\n[yellow]Optimization cancelled by user.[/yellow]\n")
```

**Pattern**:
- `[yellow]`: Warning/info color (not error)
- Simple message, no additional formatting

## Main Orchestration (main.py)

### Entry Point Pattern

```python
def main():
    """
    Main application entry point.

    Workflow:
    1. Display welcome message
    2. Load and validate data
    3. Show problem summary
    4. Build optimization model
    5. Solve model
    6. Display results
    7. Generate markdown report
    """
    try:
        # Step 1: Welcome
        show_welcome()

        # Step 2: Initial confirmation
        if not confirm_start():
            show_cancellation()
            return

        print()

        # Step 3: Load data
        print("[bold]Loading data files...[/bold]")
        try:
            data = load_all_data(data_dir='data')
        except FileNotFoundError as e:
            show_error(f"Data file not found: {e}")
            print("\n[yellow]Make sure all required Excel files are in the data/ directory:[/yellow]")
            print("  • INPUT_RawMaterial_Details.xlsx")
            print("  • INPUT_RawMaterial_Distance_Matrix_And_Freight.xlsx")
            print("  • INPUT_FinishedProd_Distance_Matrix_And_Freight.xlsx")
            print("  • INPUT_Demand_Yield_Limits.xlsx")
            print("  • INPUT_Outbound_Details.xlsx")
            return
        except ValueError as e:
            show_error(f"Data validation failed:\n{e}")
            return
        except Exception as e:
            show_error(f"Unexpected error loading data: {e}")
            return

        # Step 4: Show problem summary
        show_problem_summary(data)

        # Step 5: Solve confirmation
        if not confirm_solve():
            show_cancellation()
            return

        # Step 6: Build model
        try:
            model = build_model(data)
        except Exception as e:
            show_error(f"Failed to build model: {e}")
            return

        # Step 7: Solve optimization
        try:
            solution = solve_optimization(model, solver_name='highs')
        except RuntimeError as e:
            show_error(str(e))
            print("\n[yellow]Troubleshooting tips:[/yellow]")
            print("  • Check that HiGHS solver is installed: pip install highspy")
            print("  • Verify data files have valid values")
            print("  • Check that sufficient raw material is available to meet target")
            return
        except Exception as e:
            show_error(f"Unexpected solver error: {e}")
            return

        # Step 8: Display results
        show_results_summary(solution)

        # Step 9: Generate report
        print("[bold]Generating detailed report...[/bold]")
        try:
            generate_markdown_report(solution, output_path='results/optimization_output.md')
        except Exception as e:
            show_error(f"Failed to generate report: {e}")
            return

        print()
        print("[bold green]✓ Optimization completed successfully![/bold green]\n")

        # Step 10: What-if scenario analysis (interactive)
        from rich.prompt import Confirm
        print("[bold cyan]🎯 What-If Scenario Analysis[/bold cyan]")
        print("You can now ask natural language questions to explore alternative scenarios.\n")

        if Confirm.ask("Would you like to run what-if scenarios?", default=True):
            from src.nl_interface import run_interactive_whatif
            try:
                run_interactive_whatif(
                    baseline_solution=solution,
                    data=data,
                    model=model
                )
            except KeyboardInterrupt:
                print("\n[yellow]What-if analysis interrupted.[/yellow]")
            except Exception as e:
                show_error(f"What-if analysis error: {e}")
                import traceback
                print("\n[dim]Full traceback:[/dim]")
                traceback.print_exc()

    except KeyboardInterrupt:
        print("\n\n[yellow]Interrupted by user.[/yellow]\n")
        return
    except Exception as e:
        show_error(f"Unexpected error: {e}")
        import traceback
        print("\n[dim]Full traceback:[/dim]")
        traceback.print_exc()
        return


if __name__ == "__main__":
    main()
```

### Error Handling Strategy

**Three-Layer Exception Handling**:

1. **Specific Exceptions** (inner try-except blocks):
   - `FileNotFoundError`: Data files missing
   - `ValueError`: Data validation failed
   - `RuntimeError`: Solver errors (infeasibility)
   - Each has custom error message + troubleshooting tips

2. **Generic Exceptions** (per-step):
   - `Exception as e`: Catch unexpected errors
   - Display error and return (graceful degradation)

3. **Outer Catch-All**:
   - `KeyboardInterrupt`: Ctrl+C handling (yellow warning)
   - `Exception`: Ultimate fallback with full traceback

**Pattern**: Every major step wrapped in try-except, early returns prevent cascading failures.

## Natural Language Interface (src/nl_interface.py)

### Interactive What-If Loop

```python
def run_interactive_whatif(baseline_solution: Dict, data: Dict, model=None) -> None:
    """
    Run interactive what-if scenario analysis with natural language queries.

    Args:
        baseline_solution: Baseline optimization solution
        data: Original data dictionary
        model: Original Pyomo model (optional, for reference)
    """
    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[bold red]❌ Error: ANTHROPIC_API_KEY environment variable not set[/bold red]")
        console.print("\nTo use the what-if scenario analysis, you need to set your Claude API key:")
        console.print("  Windows: set ANTHROPIC_API_KEY=your_key_here")
        console.print("  Linux/Mac: export ANTHROPIC_API_KEY=your_key_here")
        console.print("\nGet your API key from: https://console.anthropic.com/")
        return

    # Display welcome message
    _display_welcome(baseline_solution, data)

    scenario_count = 0

    # Main interaction loop
    while True:
        try:
            console.print()
            user_query = Prompt.ask(
                "[bold cyan]Type your question (or 'help' for examples, 'quit' to exit)[/bold cyan]"
            )

            # Check for exit
            if user_query.lower() in ['quit', 'exit', 'q']:
                break

            # Check for help
            if user_query.lower() in ['help', 'h', '?']:
                _display_help(baseline_solution, data)
                continue

            # Parse query with Claude API
            console.print("\n[dim]Parsing query with Claude...[/dim]")

            try:
                parsed = parse_query_with_claude(user_query, baseline_solution, data, api_key)
            except APIConnectionError:
                console.print("[bold red]❌ Could not connect to Claude API[/bold red]")
                console.print("Please check your internet connection and try again.")
                continue
            except APIError as e:
                console.print(f"[bold red]❌ Claude API error: {e}[/bold red]")
                continue

            # Display scenario explanation
            console.print()
            console.print(Panel.fit(
                f"[bold]📋 Scenario Identified[/bold]\n\n{parsed['explanation']}",
                border_style="cyan"
            ))
            console.print()

            # Confirm before running
            if not Confirm.ask("Run this scenario?", default=True):
                console.print("[yellow]Scenario cancelled[/yellow]")
                continue

            # Run scenario and display results...

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted by user[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[bold red]❌ Unexpected error: {e}[/bold red]")
            continue

    # Exit message
    console.print()
    if scenario_count > 0:
        console.print(f"[bold green]Thank you! You ran {scenario_count} scenario(s).[/bold green]")
        console.print(f"Reports saved in [cyan]results/[/cyan] directory.")
    else:
        console.print("[yellow]No scenarios were run.[/yellow]")
    console.print()
```

**Pattern**:
- `while True` loop for continuous interaction
- `Prompt.ask()`: Free-text input (not just Y/n)
- Built-in commands: `quit`, `help`
- Graceful API error handling
- Scenario counter for exit summary

### Welcome Display with Context

```python
def _display_welcome(baseline_solution: Dict, data: Dict) -> None:
    """Display welcome message with example queries."""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]🎯 WHAT-IF SCENARIO ANALYSIS[/bold cyan]\n\n"
        "Ask natural language questions to explore alternative scenarios",
        border_style="cyan"
    ))
    console.print()

    console.print("[bold]Baseline Solution:[/bold]")
    console.print(f"  • Facility: {baseline_solution['facility_location']}")
    console.print(f"  • Total Cost: ${baseline_solution['total_cost']:,.2f}")
    console.print(f"  • Production: {baseline_solution['total_finished_product']:,.2f} tons")
    console.print()

    console.print("[bold]Example Questions:[/bold]")
    console.print("  • \"What is the total cost if the facility is at Wiggins?\"")
    console.print("  • \"What if we change the Port of Mobile to Port of Pascagoula?\"")
    console.print("  • \"What if MaterialE max consumption is 40% instead of 50%?\"")
    console.print("  • \"What if inbound freight costs increase 15%?\"")
    console.print()
```

**Pattern**:
- Show current context (baseline solution)
- Provide concrete examples (not abstract instructions)
- Use bullet points for scannability

### Comprehensive Help Display

```python
def _display_help(baseline_solution: Dict, data: Dict) -> None:
    """Display help information with detailed examples and question categories."""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]📚 HELP - What-If Scenario Analysis[/bold cyan]\n\n"
        "You can ask questions in natural language to explore different scenarios",
        border_style="green"
    ))
    console.print()

    # Show current baseline context
    console.print("[bold]Current Baseline:[/bold]")
    console.print(f"  • Facility: [cyan]{baseline_solution['facility_location']}[/cyan]")
    console.print(f"  • Total Cost: [cyan]${baseline_solution['total_cost']:,.2f}[/cyan]")
    console.print()

    # Question categories with visual separators
    console.print("[bold green]═══════════════════════════════════════════════════════════[/bold green]")
    console.print("[bold]📍 1. FACILITY LOCATION SCENARIOS[/bold]")
    console.print("[dim]Test different facility locations to see cost impacts[/dim]")
    console.print()
    console.print("  Examples:")
    console.print("    • \"What is the total cost if the facility is at Wiggins?\"")
    console.print("    • \"What if we build the facility at Hood_Waynesboro?\"")
    console.print()

    console.print("[bold green]═══════════════════════════════════════════════════════════[/bold green]")
    console.print("[bold]🚢 2. PORT SELECTION SCENARIOS[/bold]")
    console.print("[dim]Change which ports are used for finished product shipping[/dim]")
    console.print()
    console.print("  Examples:")
    console.print("    • \"What if we only use Pascagoula port?\"")
    console.print()

    # ... (more categories)

    console.print("[bold cyan]💡 Tips:[/bold cyan]")
    console.print("  • Ask questions in plain English - the system understands natural language")
    console.print("  • Type [bold]'help'[/bold] anytime to see this message again")
    console.print("  • Type [bold]'quit'[/bold] to exit the what-if analysis")
    console.print()
```

**Pattern**:
- Categorized help with emojis for visual scanning
- Visual separators: `═══` lines
- `[dim]` markup for descriptions
- `[bold]` for category headers
- Nested indentation (2 spaces per level)

## Rich Markup Reference

### Color and Style Tags

```python
# Colors
"[red]text[/red]"           # Red text
"[green]text[/green]"       # Green text
"[cyan]text[/cyan]"         # Cyan text
"[yellow]text[/yellow]"     # Yellow text
"[blue]text[/blue]"         # Blue text

# Styles
"[bold]text[/bold]"         # Bold text
"[dim]text[/dim]"           # Dimmed text
"[italic]text[/italic]"     # Italic text
"[underline]text[/underline]" # Underlined text

# Combined
"[bold red]text[/bold red]" # Bold red text
"[bold cyan]text[/bold cyan]" # Bold cyan text
```

### Number Formatting

```python
# Comma separator
f"{value:,}"                # 1000 → 1,000

# Decimals with comma
f"{value:,.2f}"             # 1234.56 → 1,234.56

# Percentage
f"{value:.0%}"              # 0.5 → 50%
f"{value:.1%}"              # 0.567 → 56.7%

# Currency
f"${value:,.2f}"            # 1234.56 → $1,234.56

# Right-justified
f"{value:>10,.2f}"          # Right-align in 10 chars
```

### Emoji Usage

```python
# Status indicators
"✓"  # Success (green context)
"✗"  # Error (red context)
"❌" # Strong error
"⚠️"  # Warning

# Category icons
"🌲" # Nature/environment
"📊" # Data/analytics
"🚀" # Action/launch
"🎯" # Goals/targets
"📍" # Location
"🚢" # Shipping/ports
"⚙️"  # Settings/config
"💰" # Money/costs
"📦" # Supply/inventory
"📚" # Help/documentation
"💡" # Tips/ideas
```

## Table Patterns

### Pattern 1: Label-Value Pairs (No Headers)

```python
table = Table(show_header=False, box=None, padding=(0, 2))
table.add_column(style="cyan")    # Labels in cyan
table.add_column()                 # Values default style

table.add_row("Label:", "Value")
table.add_row("Label 2:", "Value 2")

console.print(table)
```

**Use Case**: Key metrics, configuration summaries

### Pattern 2: Columnar Data (With Headers)

```python
table = Table(show_header=True, box=None, padding=(0, 2))
table.add_column("Name", style="cyan")
table.add_column("Amount", justify="right")
table.add_column("Percentage", justify="right")

table.add_row("Item 1", "$1,234.56", "45.0%")
table.add_row("Item 2", "$987.65", "36.0%")

console.print(table)
```

**Use Case**: Cost breakdowns, raw material consumption, comparisons

### Pattern 3: Multi-Section Display

```python
# Section 1
console.print("[bold]Section Title:[/bold]\n")
table1 = Table(...)
console.print(table1)
console.print()

# Section 2
console.print("[bold]Another Section:[/bold]\n")
table2 = Table(...)
console.print(table2)
console.print()
```

**Pattern**: Section title → blank line → table → blank line

## Panel Patterns

### Pattern 1: Welcome/Banner

```python
console.print(Panel.fit(
    "[bold cyan]TITLE[/bold cyan]\n\n"
    "Description text that can span\n"
    "multiple lines.",
    border_style="cyan"
))
```

### Pattern 2: Information Display

```python
console.print(Panel.fit(
    f"[bold]📋 Title[/bold]\n\n{dynamic_content}",
    border_style="cyan"
))
```

**Pattern**: Emoji + title, double newline, content

## Prompt Patterns

### Pattern 1: Yes/No Confirmation

```python
from rich.prompt import Confirm

if Confirm.ask("Question text?", default=True):
    # User confirmed
    proceed()
else:
    # User declined
    cancel()
```

**Returns**: `bool` (True/False)
**UI**: `Question text? [Y/n]` (capital Y indicates default)

### Pattern 2: Free Text Input

```python
from rich.prompt import Prompt

user_input = Prompt.ask(
    "[bold cyan]Enter your query[/bold cyan]"
)
```

**Returns**: `str`
**UI**: `Enter your query: ` (cursor waits for input)

## Color Scheme Guidelines

### Semantic Color Usage

- **Cyan**: Primary theme color, titles, data labels
- **Green**: Success, positive results, completion messages
- **Red**: Errors, failures, critical warnings
- **Yellow**: Warnings, cancellations, informational alerts
- **Dim**: Secondary text, help text, metadata

### Consistency Rules

1. **Panels**: Always use `border_style="cyan"` (except help: `"green"`)
2. **Success**: Always use `[bold green]✓` prefix
3. **Errors**: Always use `[bold red]✗` or `❌` prefix
4. **Warnings**: Always use `[yellow]` (not bold)
5. **Data labels**: Always use `style="cyan"` in first column

## Spacing Guidelines

### Vertical Spacing

```python
# Before major sections
console.print()               # Single blank line

# After panels
console.print()               # Single blank line

# Between sections
console.print("\n")           # Explicit newline in string

# Before/after entire CLI flow
console.print()               # Entry padding
# ... content ...
console.print()               # Exit padding
```

### Horizontal Spacing

```python
# Table padding
padding=(0, 2)                # 0 vertical, 2 horizontal

# Indentation levels
"  • Item"                    # 2 spaces for bullets
"    • Sub-item"              # 4 spaces for nested bullets
```

## Replication Checklist

To replicate this CLI in a new project:

### 1. Install Dependencies

```bash
pip install rich>=13.0.0
```

### 2. Create CLI Module

```python
# src/cli.py
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.panel import Panel
from rich.table import Table

console = Console()

# Add functions: show_welcome, confirm_start, show_error, etc.
```

### 3. Create Main Orchestrator

```python
# main.py
from src.cli import *

def main():
    try:
        show_welcome()
        if not confirm_start():
            show_cancellation()
            return

        # Business logic with try-except per step
        # Use show_error() for error display
        # Use show_results_summary() for output

    except KeyboardInterrupt:
        print("\n\n[yellow]Interrupted by user.[/yellow]\n")
        return
    except Exception as e:
        show_error(f"Unexpected error: {e}")
        return

if __name__ == "__main__":
    main()
```

### 4. Follow Patterns

- **Separation of concerns**: CLI module ONLY displays, never computes
- **Consistent error handling**: 3-layer exception strategy
- **Color scheme**: Cyan primary, green success, red error, yellow warning
- **Table patterns**: No headers for label-value, headers for data
- **Spacing**: Blank lines before/after major sections
- **Emoji usage**: Consistent category icons

### 5. Test Interactivity

```python
# Test confirmation
if Confirm.ask("Test?", default=True):
    print("Confirmed")

# Test prompt
name = Prompt.ask("Enter name")
print(f"Hello, {name}")

# Test error display
show_error("This is a test error")
```

## Advanced Patterns

### Progress Indicators

```python
from rich.progress import Progress, SpinnerColumn, TextColumn

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    console=console
) as progress:
    task = progress.add_task("Processing...", total=None)
    # Do work
    progress.update(task, completed=True)
```

**Use Case**: Long-running operations (not used in current implementation, but available)

### Live Display

```python
from rich.live import Live
from rich.table import Table

table = Table()
with Live(table, refresh_per_second=4, console=console):
    # Update table dynamically
    pass
```

**Use Case**: Real-time metric updates

### Syntax Highlighting

```python
from rich.syntax import Syntax

code = Syntax(code_string, "python", theme="monokai")
console.print(code)
```

**Use Case**: Displaying code snippets, SQL queries

## Testing the CLI

### Manual Test Script

```python
# test_cli.py
from src.cli import *

# Test 1: Welcome banner
show_welcome()

# Test 2: Confirmation
result = confirm_start()
print(f"User confirmed: {result}")

# Test 3: Error display
show_error("This is a test error with detailed information")

# Test 4: Table display
test_data = {
    'collection_points': ['A', 'B', 'C'],
    'raw_material_types': ['Type1', 'Type2'],
    'target': 150000.50,
    'ports': ['Port1', 'Port2'],
    'max_consumption': {'A': 1.0, 'E': 0.5}
}
show_problem_summary(test_data)

# Test 5: Results display
test_solution = {
    'facility_location': 'TestLocation',
    'total_cost': 1234567.89,
    'total_finished_product': 150000.00,
    'total_raw material': 200000.00,
    'solve_time': 2.45,
    'raw_material_cost': 500000.00,
    'inbound_freight': 300000.00,
    'outbound_freight': 200000.00,
    'port_cost': 234567.89,
    'raw_material_by_type': {
        'RawMaterialA': 50000.0,
        'RawMaterialB': 75000.0,
        'RawMaterialC': 40000.0,
        'RawMaterialD': 25000.0,
        'RawMaterialE': 10000.0
    }
}
show_results_summary(test_solution)
```

### Expected Output

- ✅ Clean formatting with consistent spacing
- ✅ Colors display correctly (cyan, green, red, yellow)
- ✅ Emojis render properly
- ✅ Tables align correctly
- ✅ Numbers format with commas and decimals
- ✅ Confirmations accept Y/n input
- ✅ No business logic in display functions

## Performance Considerations

- **Rich console**: Minimal overhead, no performance issues
- **Table rendering**: Instant for < 1000 rows
- **Panel rendering**: Instant regardless of content length
- **Prompt interactions**: Blocking (expected for CLI)

## Cross-Platform Compatibility

### Windows

```python
# Windows supports rich colors in:
# - Windows Terminal (full support)
# - PowerShell 7+ (full support)
# - CMD (limited support, fallback to basic colors)
```

### Linux/Mac

```python
# Full support in all modern terminals
# - bash, zsh, fish
# - iTerm2, Terminal.app
# - GNOME Terminal, Konsole
```

### Fallback Handling

Rich automatically detects terminal capabilities and degrades gracefully:
- **No color support**: Falls back to plain text
- **No emoji support**: Uses ASCII alternatives
- **Narrow terminal**: Wraps content automatically

## Summary

This CLI architecture provides:

1. **Clean separation**: Presentation (CLI) vs. business logic (modules)
2. **Consistent UX**: Color scheme, spacing, interaction patterns
3. **Robust error handling**: 3-layer exception strategy
4. **Rich interactivity**: Confirmations, prompts, live updates
5. **Professional appearance**: Tables, panels, formatting
6. **100% replicable**: All patterns documented with code examples

Follow these patterns to create a professional, user-friendly CLI for any optimization, data processing, or analysis application.
