"""Natural language what-if scenario interface using Claude API."""

import os
import json
import copy
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import re
from datetime import datetime

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.panel import Panel
from rich.table import Table

from .data_loader import OptimizationData, CollectionPoint, ProductionParameters, check_production_feasibility
from .model_builder import build_facility_location_model
from .solver import solve_optimization
from .reporter import generate_markdown_report
from .cli import print_error, print_success, print_info

console = Console()


def run_interactive_whatif(
    baseline_solution: Dict,
    baseline_data: OptimizationData,
    baseline_model = None
) -> None:
    """
    Run interactive what-if scenario analysis with natural language queries.

    Args:
        baseline_solution: Baseline optimization solution dictionary
        baseline_data: Original OptimizationData object
        baseline_model: Original Pyomo model (optional, for reference)
    """
    # Check for anthropic package
    try:
        from anthropic import Anthropic, APIError, APIConnectionError
    except ImportError:
        console.print("[bold red]❌ Error: anthropic package not installed[/bold red]")
        console.print("\n[yellow]To use the what-if scenario analysis, install the anthropic package:[/yellow]")
        console.print("  [cyan]pip install anthropic[/cyan]")
        console.print("\nThen set your API key:")
        console.print("  [cyan]Windows:[/cyan] set ANTHROPIC_API_KEY=your_key_here")
        console.print("  [cyan]Linux/Mac:[/cyan] export ANTHROPIC_API_KEY=your_key_here")
        console.print("\nGet your API key from: [cyan]https://console.anthropic.com/[/cyan]")
        return

    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[bold red]❌ Error: ANTHROPIC_API_KEY environment variable not set[/bold red]")
        console.print("\n[yellow]To use the what-if scenario analysis, you need to set your Claude API key:[/yellow]")
        console.print("  [cyan]Windows:[/cyan] set ANTHROPIC_API_KEY=your_key_here")
        console.print("  [cyan]Linux/Mac:[/cyan] export ANTHROPIC_API_KEY=your_key_here")
        console.print("\nGet your API key from: [cyan]https://console.anthropic.com/[/cyan]")
        return

    # Display welcome message with baseline context
    _display_welcome(baseline_solution, baseline_data)

    scenario_count = 0

    # Main interaction loop
    while True:
        try:
            console.print()
            user_query = Prompt.ask(
                "[bold cyan]Your question (or 'help', 'list', 'quit')[/bold cyan]"
            )

            # Command handling
            query_lower = user_query.lower().strip()

            if query_lower in ['quit', 'exit', 'q']:
                break

            if query_lower in ['help', 'h', '?']:
                _display_help(baseline_solution, baseline_data)
                continue

            if query_lower in ['list', 'ls']:
                _display_list_resources(baseline_data)
                continue

            # Parse query with Claude API
            console.print("\n[dim]Parsing query with Claude API...[/dim]")

            try:
                parsed = parse_query_with_claude(
                    user_query,
                    baseline_solution,
                    baseline_data,
                    api_key,
                    Anthropic
                )
            except APIConnectionError:
                console.print("[bold red]❌ Could not connect to Claude API[/bold red]")
                console.print("[yellow]Please check your internet connection and try again.[/yellow]")
                continue
            except APIError as e:
                console.print(f"[bold red]❌ Claude API error: {e}[/bold red]")
                continue
            except json.JSONDecodeError:
                console.print("[bold red]❌ Could not parse Claude API response[/bold red]")
                console.print("[yellow]Please try rephrasing your question.[/yellow]")
                continue

            # Display scenario explanation
            console.print()
            console.print(Panel.fit(
                f"[bold]📋 Scenario Identified[/bold]\n\n{parsed['explanation']}",
                border_style="cyan"
            ))
            console.print()

            # Show modifications
            if parsed['modifications']:
                console.print("[bold]Planned Modifications:[/bold]")
                for mod in parsed['modifications']:
                    console.print(f"  • {mod['description']}")
                console.print()
            else:
                console.print("[yellow]No modifications identified. Please rephrase your question.[/yellow]")
                continue

            # Confirm before running
            if not Confirm.ask("Run this scenario?", default=True):
                console.print("[yellow]Scenario cancelled[/yellow]")
                continue

            # Apply modifications
            console.print("\n[dim]Applying scenario modifications...[/dim]")
            try:
                modified_data = apply_scenario_modifications(
                    baseline_data,
                    parsed['modifications']
                )
            except ValueError as e:
                print_error(f"Invalid modification: {e}")
                continue

            # Check production feasibility for both phases
            console.print("[dim]Checking production feasibility...[/dim]")

            # Check Phase 1 feasibility (without MaterialE)
            try:
                feasibility_phase1 = check_production_feasibility(modified_data, exclude_material_e=True)
                console.print(
                    f"[green]✓[/green] Phase 1 feasibility: Target {feasibility_phase1['target']:,.0f} tons is achievable "
                    f"without MaterialE (max: {feasibility_phase1['achievable']:,.0f} tons)"
                )
            except ValueError as e:
                print_error("Phase 1 feasibility check failed (without MaterialE)")
                console.print(f"\n[yellow]{str(e)}[/yellow]\n")
                console.print("[yellow]This production target is too high for materials A-D alone.[/yellow]")
                console.print("[yellow]Try a lower production target or increase raw material availability.[/yellow]")
                continue

            # Check full feasibility (with MaterialE)
            try:
                feasibility_full = check_production_feasibility(modified_data, exclude_material_e=False)
                console.print(
                    f"[green]✓[/green] Full feasibility: Target {feasibility_full['target']:,.0f} tons is achievable "
                    f"with MaterialE (max: {feasibility_full['achievable']:,.0f} tons)"
                )
            except ValueError as e:
                print_error("Full feasibility check failed")
                console.print(f"\n[yellow]{str(e)}[/yellow]\n")
                console.print("[yellow]This scenario is not feasible. Try adjusting the parameters.[/yellow]")
                continue

            # Two-phase optimization (same as baseline)
            # Check if facility is forced by user
            facility_forced = hasattr(modified_data, 'forced_facility') and modified_data.forced_facility

            if facility_forced:
                # Skip Phase 1 if facility is explicitly forced
                console.print(f"[dim]Using forced facility: {modified_data.forced_facility}[/dim]")
                whatif_facility = modified_data.forced_facility
            else:
                # Phase 1: Find optimal facility location (exclude MaterialE)
                console.print("[dim]Phase 1: Finding optimal facility location (excluding MaterialE)...[/dim]")
                try:
                    whatif_model_phase1 = build_facility_location_model(
                        modified_data,
                        exclude_material_e=True
                    )
                    whatif_solution_phase1 = solve_optimization(whatif_model_phase1, time_limit=300)
                    whatif_facility = whatif_solution_phase1['facility_location']
                    console.print(f"[green]✓[/green] Phase 1 complete: Optimal facility is {whatif_facility}")
                except Exception as e:
                    print_error(f"Phase 1 optimization failed: {e}")
                    continue

            # Phase 2: Full optimization with MaterialE included
            console.print("[dim]Phase 2: Full optimization with MaterialE included...[/dim]")
            try:
                whatif_model = build_facility_location_model(
                    modified_data,
                    exclude_material_e=False
                )

                # Fix facility location from Phase 1 (or forced facility)
                for s in whatif_model.Sites:
                    if s == whatif_facility:
                        whatif_model.y[s].fix(1)
                    else:
                        whatif_model.y[s].fix(0)

                # Apply port forcing if specified
                if hasattr(modified_data, 'forced_ports') and modified_data.forced_ports:
                    for s in whatif_model.Sites:
                        for p in whatif_model.Ports:
                            if p not in modified_data.forced_ports:
                                whatif_model.ship_to_port[s, p].fix(0)

            except Exception as e:
                print_error(f"Failed to build Phase 2 model: {e}")
                continue

            console.print("[dim]Solving Phase 2 optimization...[/dim]")
            try:
                whatif_solution = solve_optimization(whatif_model, time_limit=300)
            except RuntimeError as e:
                print_error(f"Optimization failed: {e}")
                console.print("\n[yellow]This scenario may be infeasible:[/yellow]")
                console.print("  • Production target too high for available materials")
                console.print("  • Constraint conflicts (e.g., yield + max consumption)")
                console.print("  • Try adjusting parameters")
                continue
            except Exception as e:
                print_error(f"Solver error: {e}")
                continue

            print_success("Scenario optimization completed!")

            # Compare results
            console.print()
            compare_scenarios(baseline_solution, whatif_solution, parsed)

            # Generate versioned report
            scenario_count += 1
            version_number = get_next_version_number(Path('results'))
            scenario_name = parsed.get('scenario_name', f'What-If Scenario {scenario_count}')
            report_filename = f'whatif_output_v{version_number}.md'

            console.print("\n[dim]Generating detailed report...[/dim]")
            try:
                generate_whatif_report(
                    baseline_solution=baseline_solution,
                    whatif_solution=whatif_solution,
                    modifications=parsed['modifications'],
                    explanation=parsed['explanation'],
                    output_path=f'results/{report_filename}',
                    scenario_name=scenario_name
                )
                print_success(f"Report saved to: results/{report_filename}")
            except Exception as e:
                print_error(f"Failed to generate report: {e}")

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted by user[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[bold red]❌ Unexpected error: {e}[/bold red]")
            import traceback
            console.print("[dim]Traceback:[/dim]")
            traceback.print_exc()
            continue

    # Exit message
    console.print()
    if scenario_count > 0:
        console.print(f"[bold green]Thank you! You ran {scenario_count} scenario(s).[/bold green]")
        console.print(f"Reports saved in [cyan]results/[/cyan] directory.")
    else:
        console.print("[yellow]No scenarios were run.[/yellow]")
    console.print()


def parse_query_with_claude(
    query: str,
    baseline_solution: Dict,
    baseline_data: OptimizationData,
    api_key: str,
    anthropic_class
) -> Dict:
    """
    Parse natural language query using Claude API to extract parameter modifications.

    Args:
        query: User's natural language question
        baseline_solution: Current baseline solution for context
        baseline_data: Current baseline data for context
        api_key: Anthropic API key
        anthropic_class: Anthropic class for creating client

    Returns:
        Dictionary with modifications, explanation, and scenario name

    Raises:
        APIError: If Claude API call fails
        APIConnectionError: If cannot connect to API
        json.JSONDecodeError: If response cannot be parsed
    """
    client = anthropic_class(api_key=api_key)

    # Build context from baseline
    context_info = {
        "facility_location": baseline_solution['facility_location'],
        "total_cost": baseline_solution['costs']['total_cost'],
        "production_target": baseline_data.production_params.target_tons,
        "ports": [p.port_name for p in baseline_data.ports],
        "collection_points": [cp.site_id for cp in baseline_data.collection_points],
        "materials": ['A', 'B', 'C', 'D', 'E'],
        "yield_factors": baseline_data.production_params.yield_factors,
        "max_consumption": baseline_data.production_params.max_consumption
    }

    # Construct prompt for Claude
    system_prompt = """You are an expert logistics optimization analyst. Parse user queries about supply chain scenarios and extract structured parameter modifications.

**Your task**: Convert natural language questions into structured JSON modifications for a logistics optimization model.

**Available Parameters**:
1. production_target - Change production target (tons)
2. facility_location - Force specific facility location (must match site_id exactly)
3. port_selection - Force specific port(s) (must match port names exactly)
4. freight_cost_inbound - Adjust inbound freight costs (percentage multiplier)
5. freight_cost_outbound - Adjust outbound freight costs (percentage multiplier)
6. freight_cost_sea - Adjust sea freight costs (percentage multiplier)
7. yield_factor - Modify material yield factors (specify material A-E)
8. raw_material_availability - Change available volumes (specify site and material)
9. max_consumption - Modify consumption limits (specify material A-E)
10. material_price - Adjust raw material prices (specify site/material or global %)

**Output Format** (JSON):
{
  "modifications": [
    {
      "parameter_type": "production_target",
      "action": "set",
      "value": 200000.0,
      "description": "Change production target to 200,000 tons"
    }
  ],
  "explanation": "Clear explanation of what this scenario tests and expected impacts",
  "scenario_name": "Descriptive scenario name"
}

**Important**:
- For facility/port forcing, use exact names from the context
- For percentage changes, use multipliers (e.g., 1.15 for +15%, 0.85 for -15%)
- If user query is vague, make reasonable assumptions and explain in explanation field
- Always provide clear description for each modification"""

    user_prompt = f"""**Current Baseline Context**:
- Facility Location: {context_info['facility_location']}
- Total Cost: ${context_info['total_cost']:,.2f}
- Production Target: {context_info['production_target']:,.0f} tons
- Available Ports: {', '.join(context_info['ports'])}
- Collection Points: {len(context_info['collection_points'])} sites
- Yield Factors: {', '.join([f'{k}:{v:.2%}' for k, v in context_info['yield_factors'].items()])}
- Max Consumption: {', '.join([f'{k}:{v:.0%}' for k, v in context_info['max_consumption'].items()])}

**User Query**: {query}

**Instructions**: Parse the query and output ONLY valid JSON matching the specified format. Do not include any other text."""

    # Call Claude API
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2000,
        temperature=0.0,  # Deterministic for parsing
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )

    # Extract response text
    response_text = message.content[0].text.strip()

    # Remove markdown code blocks if present
    if response_text.startswith('```'):
        response_text = re.sub(r'^```json?\n?', '', response_text)
        response_text = re.sub(r'\n?```$', '', response_text)

    # Parse JSON
    parsed = json.loads(response_text)

    # Validate required fields
    if 'modifications' not in parsed:
        parsed['modifications'] = []
    if 'explanation' not in parsed:
        parsed['explanation'] = "No explanation provided"
    if 'scenario_name' not in parsed:
        parsed['scenario_name'] = "Custom What-If Scenario"

    return parsed


