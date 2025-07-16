import gurobipy as gp
from gurobipy import GRB
import config 
import math

def build_and_solve_model():
    """
    Builds and solves the "Model V2" for joint patient selection and supply chain.
    This function uses data and parameters imported from the config.py file.
    
    Returns:
        A tuple containing the solved Gurobi model object and a dictionary
        of the variable objects for later analysis.
    """

    m = gp.Model('HaH_Model')

    # --- 1. Decision Variables ---
    
    # HaH Patient Selection
    x = m.addVars(config.P, vtype=GRB.BINARY, name='x')  # =1 if patient i is selected for HaH; =0 if in-hospital.

    # HaH Supply Chain Coordination
    y = m.addVars(config.S, config.J, config.T, lb=0, name='y')  # Inventory of bundle s at depot j at start of day t.
    z = m.addVars(config.S, config.E, config.J, config.T, lb=0, name='z') # Units of bundle s delivered from j to patient i on day t.
    p = m.addVars(config.S, config.J, config.T, lb=0, name='p') # Units of bundle s procured at depot j on day t.
    a = m.addVars(config.E, config.J, config.T, vtype=GRB.BINARY, name='a') # =1 if a delivery is made from j to patient i on day t.
    
    # Auxiliary variables for VRP cost calculation
    n_jt = m.addVars(config.J, config.T, lb=0, name='n_jt') # Number of HaH visits by depot j on day t.

    # --- 2. Objective Function ---
    # The objective is to minimize the sum of all operational costs.
    in_hosp_cost = gp.quicksum(config.c_Hosp * config.L_hosp[i] * (1 - x[i]) for i in config.P)
    nurse_cost = gp.quicksum(config.c_N * config.L_home[i] * x[i] for i in config.E)
    procure_cost = gp.quicksum(config.c_P[s] * p[s, j, t] for s in config.S for j in config.J for t in config.T)
    holding_cost = gp.quicksum(config.c_V * y[s, j, t] for s in config.S for j in config.J for t in config.T)
    
    # Transportation cost is defined via the complex VRP constraint below
    vrp_jt = m.addVars(config.J, config.T, name="vrp_jt")
    transport_cost = gp.quicksum(config.c_D * vrp_jt[j, t] for j in config.J for t in config.T)

    m.setObjective(
        in_hosp_cost + nurse_cost + procure_cost + holding_cost + transport_cost,
        GRB.MINIMIZE
    )

    # --- 3. Constraints ---
    # In-eligibility for high-risk patients
    m.addConstrs((x[i] == 0 for i in config.H), name="ineligibility")

    # Hospital bed capacity
    m.addConstr(gp.quicksum(1 - x[i] for i in config.P) <= config.B, name="bed_capacity")

    # Demand fulfillment for each supply bundle
    m.addConstrs((gp.quicksum(z[s, i, j, t] for j in config.J) == config.demand.get((s, i, t), 0) * x[i]
                  for s in config.S for i in config.E for t in config.T), name="demand_fulfillment")
                  
    # Inventory balance, including procurement
    for s in config.S:
        for j in config.J:
            initial_inventory = 0
            m.addConstr(initial_inventory + p[s,j,0] - gp.quicksum(z[s, i, j, 0] for i in config.E) == y[s,j,0])
            for t in config.T[:-1]:
                m.addConstr(
                    y[s, j, t] + p[s, j, t+1] - gp.quicksum(z[s, i, j, t+1] for i in config.E) == y[s, j, t+1], 
                    name=f"inventory_balance_{s}_{j}_{t+1}"
                )

    # Link delivery quantity (z) to the binary delivery indicator (a)
    m.addConstrs((gp.quicksum(z[s, i, j, t] for s in config.S) <= config.Gurobi_BIG_M * a[i, j, t]
                  for i in config.E for j in config.J for t in config.T), name="link_z_a")

    # Count the number of unique patient deliveries per depot per day
    m.addConstrs((n_jt[j, t] == gp.quicksum(a[i, j, t] for i in config.E) 
                  for j in config.J for t in config.T), name="count_deliveries")

    # VRP tour length approximation formula
    for j in config.J:
        for t in config.T:
            num_vehicles = m.addVar(vtype=GRB.INTEGER, name=f"num_vehicles_{j}_{t}")
            m.addGenConstrDiv(n_jt[j,t], config.gamma, num_vehicles, name=f"calc_vehicles_{j}_{t}")

            avg_round_trip_dist = 2 * config.avg_q.get(j, 0)
            
            sqrt_n = m.addVar(lb=0, name=f"sqrt_n_{j}_{t}")
            m.addGenConstrPow(n_jt[j, t], sqrt_n, 0.5, name=f"pow_sqrt_n_{j}_{t}")

            m.addConstr(
                vrp_jt[j,t] == (num_vehicles * avg_round_trip_dist) + (config.beta * sqrt_n), 
                name=f"vrp_cost_def_{j}_{t}"
            )

    # --- Solver Parameters ---
    m.Params.TimeLimit = config.Gurobi_Time_Limit 
    m.Params.NonConvex = config.Gurobi_Non_Convex
    
    # --- Solve the Model ---
    m.optimize()
    
    # --- Return Results ---
    if m.SolCount > 0:
        return m, {'x': x, 'y': y, 'z': z, 'a': a, 'p': p, 'n_jt': n_jt}
    else:
        return None, None