# Logistics Optimizer 

## Introduction

This prototype implements a **facility location optimization system** that finds the optimal production facility location from multiple collection points to minimize total logistics costs. The system uses Mixed-Integer Linear Programming (MILP) to make strategic decisions about:

- **Where** to locate the production facility.
- **Which** raw material sources to use.
- **Which** export ports to select.
- **How much** raw material to procure from each source.

The optimizer uses a **two-phase approach** assuming strategic constraints:

1. **Phase 1:** Find optimal facility location using Materials A-D (excluding MaterialE simulating strategic constraints).
2. **Phase 2:** Re-optimize with MaterialE included at the selected facility location.

After solving the baseline optimization, users can explore **natural language what-if scenarios** powered by Claude API to understand how changes in production targets, costs.. affect the optimal solution.

### Development Approach

This application was **developed entirely using Claude Code** following specifications in the `guidance/` directory. As the prototype author, I am not a professional software developer. While the prototype is fully functional for its intended purpose, **I acknowledge concerns about scalability and future potential technical debt**.

---

## The Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Modeling** | Pyomo 6.7+ | Mathematical optimization modeling |
| **Solver** | HiGHS 1.5+ | High-performance MILP solver |
| **Data Validation** | Pydantic 2.0+ | Type-safe data contracts |
| **Data Processing** | pandas 2.0+ | Excel file loading and manipulation |
| **CLI** | Rich 13.0+ | Terminal UI with tables, panels, and colors |
| **Natural Language** | Claude API (Anthropic) | What-if scenario query parsing |
| **Python** | 3.8+ | Core runtime |

---

## Important: What-If Scenario Best Practices

The what-if interface supports natural language queries to explore alternative scenarios. Here are effective query patterns:

### ✅ **Production Volume Changes**
- "What if production target is 200,000 tons?"
- "What if we increase production by 15%?"
- "What if we reduce production to 180,000 tons?"

### ✅ **Facility and Port Constraints**
- "What if the facility must be at SupplierA_City1?"
- "What if we can only use Port_B?"
- "What if we force facility at SupplierC_City2 and use Port_A and Port_C?"

### ✅ **Cost Adjustments**
- "What if inbound freight costs increase by 20%?"
- "What if sea freight costs decrease by 10%?"
- "What if all freight costs go up 15%?"

### ✅ **Material Parameters**
- "What if MaterialE yield factor increases to 22%?"
- "What if SupplierB_City1 MaterialA volume doubles?"
- "What if MaterialA max consumption increases to 35%?"

### ✅ **Combined Scenarios**
- "What if production increases to 220,000 tons and inbound freight costs go up 10%?"
- "What if we force Port_B and sea freight costs decrease by 15%?"

### ❌ **Avoid Vague Questions**
- "Make it better" ❌
- "Optimize more" ❌
- "What's the best option?" ❌

**Why specificity matters:** The Claude API needs clear parameter changes to modify the optimization model correctly. Specific values and constraints ensure accurate scenario analysis.

---

## User Scenarios

### **Scenario 1: Baseline Optimization**
Run the standard facility location optimization to establish the baseline solution.

**User Action:**
```bash
python main.py
```

**System Behavior:**
1. Displays welcome banner with project overview
2. Prompts user to confirm data loading
3. Loads and validates all Excel input files
4. Checks production feasibility (materials sufficient for target)
5. Shows problem summary (collection points, production target, ports, constraints)
6. Prompts user to confirm optimization
7. **Phase 1:** Finds optimal facility location using Materials A-D only
8. **Phase 2:** Re-optimizes with MaterialE at selected facility
9. Displays results in terminal (facility, costs, sourcing breakdown)
10. Saves detailed markdown report to `results/optimization_output.md`

**Output Includes:**
- Optimal facility location
- Selected port(s) for export
- Total cost breakdown by component (raw materials, inbound/outbound freight, port ops, sea freight)
- Raw material sourcing breakdown (which sources supply which materials)
- Cost per ton of finished product
- Production and yield metrics
- Solve time

---

### **Scenario 2: What-If Analysis - Production Volume**
Explore how changing production target affects costs and facility selection.

**User Question (in what-if mode):**
> "What if production target is 200,000 tons?"

**System Behavior:**
1. Calls Claude API to parse the natural language query
2. Extracts modification: `production_target = 200000`
3. Displays parsed scenario and asks for confirmation
4. Checks feasibility for Phase 1 (without MaterialE) and full scenario (with MaterialE)
5. Runs two-phase optimization with modified production target
6. Compares results to baseline in side-by-side table
7. Generates detailed comparison report with:
   - Cost changes by component ($ and %)
   - Material consumption changes by type
   - Narrative key insights (business-friendly summary)
8. Saves versioned report: `results/whatif_output_v1.md`

**Key Insights Example:**
> "The optimal facility location remains SupplierA_City1, confirming that the network structure is still appropriate. Increasing production to 200,000 tons raises total logistics costs from $12.3M to $14.1M (+15%), primarily due to the need for additional raw material procurement. The cost per ton increases slightly from $61.50 to $70.50, indicating modest economies of scale are offset by sourcing from more distant collection points..."

