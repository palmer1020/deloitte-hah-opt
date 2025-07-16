import gurobipy as gp
from gurobipy import GRB
import config

def build_and_solve_model(distance_matrix):
    """
    Builds and solves the "Model V2" using a pre-calculated distance matrix.
    This version includes a more precise VRP cost formulation using quadratic constraints.
    """
    m = gp.Model('HaH_Model_V2_Quadratic')

    # --- 1. Decision Variables ---
    x = m.addVars(config.P, vtype=GRB.BINARY, name='x')
    y = m.addVars(config.S, config.J, config.T, lb=0, name='y')
    z = m.addVars(config.S, config.E, config.J, config.T, lb=0, name='z')
    p = m.addVars(config.S, config.J, config.T, lb=0, name='p')
    a = m.addVars(config.E, config.J, config.T, vtype=GRB.BINARY, name='a')
    n_jt = m.addVars(config.J, config.T, lb=0, name='n_jt')

    # --- 2. Objective Function ---
    in_hosp_cost = gp.quicksum(config.c_Hosp * config.L_hosp[i] * (1 - x[i]) for i in config.P)
    nurse_cost = gp.quicksum(config.c_N * config.L_home[i] * x[i] for i in config.E)
    procure_cost = gp.quicksum(config.c_P[s] * p[s, j, t] for s in config.S for j in config.J for t in config.T)
    holding_cost = gp.quicksum(config.c_V * y[s, j, t] for s in config.S for j in config.J for t in config.T)
    
    vrp_jt = m.addVars(config.J, config.T, name="vrp_jt")
    transport_cost = gp.quicksum(config.c_D * vrp_jt[j, t] for j in config.J for t in config.T)

    m.setObjective(
        in_hosp_cost + nurse_cost + procure_cost + holding_cost + transport_cost,
        GRB.MINIMIZE
    )

    # --- 3. Constraints ---
    m.addConstrs((x[i] == 0 for i in config.H), name="ineligibility")
    m.addConstr(gp.quicksum(1 - x[i] for i in config.P) <= config.B, name="bed_capacity")
    m.addConstrs((gp.quicksum(z[s, i, j, t] for j in config.J) == config.demand.get((s, i, t), 0) * x[i]
                  for s in config.S for i in config.E for t in config.T), name="demand_fulfillment")
                  
    for s in config.S:
        for j in config.J:
            initial_inventory = 0
            m.addConstr(initial_inventory + p[s,j,0] - gp.quicksum(z[s, i, j, 0] for i in config.E) == y[s,j,0])
            for t in config.T[:-1]:
                m.addConstr(
                    y[s, j, t] + p[s, j, t+1] - gp.quicksum(z[s, i, j, t+1] for i in config.E) == y[s, j, t+1], 
                    name=f"inventory_balance_{s}_{j}_{t+1}"
                )

    m.addConstrs((gp.quicksum(z[s, i, j, t] for s in config.S) <= config.GUROBI_BIG_M * a[i, j, t]
                  for i in config.E for j in config.J for t in config.T), name="link_z_a")

    m.addConstrs((n_jt[j, t] == gp.quicksum(a[i, j, t] for i in config.E) 
                  for j in config.J for t in config.T), name="count_deliveries")

    # --- VRP tour length approximation (New, more precise implementation) ---
    for j in config.J:
        for t in config.T:
            num_vehicles = m.addVar(vtype=GRB.INTEGER, name=f"num_vehicles_{j}_{t}")
            m.addConstr(num_vehicles * config.gamma >= n_jt[j,t], name=f"calc_vehicles_{j}_{t}")
            
            # --- NEW: Re-introducing the decision-making link using a Quadratic Constraint ---
            # Define a new variable for the actual average one-way distance
            avg_dist_jt = m.addVar(lb=0, name=f"avg_dist_{j}_{t}")
            
            # Calculate the total one-way distance for selected patients
            total_one_way_distance = gp.quicksum(a[i, j, t] * distance_matrix[j, config.num_J + i] for i in config.E)
            
            # Add a quadratic constraint: avg_dist * n_jt == total_distance
            # This ensures that avg_dist accurately reflects the decision variables 'a'.
            # Note: A small tolerance (e.g., 1e-6) might be needed if n_jt can be zero.
            m.addQConstr(avg_dist_jt * n_jt[j, t] == total_one_way_distance, name=f"avg_dist_calc_{j}_{t}")
            
            # Part 1: Spoke Cost
            spoke_cost = num_vehicles * 2 * avg_dist_jt
            
            # Part 2: Tour Cost 
            sqrt_n = m.addVar(lb=0, name=f"sqrt_n_{j}_{t}")
            m.addGenConstrPow(n_jt[j, t], sqrt_n, 0.5, name=f"pow_sqrt_n_{j}_{t}")
            tour_cost = config.beta * sqrt_n

            # Combine both parts to define the total VRP cost
            m.addConstr(vrp_jt[j,t] == spoke_cost + tour_cost, name=f"vrp_cost_def_{j}_{t}")

    # --- Solver Parameters ---
    m.Params.TimeLimit = config.GUROBI_TIME_LIMIT 
    m.Params.NonConvex = 2 # Setting this to 2 is required for Gurobi to handle non-convex quadratic constraints
    
    m.optimize()
    
    if m.SolCount > 0:
        cost_breakdown = {
            "In-Hospital": in_hosp_cost.getValue(),
            "Nurse Visits": nurse_cost.getValue(),
            "Procurement": procure_cost.getValue(),
            "Inventory": holding_cost.getValue(),
            "Transport": transport_cost.getValue()
        }
        variables = {'x': x, 'y': y, 'z': z, 'a': a, 'p': p, 'n_jt': n_jt}
        return m, variables, cost_breakdown
    else:
        return None, None, None