def apply_scenario_modifications(
    baseline_data: OptimizationData,
    modifications: List[Dict]
) -> OptimizationData:
    """
    Apply parsed modifications to baseline data, returning modified copy.

    Args:
        baseline_data: Original OptimizationData
        modifications: List of modification dictionaries

    Returns:
        Modified OptimizationData (deep copy)

    Raises:
        ValueError: If modification is invalid or references non-existent entity
    """
    # Deep copy to avoid mutating baseline
    modified_data = copy.deepcopy(baseline_data)

    for mod in modifications:
        param_type = mod['parameter_type']
        action = mod['action']
        value = mod['value']

        try:
            if param_type == 'production_target':
                if action == 'set':
                    modified_data.production_params.target_tons = float(value)
                elif action == 'increase':
                    modified_data.production_params.target_tons += float(value)
                elif action == 'decrease':
                    modified_data.production_params.target_tons -= float(value)
                elif action == 'multiply':
                    modified_data.production_params.target_tons *= float(value)

            elif param_type == 'facility_location':
                # Store as metadata for model building
                if not hasattr(modified_data, 'forced_facility'):
                    modified_data.forced_facility = None
                modified_data.forced_facility = value  # site_id string

            elif param_type == 'port_selection':
                # Store as metadata for model building
                if not hasattr(modified_data, 'forced_ports'):
                    modified_data.forced_ports = []
                if isinstance(value, list):
                    modified_data.forced_ports = value
                else:
                    modified_data.forced_ports = [value]

            elif param_type == 'freight_cost_inbound':
                # Multiply all inbound freight costs (including MaterialE special freight)
                multiplier = float(value)
                for key in modified_data.inbound_freight:
                    modified_data.inbound_freight[key] *= multiplier
                modified_data.material_e_freight *= multiplier

            elif param_type == 'freight_cost_outbound':
                # Multiply all outbound freight costs
                multiplier = float(value)
                for key in modified_data.outbound_freight:
                    modified_data.outbound_freight[key] *= multiplier

            elif param_type == 'freight_cost_sea':
                # Multiply all sea freight costs
                multiplier = float(value)
                for port in modified_data.ports:
                    port.sea_freight_cost *= multiplier

            elif param_type == 'yield_factor':
                # Modify yield factor for specific material
                material = mod.get('material', None)
                if not material:
                    raise ValueError("yield_factor modification requires 'material' field")
                if material not in modified_data.production_params.yield_factors:
                    raise ValueError(f"Material {material} not found")

                if action == 'set':
                    modified_data.production_params.yield_factors[material] = float(value)
                elif action == 'multiply':
                    modified_data.production_params.yield_factors[material] *= float(value)

            elif param_type == 'max_consumption':
                # Modify max consumption limit for specific material
                material = mod.get('material', None)
                if not material:
                    raise ValueError("max_consumption modification requires 'material' field")
                if material not in modified_data.production_params.max_consumption:
                    raise ValueError(f"Material {material} not found in max_consumption")

                if action == 'set':
                    modified_data.production_params.max_consumption[material] = float(value)

            elif param_type == 'raw_material_availability':
                # Modify availability for specific site/material
                site = mod.get('site', None)
                material = mod.get('material', None)
                if not site or not material:
                    raise ValueError("raw_material_availability requires 'site' and 'material' fields")

                # Find collection point
                cp = next((c for c in modified_data.collection_points if c.site_id == site), None)
                if not cp:
                    raise ValueError(f"Collection point {site} not found")
                if material not in cp.volumes:
                    raise ValueError(f"Material {material} not found at site {site}")

                if action == 'set':
                    cp.volumes[material] = float(value)
                elif action == 'multiply':
                    cp.volumes[material] *= float(value)

            elif param_type == 'material_price':
                # Modify prices (site-specific or global)
                site = mod.get('site', None)
                material = mod.get('material', None)

                if site and material:
                    # Site-specific material price
                    cp = next((c for c in modified_data.collection_points if c.site_id == site), None)
                    if not cp:
                        raise ValueError(f"Collection point {site} not found")
                    if material not in cp.prices:
                        raise ValueError(f"Material {material} not found at site {site}")

                    if action == 'set':
                        cp.prices[material] = float(value)
                    elif action == 'multiply':
                        cp.prices[material] *= float(value)
                else:
                    # Global price adjustment (all sites, all materials)
                    multiplier = float(value)
                    for cp in modified_data.collection_points:
                        for mat in cp.prices:
                            cp.prices[mat] *= multiplier

            else:
                raise ValueError(f"Unknown parameter type: {param_type}")

        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"Error applying modification {mod['description']}: {e}")

    return modified_data


