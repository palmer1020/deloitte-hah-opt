import random
from collections import defaultdict

# --- 0. General and Gurobi Parameters ---
RANDOM_SEED = 42
Gurobi_Time_Limit = 600
Gurobi_Non_Convex = 2
Gurobi_BIG_M = 1e6
random.seed(RANDOM_SEED)

# --- 1. Basic Parameters ---
num_P = 100                 # Total number of patients.
ratio_E = 0.85              # The proportion of patients eligible for Hospital at Home (HaH).
num_S = 5                   # The number of supply bundle types. (NEW: Replaces num_K)
num_J = 1                   # The number of hospitals or depots.
num_T = 12                  # The number of days in the planning horizon.
num_E = int(num_P * ratio_E)  # The calculated number of HaH-eligible patients.
num_H = num_P - num_E       # The calculated number of high-risk (in-hospital) patients.

# --- 2. Index Sets ---
P = list(range(num_P))      # The set of all patients, indexed by i.
E = sorted(random.sample(P, num_E)) # The set of HaH-eligible patients.
H = sorted(list(set(P) - set(E))) # The set of high-risk patients.
S = list(range(num_S))      # The set of supply bundles, indexed by s. (NEW: Replaces K)
J = list(range(num_J))      # The set of hospitals/depots, indexed by j.
T = list(range(num_T))      # The set of days in the planning horizon, indexed by t.

# --- 3. Hospital Supply Parameters ---
B = 42                      # Total hospital bed capacity.
c_Hosp = 300.0              # In-hospital treatment cost per patient per day.

# --- 4. HaH Supply Parameters ---
# --- Cost Parameters ---
c_N = 250.0                 # Clinical staff home visit cost per patient per day (new name).
c_V = 3.0                   # Inventory holding cost per bundle per day.
c_D = 2.2                   # Delivery cost per unit of distance.
c_P = {s: 50.0 + s * 10.0 for s in S}  # Unit procurement cost for each bundle type s. (NEW: Indexed by s)

# --- Nurse and VRP Parameters ---
gamma = 5                   # Nurse capacity: max number of patients a nurse can visit per shift.
beta = 1.2                  # Coefficient for the sqrt(n) term in VRP cost approximation.
avg_q = {j: 15.0 for j in J} # A pre-calculated average distance from depot j to patients (in km).

# --- 5. Patient-Specific Data Generation ---
# --- Length of Stay (LOS) ---
L_Hosp_min = 3
L_Hosp_max = 8
L_Home_min = 5
L_Home_max = 12
L_hosp = {i: random.randint(L_Hosp_min, L_Hosp_max) for i in P}
L_home = {i: random.randint(L_Home_min, L_Home_max) if i in E else 0 for i in P}

# --- Daily Demand Generation (NEW: Indexed by bundle 's') ---
# This is a simplified example. A more realistic model would link patient conditions to bundles.
demand = defaultdict(int)        # Default demand is 0
for i in E:
    # For simplicity, assume each patient has a constant demand for 2 random bundles during their stay.
    demanded_bundles = random.sample(S, 2)
    for s in demanded_bundles:
        for t_day in range(L_home[i]):
            demand[s, i, t_day] = 1 # Assume they need 1 unit of each required bundle per day.