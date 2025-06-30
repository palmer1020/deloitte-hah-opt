import gurobipy as gp
from gurobipy import GRB
import config 

def build_and_solve_model():
    """
    Builds and solves the joint patient selection and supply chain model.
    This function uses data and parameters imported from the config.py file.
    
    Returns:
        A tuple containing the solved Gurobi model object and a dictionary
        of the variable objects (e.g., x, y, z) for later analysis.
        Returns (None, None) if no solution is found.
    """
    # Initialize the Gurobi model
    m = gp.Model('HaH_joint_selection_supply')

    # --- 1. Decision Variables ---

    x = m.addVars(config.P, vtype=GRB.BINARY, name='x')  # Patient selection: 1 if HaH, 0 if in-hospital [cite: 9]
    y = m.addVars(config.K, config.J, config.T, lb=0, name='y')  # Inventory level of bundle k at depot j on day t [cite: 10]
    z = m.addVars(config.E, config.K, config.J, config.T, lb=0, name='z') # Units of bundle k delivered from j to patient i on day t [cite: 11]
    a = m.addVars(config.E, config.J, config.T, vtype=GRB.BINARY, name='a') # Delivery indicator: 1 if a delivery is made [cite: 12]
    
    # Auxiliary variables for TSP tour length approximation
    N = m.addVars(config.J, config.T, lb=0, name='N')  # Number of patients served by depot j on day t
    w = m.addVars(config.J, config.T, lb=0, name='w')  # Auxiliary variable for sqrt(N)
    L = m.addVars(config.J, config.T, lb=0, name='L')  # Approximated route length (km)

    # --- 2. Objective Function ---

    # The objective is to minimize the sum of all operational costs. [cite: 16]
    in_hosp_cost = gp.quicksum(config.c_Hosp * config.L_hosp[i] * (1 - x[i]) for i in config.P) # In-hospital treatment cost [cite: 14, 16]
    nurse_cost = gp.quicksum(config.c_S * config.L_home[i] * x[i] for i in config.E) # HaH staff visit cost [cite: 15, 16]
    procure_cost = gp.quicksum(config.c_P[k] * z[i, k, j, t] for i in config.E for k in config.K for j in config.J for t in config.T) # Procurement cost of bundles [cite: 15, 16]
    transport_cost = gp.quicksum(config.c_D * L[j, t] for j in config.J for t in config.T) # Delivery cost [cite: 16]
    holding_cost = gp.quicksum(config.c_V * y[k, j, t] for k in config.K for j in config.J for t in config.T) # Inventory holding cost [cite: 16]
    
    m.setObjective(
        in_hosp_cost + nurse_cost + procure_cost + transport_cost + holding_cost,
        GRB.MINIMIZE
    )

    # --- 3. Constraints ---

    # High-risk patients are ineligible for HaH. 
    m.addConstrs((x[i] == 0 for i in config.H), name="ineligibility")

    # In-hospital patients must not exceed total bed capacity. 
    m.addConstr(gp.quicksum(1 - x[i] for i in config.P) <= config.B, name="bed_capacity")

    # Demand for treatment bundles must be fulfilled for all HaH patients. 
    m.addConstrs((gp.quicksum(z[i, k, j, t] for k in config.K for j in config.J) == config.demand[i, t] * x[i] 
                  for i in config.E for t in config.T), name="demand_fulfillment")
                  
    # Inventory balance constraints.
    y0 = {(k, j): 0.0 for k in config.K for j in config.J} # Assuming zero initial inventory
    for k in config.K:
        for j in config.J:
            # Day 0 inventory balance
            m.addConstr(y[k, j, 0] == y0[k, j] - gp.quicksum(z[i, k, j, t] for i in config.E), name=f"inv_bal_d0_{k}_{j}")
            # Inventory balance for subsequent days
            for t in config.T[1:]:
                 m.addConstr(y[k, j, t] == y[k, j, t-1] - gp.quicksum(z[i, k, j, t] for i in config.E), name=f"inv_bal_{k}_{j}_{t}")


    # Link the delivery quantity (z) to the binary delivery indicator (a).
    m.addConstrs((gp.quicksum(z[i, k, j, t] for k in config.K) <= config.Gurobi_BIG_M * a[i, j, t]
                  for i in config.E for j in config.J for t in config.T), name="link_delivery")

    # Count the number of unique patient deliveries per depot per day.
    m.addConstrs((N[j, t] == gp.quicksum(a[i, j, t] for i in config.E)
                  for j in config.J for t in config.T), name="count_deliveries")

    # TSP tour length approximation: L = alpha * sqrt(N). 
    # This requires a non-convex General Constraint (GenConstrPow).
    for j in config.J:
        for t in config.T:
            # This constraint models w = N^0.5
            m.addGenConstrPow(N[j, t], w[j, t], 0.5, name=f"sqrt_approx_{j}_{t}")
            # This constraint models L = alpha * w
            m.addConstr(config.c_D * w[j, t] <= L[j,t], name=f"tsp_tour_len_{j}_{t}")

    m.Params.TimeLimit = config.Gurobi_Time_Limit 
    m.Params.NonConvex = config.Gurobi_Non_Convex 
    m.optimize()