def _generate_scenario_summary(
    baseline: Dict,
    whatif: Dict,
    baseline_ports: set,
    whatif_ports: set
) -> None:
    """
    Generate natural language summary of scenario comparison.

    Args:
        baseline: Baseline solution dictionary
        whatif: What-if solution dictionary
        baseline_ports: Set of baseline ports
        whatif_ports: Set of what-if ports
    """
    console.print("[bold cyan]📊 Key Insights:[/bold cyan]\n")

    # Extract key metrics
    baseline_fac = baseline['facility_location']
    whatif_fac = whatif['facility_location']
    baseline_cost = baseline['costs']['total_cost']
    whatif_cost = whatif['costs']['total_cost']
    cost_diff = whatif_cost - baseline_cost
    cost_pct = (cost_diff / baseline_cost * 100) if baseline_cost > 0 else 0
    baseline_prod = baseline['total_finished_product_tons']
    whatif_prod = whatif['total_finished_product_tons']
    prod_diff = whatif_prod - baseline_prod
    prod_pct = (prod_diff / baseline_prod * 100) if baseline_prod > 0 else 0
    baseline_cpt = baseline_cost / baseline_prod
    whatif_cpt = whatif_cost / whatif_prod
    cpt_diff = whatif_cpt - baseline_cpt

    # Cost component changes
    components = {
        "Raw Materials": 'raw_material_total',
        "Inbound Freight": 'inbound_freight_total',
        "Outbound Freight": 'outbound_freight_total',
        "Port Operations": 'port_operational_total',
        "Sea Freight": 'sea_freight_total'
    }
    cost_changes = []
    for name, key in components.items():
        base_val = baseline['costs'][key]
        what_val = whatif['costs'][key]
        diff = what_val - base_val
        pct = (diff / base_val * 100) if base_val > 0 else 0
        cost_changes.append((name, diff, pct))
    cost_changes.sort(key=lambda x: abs(x[1]), reverse=True)

    # Paragraph 1: Facility location and total cost impact
    if baseline_fac == whatif_fac:
        para1 = (
            f"The optimal facility location remains [cyan]{baseline_fac}[/cyan], "
            f"confirming that the network structure is still appropriate. "
        )
    else:
        para1 = (
            f"The optimal facility location has changed from [cyan]{baseline_fac}[/cyan] "
            f"to [cyan]{whatif_fac}[/cyan], indicating a strategic shift in network configuration. "
        )

    # Add cost impact
    if cost_diff < 0:
        cost_millions = abs(cost_diff) / 1_000_000
        para1 += (
            f"[green]Total costs have decreased by approximately ${cost_millions:.1f} million "
            f"({abs(cost_pct):.1f}%), generating nearly ${cost_millions:.0f} million in savings.[/green]"
        )
    elif cost_diff > 0:
        cost_millions = cost_diff / 1_000_000
        para1 += (
            f"[red]Total costs have increased by approximately ${cost_millions:.1f} million "
            f"({cost_pct:.1f}%), adding ${cost_millions:.0f} million in additional costs.[/red]"
        )
    else:
        para1 += "Total costs remain unchanged."

    console.print(para1)
    console.print()

    # Paragraph 2: Production changes and cost drivers
    if abs(prod_diff) > 1:
        if prod_diff < 0:
            prod_word = "reduction"
        else:
            prod_word = "increase"

        para2 = (
            f"This {'improvement is' if cost_diff < 0 else 'change occurs'} alongside "
            f"a {abs(prod_pct):.1f}% {prod_word} in production volume, "
            f"with output {'decreasing' if prod_diff < 0 else 'increasing'} to "
            f"{whatif_prod:,.0f} tons. "
        )
    else:
        para2 = ""

    # Add top cost drivers
    significant_changes = [(name, diff, pct) for name, diff, pct in cost_changes if abs(diff) > 100]
    if len(significant_changes) >= 2:
        top1_name, top1_diff, top1_pct = significant_changes[0]
        top2_name, top2_diff, top2_pct = significant_changes[1]

        if para2:
            para2 += (
                f"The largest {'savings' if top1_diff < 0 else 'cost'} drivers are "
                f"{top1_name}, {'down' if top1_diff < 0 else 'up'} ${abs(top1_diff)/1_000_000:.1f} million "
                f"({abs(top1_pct):.1f}%), "
                f"and {top2_name}, {'down' if top2_diff < 0 else 'up'} ${abs(top2_diff)/1_000_000:.1f} million "
                f"({abs(top2_pct):.1f}%)."
            )
        else:
            para2 = (
                f"The largest {'savings' if top1_diff < 0 else 'cost'} drivers are "
                f"{top1_name}, {'down' if top1_diff < 0 else 'up'} ${abs(top1_diff)/1_000_000:.1f} million "
                f"({abs(top1_pct):.1f}%), "
                f"and {top2_name}, {'down' if top2_diff < 0 else 'up'} ${abs(top2_diff)/1_000_000:.1f} million "
                f"({abs(top2_pct):.1f}%)."
            )

        if para2:
            console.print(para2)
            console.print()

    # Paragraph 3: Unit cost efficiency
    if abs(cpt_diff) > 0.1:
        if cpt_diff < 0:
            para3 = (
                f"[green]Overall efficiency has improved, with cost per ton reduced by ${abs(cpt_diff):.2f}, "
                f"declining from ${baseline_cpt:.2f} to ${whatif_cpt:.2f}, "
                f"indicating a stronger cost position{' despite lower production' if prod_diff < 0 else ''}.[/green]"
            )
        else:
            para3 = (
                f"[red]Cost per ton has increased by ${cpt_diff:.2f}, "
                f"rising from ${baseline_cpt:.2f} to ${whatif_cpt:.2f}, "
                f"indicating higher unit costs in this scenario.[/red]"
            )

        console.print(para3)
        console.print()

    # Additional: Port changes (if any)
    if baseline_ports != whatif_ports:
        removed = baseline_ports - whatif_ports
        added = whatif_ports - baseline_ports
        if removed and added:
            port_note = (
                f"Port selection has changed, with {', '.join(sorted(removed))} removed "
                f"and {', '.join(sorted(added))} added to the network."
            )
        elif added:
            port_note = f"Port selection expanded to include {', '.join(sorted(added))}."
        elif removed:
            port_note = f"Port selection narrowed, removing {', '.join(sorted(removed))}."

        console.print(port_note)
        console.print()


