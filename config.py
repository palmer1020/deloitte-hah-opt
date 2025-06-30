import random
from collections import defaultdict

RANDOM_SEED = 42
Gurobi_Time_Limit = 600   
Gurobi_Non_Convex = 2           
Gurobi_BIG_M = 1e6          
random.seed(RANDOM_SEED)

# --- 1. Basic Parameters ---
num_P = 100                 # Total number of patients.
ratio_E = 0.85              # The proportion of patients eligible for Hospital at Home (HaH).
num_K = 3                   # The number of condition groups, corresponding to bundle types.
num_J = 1                   # The number of hospitals or depots.
num_T = 12                  # The number of days in the planning horizon.
num_E = int(num_P * ratio_E)  # The calculated number of HaH-eligible patients.
num_H = num_P - num_E       # The calculated number of high-risk (in-hospital) patients.

# --- 2. Index Sets ---
P = list(range(num_P))      # The set of all patients, indexed by i.
E = sorted(random.sample(P, num_E)) # The set of HaH-eligible patients.
H = sorted(list(set(P) - set(E))) # The set of high-risk patients who must stay in the hospital.
K = list(range(num_K))      # The set of condition groups, indexed by k.
J = list(range(num_J))      # The set of hospitals/depots, indexed by j.
T = list(range(num_T))      # The set of days in the planning horizon, indexed by t.

# --- 3. Hospital Supply Parameters ---
B = 42                      # Total hospital bed capacity.
c_Hosp = 300.0              # In-hospital treatment cost per patient per day.

# --- 4. HaH Supply Parameters ---
c_S = 250.0                 # Clinical staff home visit cost per patient per day.
c_V = 3.0                   # Inventory holding cost per bundle per day.
c_D = 2.2                   # Delivery cost per unit of distance.
# Unit procurement cost for each bundle type k (generated from the K set).
c_P = {k: 100.0 + k * 15.0 for k in K}  # Example: {0: 100.0, 1: 115.0, 2: 130.0}

# --- 5. Patient Demand Parameters ---

# Generate Predicted Length of Stay (LOS) for each patient
temp_L_Hosp_min = 3             
temp_L_Hosp_max = 8             
temp_L_Home_min = 5              
temp_L_Home_max = 12  
L_hosp = {i: random.randint(temp_L_Hosp_min, temp_L_Hosp_max) for i in P}
L_home = {i: random.randint(temp_L_Home_min, temp_L_Home_max) if i in E else 0 for i in P}

# Generate the daily demand for treatment bundles for each eligible patient
temp_patterns = random.choices(
    ["CONST", "LHL", "HL"],  # The three predefined demand patterns.
    weights=[0.4, 0.3, 0.3], # The mix of demand patterns for the simulation.
    k=num_E                  # The number of eligible patients to generate patterns for.
)

demand = defaultdict(int)        # Default demand for any (patient, day) is 0.
for i, pat in zip(E, temp_patterns):
    # Retrieve the specific length of stay for the patient.
    temp_LOS = L_home[i]

    if pat == "CONST":           # Pattern: constant 1 bundle/day.
        for t_day in range(temp_LOS):
            demand[(i, t_day)] = 1
    elif pat == "LHL":           # Pattern: low-high-low shape.
        mid = temp_LOS // 2
        for t_day in range(temp_LOS):
            if t_day < mid * 0.5 or t_day >= temp_LOS - mid * 0.5:
                demand[(i, t_day)] = 1
            else:
                demand[(i, t_day)] = 2
    else:                        # Pattern: "HL" (high demand, then tapering).
        half = temp_LOS // 2
        for t_day in range(temp_LOS):
            demand[(i, t_day)] = 2 if t_day < half else 1