---

## How the System Handles Your Queries

### **Baseline Optimization Flow**
1. **Data Loading:** Reads 5 Excel files from `data/` directory
2. **Validation:** Pydantic models ensure data integrity and site ID consistency
3. **Feasibility Check:** Verifies raw material availability meets production target
4. **Phase 1 Model:** Pyomo builds MILP model excluding MaterialE
5. **Phase 1 Solve:** HiGHS finds optimal facility location
6. **Phase 2 Model:** Rebuilds model WITH MaterialE, facility fixed from Phase 1
7. **Phase 2 Solve:** HiGHS optimizes full network with MaterialE
8. **Result Extraction:** Parses Pyomo solution into structured dictionary
9. **Display & Report:** Rich terminal output + markdown file generation

### **What-If Scenario Flow**
1. **User Query:** Natural language question entered in CLI
2. **Claude API Call:** Parses query into structured modifications JSON
   ```json
   {
     "modifications": [
       {
         "parameter_type": "production_target",
         "action": "set",
         "value": 200000.0,
         "description": "Increase production to 200,000 tons"
       }
     ],
     "scenario_name": "Increased Production Scenario",
     "explanation": "This scenario tests higher production volume..."
   }
   ```
3. **Data Modification:** Deep copies baseline data and applies changes
4. **Feasibility Checks:** Validates Phase 1 (no MaterialE) and full feasibility
5. **Two-Phase Optimization:** Runs same approach as baseline with modified data
6. **Comparison:** Side-by-side tables comparing baseline vs what-if
7. **Narrative Insights:** Claude-style business summary of key differences
8. **Versioned Report:** Saves `whatif_output_vN.md` with auto-incrementing version

---

## Data Files

### Prepare Input Data
Ensure the `data/` directory contains all required Excel files:

```
data/
├── INPUT_RawMaterial_Details.xlsx
├── INPUT_RawMaterial_Distance_Matrix_And_Freight.xlsx
├── INPUT_FinishedProd_Distance_Matrix_And_Freight.xlsx
├── INPUT_Demand_Yield_Limits.xlsx
└── INPUT_Port_Details.xlsx
```

**File Descriptions:**
- `INPUT_RawMaterial_Details.xlsx`: Collection point volumes and prices for Materials A-E
- `INPUT_RawMaterial_Distance_Matrix_And_Freight.xlsx`: Inbound freight costs, MaterialE special freight
- `INPUT_FinishedProd_Distance_Matrix_And_Freight.xlsx`: Outbound freight costs to ports
- `INPUT_Demand_Yield_Limits.xlsx`: Production target, yield factors, max consumption limits
- `INPUT_Port_Details.xlsx`: Port operational costs and sea freight costs

---

## Running the Optimizer

### Basic Run (Baseline Optimization Only)
```bash
python main.py
```

**Interactive Prompts:**
1. "Ready to load data and begin optimization?" → Answer `y`
2. Review problem summary (collection points, production target, ports)
3. "Ready to solve optimization problem?" → Answer `y`
4. Wait for optimization to complete (~5-30 seconds depending on problem size)
5. Review results in terminal
6. "Would you like to run what-if scenarios?" → Answer `n` to exit

**Output Files:**
- `results/optimization_output.md` - Detailed markdown report with all results

### Full Run (Baseline + What-If Scenarios)
```bash
python main.py
```

Follow prompts as above, but when asked "Would you like to run what-if scenarios?", answer `y`.

**What-If Commands:**
- `help` - Display scenario examples and syntax guide
- `list` - Show all collection points and ports
- `quit` - Exit what-if mode and return to terminal

---

## Prototype Structure

```
logistics-design-nlmv01c/
├── main.py                      # Main entry point
├── requirements.txt             # Python dependencies
├── README.md                    # This file
│
├── data/                        # Input Excel files (user-provided)
│   ├── INPUT_RawMaterial_Details.xlsx
│   ├── INPUT_RawMaterial_Distance_Matrix_And_Freight.xlsx
│   ├── INPUT_FinishedProd_Distance_Matrix_And_Freight.xlsx
│   ├── INPUT_Demand_Yield_Limits.xlsx
│   └── INPUT_Port_Details.xlsx
│
├── results/                     # Output reports (auto-generated)
│   ├── optimization_output.md   # Baseline optimization report
│   ├── whatif_output_v1.md      # What-if scenario reports
│   ├── whatif_output_v2.md
│   └── ...
│
├── src/                         # Source code modules
│   ├── data_loader.py           # Excel loading + Pydantic validation
│   ├── model_builder.py         # Pyomo MILP model construction
│   ├── solver.py                # HiGHS solver interface + result extraction
│   ├── reporter.py              # Markdown report generation
│   ├── cli.py                   # Rich terminal UI functions
│   └── nl_interface.py          # Natural language what-if interface (Claude API)
│
└── guidance/                    # Architecture documentation
    └── cli_architecture.md      # CLI design specification

ANTHROPIC_API_KEY configured to use local OS environment variables

Create a venv (virtual environment) to install the prototype dependecies

```