def compare_scenarios(
    baseline: Dict,
    whatif: Dict,
    parsed_scenario: Dict
) -> None:
    """
    Display side-by-side comparison of baseline vs what-if scenario.

    Args:
        baseline: Baseline solution dictionary
        whatif: What-if solution dictionary
        parsed_scenario: Parsed scenario with modifications
    """
    console.print("[bold cyan]Scenario Comparison:[/bold cyan]\n")

    # Main metrics comparison table
    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("Metric", style="cyan")
    table.add_column("Baseline", justify="right")
    table.add_column("What-If", justify="right")
    table.add_column("Change", justify="right")

    # Facility location
    baseline_fac = baseline['facility_location']
    whatif_fac = whatif['facility_location']
    change_fac = "✓ Same" if baseline_fac == whatif_fac else f"→ {whatif_fac}"
    table.add_row(
        "Facility Location",
        baseline_fac,
        whatif_fac,
        change_fac
    )

    # Total cost
    baseline_cost = baseline['costs']['total_cost']
    whatif_cost = whatif['costs']['total_cost']
    cost_diff = whatif_cost - baseline_cost
    cost_pct = (cost_diff / baseline_cost * 100) if baseline_cost > 0 else 0
    color = "green" if cost_diff < 0 else "red" if cost_diff > 0 else "yellow"
    table.add_row(
        "Total Cost",
        f"${baseline_cost:,.2f}",
        f"${whatif_cost:,.2f}",
        f"[{color}]{cost_diff:+,.2f} ({cost_pct:+.1f}%)[/{color}]"
    )

    # Cost per ton
    baseline_cpt = baseline_cost / baseline['total_finished_product_tons']
    whatif_cpt = whatif_cost / whatif['total_finished_product_tons']
    cpt_diff = whatif_cpt - baseline_cpt
    cpt_pct = (cpt_diff / baseline_cpt * 100) if baseline_cpt > 0 else 0
    color = "green" if cpt_diff < 0 else "red" if cpt_diff > 0 else "yellow"
    table.add_row(
        "Cost per Ton",
        f"${baseline_cpt:.2f}",
        f"${whatif_cpt:.2f}",
        f"[{color}]{cpt_diff:+.2f} ({cpt_pct:+.1f}%)[/{color}]"
    )

    # Production
    baseline_prod = baseline['total_finished_product_tons']
    whatif_prod = whatif['total_finished_product_tons']
    prod_diff = whatif_prod - baseline_prod
    prod_pct = (prod_diff / baseline_prod * 100) if baseline_prod > 0 else 0
    table.add_row(
        "Production (tons)",
        f"{baseline_prod:,.2f}",
        f"{whatif_prod:,.2f}",
        f"{prod_diff:+,.2f} ({prod_pct:+.1f}%)"
    )

    # Raw material consumption
    baseline_raw = baseline['total_raw_material_tons']
    whatif_raw = whatif['total_raw_material_tons']
    raw_diff = whatif_raw - baseline_raw
    raw_pct = (raw_diff / baseline_raw * 100) if baseline_raw > 0 else 0
    table.add_row(
        "Raw Material (tons)",
        f"{baseline_raw:,.2f}",
        f"{whatif_raw:,.2f}",
        f"{raw_diff:+,.2f} ({raw_pct:+.1f}%)"
    )

    # Avg yield factor
    baseline_yield = baseline['avg_yield_factor']
    whatif_yield = whatif['avg_yield_factor']
    yield_diff = whatif_yield - baseline_yield
    table.add_row(
        "Avg Yield Factor",
        f"{baseline_yield:.2%}",
        f"{whatif_yield:.2%}",
        f"{yield_diff:+.2%}"
    )

    console.print(table)
    console.print()

    # Cost breakdown comparison
    console.print("[bold]Cost Component Changes:[/bold]\n")

    cost_table = Table(show_header=True, box=None, padding=(0, 2))
    cost_table.add_column("Component", style="cyan")
    cost_table.add_column("Baseline ($)", justify="right")
    cost_table.add_column("Base ($/t)", justify="right")
    cost_table.add_column("What-If ($)", justify="right")
    cost_table.add_column("W-I ($/t)", justify="right")
    cost_table.add_column("Change", justify="right")

    # Get volumes for per-ton calculations
    baseline_raw = baseline['total_raw_material_tons']
    whatif_raw = whatif['total_raw_material_tons']
    baseline_prod = baseline['total_finished_product_tons']
    whatif_prod = whatif['total_finished_product_tons']

    components = [
        ("Raw Materials", 'raw_material_total', 'raw'),
        ("Inbound Freight", 'inbound_freight_total', 'raw'),
        ("Outbound Freight", 'outbound_freight_total', 'product'),
        ("Port Operations", 'port_operational_total', 'product'),
        ("Sea Freight", 'sea_freight_total', 'product')
    ]

    for name, key, basis in components:
        base_val = baseline['costs'][key]
        what_val = whatif['costs'][key]
        diff = what_val - base_val
        pct = (diff / base_val * 100) if base_val > 0 else 0
        color = "green" if diff < 0 else "red" if diff > 0 else "yellow"

        # Calculate per-ton based on component type
        if basis == 'raw':
            base_per_ton = base_val / baseline_raw if baseline_raw > 0 else 0
            what_per_ton = what_val / whatif_raw if whatif_raw > 0 else 0
        else:  # product
            base_per_ton = base_val / baseline_prod if baseline_prod > 0 else 0
            what_per_ton = what_val / whatif_prod if whatif_prod > 0 else 0

        cost_table.add_row(
            name,
            f"${base_val:,.2f}",
            f"${base_per_ton:.2f}",
            f"${what_val:,.2f}",
            f"${what_per_ton:.2f}",
            f"[{color}]{diff:+,.2f} ({pct:+.1f}%)[/{color}]"
        )

    console.print(cost_table)
    console.print()

    # Raw material consumption breakdown by type
    console.print("[bold]Raw Material Consumption Changes:[/bold]\n")

    material_table = Table(show_header=True, box=None, padding=(0, 2))
    material_table.add_column("Material", style="cyan")
    material_table.add_column("Baseline (tons)", justify="right")
    material_table.add_column("What-If (tons)", justify="right")
    material_table.add_column("Change", justify="right")

    materials = ['A', 'B', 'C', 'D', 'E']
    for mat in materials:
        mat_key = f'RawMaterial{mat}'
        base_val = baseline['raw_material_by_type'].get(mat_key, 0.0)
        what_val = whatif['raw_material_by_type'].get(mat_key, 0.0)
        diff = what_val - base_val
        color = "green" if diff < 0 else "red" if diff > 0 else "yellow"

        material_table.add_row(
            mat_key,
            f"{base_val:,.2f}",
            f"{what_val:,.2f}",
            f"[{color}]{diff:+,.2f}[/{color}]"
        )

    console.print(material_table)
    console.print()

    # Port selection comparison
    baseline_ports = set(baseline['selected_ports'])
    whatif_ports = set(whatif['selected_ports'])

    if baseline_ports != whatif_ports:
        console.print("[bold]Port Selection Changes:[/bold]")
        console.print(f"  Baseline: {', '.join(sorted(baseline_ports))}")
        console.print(f"  What-If:  {', '.join(sorted(whatif_ports))}")
        console.print()

    # Natural language summary
    _generate_scenario_summary(baseline, whatif, baseline_ports, whatif_ports)


