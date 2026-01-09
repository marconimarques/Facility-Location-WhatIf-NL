"""Markdown report generation module."""

from pathlib import Path
from datetime import datetime
from typing import Dict


def generate_markdown_report(
    solution: Dict,
    output_path: str,
    scenario_name: str = "Baseline"
) -> None:
    """Generate detailed markdown report.

    Args:
        solution: Solution dictionary from solver
        output_path: Path to save report
        scenario_name: Name of scenario for report title
    """
    report = f"""# Logistics Optimization Report

## Scenario: {scenario_name}

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Optimal Solution

### Facility Location
**Selected Site:** {solution['facility_location']}

### Production Summary"""

    # Add selected port(s)
    ports = solution['selected_ports']
    if len(ports) == 1:
        report += f"\n- **Selected Port:** {ports[0]}"
    elif len(ports) > 1:
        report += f"\n- **Selected Ports:** {', '.join(ports)}"

    report += f"""
- **Total Finished Product Produced:** {solution['total_finished_product_tons']:,.2f} tons
- **Total Raw Material Consumed:** {solution['total_raw_material_tons']:,.2f} tons
- **Average Yield Factor:** {solution['avg_yield_factor']:.2%}

---

## Cost Breakdown

| Component | Total Cost ($) | Per Ton ($/t) | % of Total |
|-----------|----------------|---------------|------------|
| Raw Materials (avg) | ${solution['costs']['raw_material_total']:,.2f} | ${solution['costs']['raw_material_per_ton']:.2f} | {solution['costs']['raw_material_total']/solution['costs']['total_cost']*100:.1f}% |
| Inbound Freight | ${solution['costs']['inbound_freight_total']:,.2f} | ${solution['costs']['inbound_freight_per_ton']:.2f} | {solution['costs']['inbound_freight_total']/solution['costs']['total_cost']*100:.1f}% |
| Outbound Freight | ${solution['costs']['outbound_freight_total']:,.2f} | ${solution['costs']['outbound_freight_per_ton']:.2f} | {solution['costs']['outbound_freight_total']/solution['costs']['total_cost']*100:.1f}% |
| Port Operations | ${solution['costs']['port_operational_total']:,.2f} | ${solution['costs']['port_operational_per_ton']:.2f} | {solution['costs']['port_operational_total']/solution['costs']['total_cost']*100:.1f}% |
| Sea Freight | ${solution['costs']['sea_freight_total']:,.2f} | ${solution['costs']['sea_freight_per_ton']:.2f} | {solution['costs']['sea_freight_total']/solution['costs']['total_cost']*100:.1f}% |
| **TOTAL** | **${solution['costs']['total_cost']:,.2f}** | **${solution['costs']['total_cost']/solution['total_finished_product_tons']:.2f}** | **100.0%** |

---

## Raw Material Sourcing Breakdown

| Collection Point | Total (t) | Mat A | Mat B | Mat C | Mat D | Mat E | % Total |
|-----------------|-----------|-------|-------|-------|-------|-------|---------|
"""

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

        mat_a = f"{materials['A']:,.0f}" if materials['A'] > 0.5 else "-"
        mat_b = f"{materials['B']:,.0f}" if materials['B'] > 0.5 else "-"
        mat_c = f"{materials['C']:,.0f}" if materials['C'] > 0.5 else "-"
        mat_d = f"{materials['D']:,.0f}" if materials['D'] > 0.5 else "-"
        mat_e = f"{materials['E']:,.0f}" if materials['E'] > 0.5 else "-"

        report += f"| {source} | {source_total:,.0f} | {mat_a} | {mat_b} | {mat_c} | {mat_d} | {mat_e} | {source_pct:.1f}% |\n"

    # Add totals row
    totals_by_type = {
        'A': solution['raw_material_by_type'].get('RawMaterialA', 0),
        'B': solution['raw_material_by_type'].get('RawMaterialB', 0),
        'C': solution['raw_material_by_type'].get('RawMaterialC', 0),
        'D': solution['raw_material_by_type'].get('RawMaterialD', 0),
        'E': solution['raw_material_by_type'].get('RawMaterialE', 0)
    }

    report += f"| **TOTAL BY TYPE** | **{total_raw:,.0f}** | **{totals_by_type['A']:,.0f}** | **{totals_by_type['B']:,.0f}** | **{totals_by_type['C']:,.0f}** | **{totals_by_type['D']:,.0f}** | **{totals_by_type['E']:,.0f}** | **100.0%** |\n"

    # Add percentage row
    pct_a = (totals_by_type['A']/total_raw*100) if total_raw > 0 else 0
    pct_b = (totals_by_type['B']/total_raw*100) if total_raw > 0 else 0
    pct_c = (totals_by_type['C']/total_raw*100) if total_raw > 0 else 0
    pct_d = (totals_by_type['D']/total_raw*100) if total_raw > 0 else 0
    pct_e = (totals_by_type['E']/total_raw*100) if total_raw > 0 else 0

    report += f"| *% of Total* | *100.0%* | *{pct_a:.1f}%* | *{pct_b:.1f}%* | *{pct_c:.1f}%* | *{pct_d:.1f}%* | *{pct_e:.1f}%* | |\n"

    report += f"""
---

## Port Shipments

| Facility | Port | Tons Shipped |
|----------|------|-------------|
"""

    for (site, port), tons in sorted(solution['port_shipments'].items()):
        report += f"| {site} | {port} | {tons:,.2f} |\n"

    report += f"""
---

## Optimization Details

- **Solver:** HiGHS
- **Solve Time:** {solution['solve_time_seconds']:.2f} seconds
- **MIP Gap:** {solution.get('mip_gap', 0.01):.2%}

---

*Report generated by Logistics Optimizer*
"""

    # Write to file
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
