"""Main orchestration script for Logistics Optimizer."""

from src.data_loader import load_all_data, check_production_feasibility
from src.model_builder import build_facility_location_model
from src.solver import solve_optimization
from src.reporter import generate_markdown_report
from src.cli import (print_header, print_success, print_error, print_info, display_results,
                     show_welcome, confirm_start, confirm_solve, show_problem_summary,
                     show_cancellation, show_whatif_prompt)
from rich.console import Console

console = Console()


def main():
    """Main workflow orchestration with two-phase optimization."""

    try:
        # Step 0: Welcome banner
        show_welcome()

        # Step 1: Initial confirmation
        if not confirm_start():
            show_cancellation()
            return

        console.print()

        # Step 2: Load and validate data
        print_header("Loading data files...")
        data = load_all_data(data_dir='data')
        print_success(f"Loaded {len(data.collection_points)} collection points")
        print_success(f"Target production: {data.production_params.target_tons:,.0f} tons")

        # Step 3: Show problem summary
        show_problem_summary(data)

        # Step 4: Check production feasibility
        print_header("Checking production feasibility...")
        print_info("Validating raw material availability against production target...")

        # Check Phase 1 feasibility (without MaterialE)
        feasibility_phase1 = check_production_feasibility(data, exclude_material_e=True)
        print_success(f"Phase 1 feasibility: Target {feasibility_phase1['target']:,.0f} tons is achievable")
        print_info(f"  Maximum achievable: {feasibility_phase1['achievable']:,.0f} tons")
        print_info(f"  Margin: {feasibility_phase1['margin']:,.0f} tons ({feasibility_phase1['margin']/feasibility_phase1['target']*100:.1f}%)")

        # Check full feasibility (with MaterialE)
        feasibility_full = check_production_feasibility(data, exclude_material_e=False)
        print_success(f"Full feasibility: Target {feasibility_full['target']:,.0f} tons is achievable")
        print_info(f"  Maximum achievable: {feasibility_full['achievable']:,.0f} tons")
        print_info(f"  Margin: {feasibility_full['margin']:,.0f} tons ({feasibility_full['margin']/feasibility_full['target']*100:.1f}%)")

        # Step 5: Solve confirmation
        if not confirm_solve():
            show_cancellation()
            return

        # Step 6: Phase 1 - Facility location selection (exclude MaterialE)
        print_header("Phase 1: Finding optimal facility location (excluding MaterialE)...")
        print_info("Building optimization model...")

        model_phase1 = build_facility_location_model(data, exclude_material_e=True)

        print_info("Solving optimization problem...")
        solution_phase1 = solve_optimization(model_phase1, time_limit=300)

        facility = solution_phase1['facility_location']
        print_success(f"Optimal facility location: {facility}")
        print(f"  Phase 1 Total Cost: ${solution_phase1['costs']['total_cost']:,.2f}")

        # Step 3: Phase 2 - Full optimization (include MaterialE)
        print_header("Phase 2: Full optimization with MaterialE included...")
        print_info(f"Fixing facility location at: {facility}")
        print_info("Building optimization model...")

        model_phase2 = build_facility_location_model(data, exclude_material_e=False)

        # Fix facility location from Phase 1
        for s in model_phase2.Sites:
            if s == facility:
                model_phase2.y[s].fix(1)
            else:
                model_phase2.y[s].fix(0)

        print_info("Solving optimization problem...")
        solution_phase2 = solve_optimization(model_phase2, time_limit=300)

        print_success("Optimization completed successfully!")

        # Step 4: Display results
        print_header("Optimization Results")
        display_results(solution_phase2)

        # Step 5: Generate markdown report
        print_header("Generating detailed report...")
        generate_markdown_report(
            solution_phase2,
            output_path='results/optimization_output.md',
            scenario_name='Baseline'
        )
        print_success("Report saved to: results/optimization_output.md")

        console.print()
        from rich import print as rprint
        rprint("[bold green]✓ Baseline optimization completed successfully![/bold green]\n")

        # Step 11: What-if scenario analysis
        if show_whatif_prompt():
            from src.nl_interface import run_interactive_whatif
            try:
                run_interactive_whatif(
                    baseline_solution=solution_phase2,
                    baseline_data=data,
                    baseline_model=model_phase2
                )
            except KeyboardInterrupt:
                console.print("\n[yellow]What-if analysis interrupted.[/yellow]")
            except Exception as e:
                print_error(f"What-if analysis error: {e}")
                import traceback
                console.print("\n[dim]Full traceback:[/dim]")
                traceback.print_exc()

    except FileNotFoundError as e:
        print_error(f"Data file not found: {e}")
        print("\nEnsure all Excel files are in the 'data/' directory:")
        print("  - INPUT_RawMaterial_Details.xlsx")
        print("  - INPUT_RawMaterial_Distance_Matrix_And_Freight.xlsx")
        print("  - INPUT_FinishedProd_Distance_Matrix_And_Freight.xlsx")
        print("  - INPUT_Demand_Yield_Limits.xlsx")
        print("  - INPUT_Port_Details.xlsx")

    except ValueError as e:
        print_error(f"Data validation failed: {e}")
        print("\nCheck your Excel files for:")
        print("  - Missing or incorrect column names")
        print("  - Invalid data values")
        print("  - Missing material types (A-E)")

    except RuntimeError as e:
        print_error(f"Solver error: {e}")

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        print("\n[dim]Full traceback:[/dim]")
        traceback.print_exc()


if __name__ == "__main__":
    main()