def get_next_version_number(results_dir: Path) -> int:
    """
    Scan results directory for existing whatif_output_v*.md files and return next version.

    Args:
        results_dir: Path to results directory

    Returns:
        Next version number (1, 2, 3, ...)
    """
    if not results_dir.exists():
        results_dir.mkdir(parents=True, exist_ok=True)
        return 1

    # Find all whatif_output_v*.md files
    pattern = re.compile(r'whatif_output_v(\d+)\.md')
    max_version = 0

    for file in results_dir.glob('whatif_output_v*.md'):
        match = pattern.match(file.name)
        if match:
            version = int(match.group(1))
            max_version = max(max_version, version)

    return max_version + 1


def generate_whatif_report(
    baseline_solution: Dict,
    whatif_solution: Dict,
    modifications: List[Dict],
    explanation: str,
    output_path: str,
    scenario_name: str
) -> None:
    """
    Generate markdown report comparing baseline to what-if scenario.

    Args:
        baseline_solution: Baseline solution dictionary
        whatif_solution: What-if solution dictionary
        modifications: List of modifications applied
        explanation: Scenario explanation from Claude
        output_path: Path to save report
        scenario_name: Name of scenario
    """
    report = f"""# What-If Scenario Analysis Report

## Scenario: {scenario_name}

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Scenario Description

{explanation}

### Applied Modifications

"""

    for mod in modifications:
        report += f"- **{mod['parameter_type']}**: {mod['description']}\n"

    report += """

---

## Comparison: Baseline vs What-If

### Key Metrics

| Metric | Baseline | What-If | Change | % Change |
|--------|----------|---------|--------|----------|
"""

    # Facility location
    baseline_fac = baseline_solution['facility_location']
    whatif_fac = whatif_solution['facility_location']
    report += f"| Facility Location | {baseline_fac} | {whatif_fac} | {'No Change' if baseline_fac == whatif_fac else 'Changed'} | - |\n"

    # Total cost
    baseline_cost = baseline_solution['costs']['total_cost']
    whatif_cost = whatif_solution['costs']['total_cost']
    cost_diff = whatif_cost - baseline_cost
    cost_pct = (cost_diff / baseline_cost * 100) if baseline_cost > 0 else 0
    report += f"| Total Cost | ${baseline_cost:,.2f} | ${whatif_cost:,.2f} | ${cost_diff:+,.2f} | {cost_pct:+.1f}% |\n"

    # Cost per ton
    baseline_cpt = baseline_cost / baseline_solution['total_finished_product_tons']
    whatif_cpt = whatif_cost / whatif_solution['total_finished_product_tons']
    cpt_diff = whatif_cpt - baseline_cpt
    cpt_pct = (cpt_diff / baseline_cpt * 100) if baseline_cpt > 0 else 0
    report += f"| Cost per Ton | ${baseline_cpt:.2f} | ${whatif_cpt:.2f} | ${cpt_diff:+.2f} | {cpt_pct:+.1f}% |\n"

    # Production
    baseline_prod = baseline_solution['total_finished_product_tons']
    whatif_prod = whatif_solution['total_finished_product_tons']
    prod_diff = whatif_prod - baseline_prod
    prod_pct = (prod_diff / baseline_prod * 100) if baseline_prod > 0 else 0
    report += f"| Production (tons) | {baseline_prod:,.2f} | {whatif_prod:,.2f} | {prod_diff:+,.2f} | {prod_pct:+.1f}% |\n"

    # Raw material
    baseline_raw = baseline_solution['total_raw_material_tons']
    whatif_raw = whatif_solution['total_raw_material_tons']
    raw_diff = whatif_raw - baseline_raw
    raw_pct = (raw_diff / baseline_raw * 100) if baseline_raw > 0 else 0
    report += f"| Raw Material (tons) | {baseline_raw:,.2f} | {whatif_raw:,.2f} | {raw_diff:+,.2f} | {raw_pct:+.1f}% |\n"

    # Yield
    baseline_yield = baseline_solution['avg_yield_factor']
    whatif_yield = whatif_solution['avg_yield_factor']
    yield_diff = whatif_yield - baseline_yield
    report += f"| Avg Yield Factor | {baseline_yield:.2%} | {whatif_yield:.2%} | {yield_diff:+.2%} | - |\n"

    report += """

---

## Cost Breakdown Comparison

| Component | Baseline | What-If | Change | % Change |
|-----------|----------|---------|--------|----------|
"""

    components = [
        ("Raw Materials", 'raw_material_total'),
        ("Inbound Freight", 'inbound_freight_total'),
        ("Outbound Freight", 'outbound_freight_total'),
        ("Port Operations", 'port_operational_total'),
        ("Sea Freight", 'sea_freight_total')
    ]

    for name, key in components:
        base_val = baseline_solution['costs'][key]
        what_val = whatif_solution['costs'][key]
        diff = what_val - base_val
        pct = (diff / base_val * 100) if base_val > 0 else 0
        report += f"| {name} | ${base_val:,.2f} | ${what_val:,.2f} | ${diff:+,.2f} | {pct:+.1f}% |\n"

    report += f"""

---

## What-If Solution Details

### Facility & Ports
- **Facility Location:** {whatif_solution['facility_location']}
- **Selected Ports:** {', '.join(whatif_solution['selected_ports'])}

### Production Summary
- **Total Finished Product Produced:** {whatif_solution['total_finished_product_tons']:,.2f} tons
- **Total Raw Material Consumed:** {whatif_solution['total_raw_material_tons']:,.2f} tons
- **Average Yield Factor:** {whatif_solution['avg_yield_factor']:.2%}

---

## Raw Material Consumption by Type

| Material | Baseline (tons) | What-If (tons) | Change |
|----------|----------------|----------------|--------|
"""

    for mat_type in ['RawMaterialA', 'RawMaterialB', 'RawMaterialC', 'RawMaterialD', 'RawMaterialE']:
        base_tons = baseline_solution['raw_material_by_type'].get(mat_type, 0.0)
        what_tons = whatif_solution['raw_material_by_type'].get(mat_type, 0.0)
        diff = what_tons - base_tons
        report += f"| {mat_type} | {base_tons:,.2f} | {what_tons:,.2f} | {diff:+,.2f} |\n"

    report += """

---

*Report generated by Logistics Optimizer - What-If Analysis*
"""

    # Write to file
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)


