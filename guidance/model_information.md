# Logistics Solver - Model Information

## Files Description

- **INPUT_FinishedProd_Distance_Matrix_And_Freight.xlsx**: Contains the finished product possible sites distances (miles) and freights (US$/ton)
- **INPUT_RawMaterial_Details.xlsx**: Contains the raw material collection points volumes (tons) and price (US$/t)
- **INPUT_RawMaterial_Distance_Matrix_And_Freight.xlsx**: Contains the raw material collection points distances (miles) and freights (US$/ton)
- **INPUT_Demand_Yield_Limits.xlsx**: Contains the finished product production volume (tons), maximum consumption per type of raw material (%), yield factor to convert each type of raw material into finished product (%)
- **INPUT_Ports_Details.xlsx**: Contains ports operational cost (US$/t) and sea freights (US$/t)

## Project Description

- A Solver able to define the best facility location by minimizing the total cost composed by the raw material and the logistics costs.
- An integration to LLM to run what-if scenarios using natural language feature to change the model parameters. 

## Guidance

### 1. Planning
Use your plan mode before going any further with coding.

### 2. Facility Location Remarks
1. The optimum facility location must be one of the rawmaterial collection points.
2. The optimum facility location must be selected without consider the RawMaterialE_Volume in INPUT_RawMaterial_Details.xlsx file.
3. After the optimum facility location selected, then add the RawMaterialE_Volume and update the calculation accordingly. 

### 3. Data Understanding
Carefully understand all files in the folder `@data`.

### 4. Solver Selection
HiGHS optimization solver.

### 5. Constraints Analysis
Carefully analyze all possible constraints within the optimization model. 

### 6. Required Outputs
As minimum outputs you must bring:
- Optimum facility location defined among all rawmaterial collection points
- Finishedprod production in tons
- Total raw material consumed in tons
- Total raw material consumed per type in tons
- Total raw material consumed per rawmaterial collection point in tons
- Raw material average cost in US$/t
- Raw material inbound logistics cost in US$/t
- Finished product outbound logistics cost in US$/t
- Average yield factor in %
- Costs must be shown in US$/t and respective total cost based on the total tons
- When running what-if scenarios you must always show the baseline scenario versus new scenario pointing out the differences.

### 7. Output Organization
1. Register the baseline scenario outputs in the folder `@results` in a file named as `optimization_output.md`.
2. For every new what-if run, register the outputs in the folder `@results` in a file named as `whatif_output.md`. Create a version control as per what-if runs.   

### 8. Scalability
The model must be scalable to run new updated files from the folder `@data`.

### 9. User Interface
- Follow the `cli_architecture.md` in `@resultsguidance`

### 10. Requirements
- Create a virtual environment within this project to install all dependencies. 

### 11. LLM Integration: natural language feature to manage what-if scenarios
- To integrate the LLM natural language feature, use ANTHROPIC_API_KEY from my Windows OS environment variables.
- Provide the user with the feature to change finished product production, to change yield factors, to force facility location to a given raw material collection point, to force the selected port to a given port, to change freights values, to change raw material availability, using natural language. 
- Provide the user with a first clear interpretation of the solver output also using natural language. Your explanation must be a initial insight for the user judgement. 
- Provide the user with a "help" command that list the possible questions to run what-if scenarios.
- Provide the user with a "ls" command that list raw material collection points and ports available in the model. 
- This natural languagem feature must enable any person to manage the model without knowing optimization, python, solvers.   