def _display_welcome(baseline_solution: Dict, baseline_data: OptimizationData) -> None:
    """Display welcome message for what-if analysis with baseline context."""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]🎯 WHAT-IF SCENARIO ANALYSIS[/bold cyan]\n\n"
        "Ask natural language questions to explore alternative scenarios.\n"
        "Powered by Claude API.",
        border_style="cyan"
    ))
    console.print()

    console.print("[bold]Baseline Solution:[/bold]")
    console.print(f"  • Facility: [cyan]{baseline_solution['facility_location']}[/cyan]")
    console.print(f"  • Total Cost: [cyan]${baseline_solution['costs']['total_cost']:,.2f}[/cyan]")
    console.print(f"  • Production: [cyan]{baseline_solution['total_finished_product_tons']:,.2f} tons[/cyan]")
    console.print(f"  • Ports: [cyan]{', '.join(baseline_solution['selected_ports'])}[/cyan]")
    console.print()

    console.print("[bold]Example Questions:[/bold]")
    console.print("  • \"What if production target increases to 220,000 tons?\"")
    console.print("  • \"What if the facility is forced at SupplierA_City1?\"")
    console.print("  • \"What if inbound freight costs increase by 20%?\"")
    console.print("  • \"What if we only use Port_B?\"")
    console.print("  • \"What if MaterialE yield factor improves to 22%?\"")
    console.print()
    console.print("[dim]Type 'help' for more examples, 'list' to see resources, 'quit' to exit[/dim]")


def _display_help(baseline_solution: Dict, baseline_data: OptimizationData) -> None:
    """Display comprehensive help with categorized examples."""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]📚 HELP - What-If Scenario Analysis[/bold cyan]\n\n"
        "Ask questions in natural language to explore different scenarios",
        border_style="green"
    ))
    console.print()

    console.print("[bold]Current Baseline:[/bold]")
    console.print(f"  • Facility: [cyan]{baseline_solution['facility_location']}[/cyan]")
    console.print(f"  • Total Cost: [cyan]${baseline_solution['costs']['total_cost']:,.2f}[/cyan]")
    console.print(f"  • Production: [cyan]{baseline_solution['total_finished_product_tons']:,.2f} tons[/cyan]")
    console.print()

    console.print("[bold green]═══════════════════════════════════════════════════════════[/bold green]")
    console.print("[bold]📍 1. FACILITY LOCATION SCENARIOS[/bold]")
    console.print("[dim]Test different facility locations to see cost impacts[/dim]")
    console.print()
    console.print("  Examples:")
    console.print("    • \"What if the facility is at SupplierA_City1?\"")
    console.print("    • \"Force facility location to SupplierC_City3\"")
    console.print()

    console.print("[bold green]═══════════════════════════════════════════════════════════[/bold green]")
    console.print("[bold]🚢 2. PORT SELECTION SCENARIOS[/bold]")
    console.print("[dim]Change which ports are used for shipping[/dim]")
    console.print()
    console.print("  Examples:")
    console.print("    • \"What if we only use Port_B?\"")
    console.print("    • \"Force shipment through Port_A only\"")
    console.print()

    console.print("[bold green]═══════════════════════════════════════════════════════════[/bold green]")
    console.print("[bold]📦 3. PRODUCTION TARGET SCENARIOS[/bold]")
    console.print("[dim]Adjust production volumes[/dim]")
    console.print()
    console.print("  Examples:")
    console.print("    • \"What if production target is 220,000 tons?\"")
    console.print("    • \"Increase production by 10%\"")
    console.print()

    console.print("[bold green]═══════════════════════════════════════════════════════════[/bold green]")
    console.print("[bold]💰 4. FREIGHT COST SCENARIOS[/bold]")
    console.print("[dim]Model cost increases or decreases[/dim]")
    console.print()
    console.print("  Examples:")
    console.print("    • \"What if inbound freight costs increase 15%?\"")
    console.print("    • \"Reduce outbound freight by 10%\"")
    console.print("    • \"Increase sea freight costs by 25%\"")
    console.print()

    console.print("[bold green]═══════════════════════════════════════════════════════════[/bold green]")
    console.print("[bold]⚙️ 5. YIELD FACTOR SCENARIOS[/bold]")
    console.print("[dim]Change conversion efficiency of materials[/dim]")
    console.print()
    console.print("  Examples:")
    console.print("    • \"What if MaterialE yield increases to 22%?\"")
    console.print("    • \"Improve MaterialA yield factor by 10%\"")
    console.print()

    console.print("[bold green]═══════════════════════════════════════════════════════════[/bold green]")
    console.print("[bold]📊 6. AVAILABILITY SCENARIOS[/bold]")
    console.print("[dim]Model supply constraints or expansions[/dim]")
    console.print()
    console.print("  Examples:")
    console.print("    • \"What if SupplierA_City1 MaterialC availability doubles?\"")
    console.print("    • \"Reduce MaterialE availability by 20%\"")
    console.print()

    console.print("[bold cyan]💡 Tips:[/bold cyan]")
    console.print("  • Ask questions in plain English - Claude understands context")
    console.print("  • Type [bold]'list'[/bold] to see all collection points and ports")
    console.print("  • Type [bold]'help'[/bold] anytime to see this message")
    console.print("  • Type [bold]'quit'[/bold] to exit")
    console.print()


def _display_list_resources(baseline_data: OptimizationData) -> None:
    """Display list of collection points and ports for reference."""
    console.print()
    console.print("[bold cyan]Available Resources:[/bold cyan]\n")

    # Collection points table
    console.print("[bold]Collection Points (Facility Location Options):[/bold]")
    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("Site ID", style="cyan")
    table.add_column("Company")
    table.add_column("Plant")

    for cp in baseline_data.collection_points:
        table.add_row(cp.site_id, cp.company, cp.plant)

    console.print(table)
    console.print()

    # Ports table
    console.print("[bold]Export Ports:[/bold]")
    port_table = Table(show_header=True, box=None, padding=(0, 2))
    port_table.add_column("Port Name", style="cyan")
    port_table.add_column("Operational Cost ($/ton)", justify="right")
    port_table.add_column("Sea Freight ($/ton)", justify="right")

    for port in baseline_data.ports:
        port_table.add_row(
            port.port_name,
            f"${port.operational_cost:.2f}",
            f"${port.sea_freight_cost:.2f}"
        )

    console.print(port_table)
    console.print()

    # Materials summary
    console.print("[bold]Materials:[/bold] A, B, C, D, E")
    console.print()

    console.print("[dim]Use these exact names in your questions[/dim]")
    console.print()
