import random
from collections import defaultdict
import numpy as np

# =============================================================================
# --- Section 0: Credentials and High-Level Control Parameters ---
# =============================================================================
# --- API Key ---
# IMPORTANT: This is your private Google Maps API key.
# Do not share this file publicly or commit it to a public repository with the key filled in.
Maps_API_KEY = "YOUR_API_KEY_HERE"

# --- Scenario Definition ---
# This is the main control panel for your experiments.
# Change these values to define a new experimental run.
SCENARIO_NAME = "Boston Experiment"
NUM_PATIENTS_TO_GENERATE = 20
HOSPITAL_BED_CAPACITY = 10
NUM_DEPOTS_TO_USE = 2 
SCENARIO_FILENAME_BASE = "boston_exp"

# =============================================================================
# --- Section 1: DYNAMIC FILENAME CONFIGURATION ---
# --- Filenames are now generated automatically based on the parameters above ---
# =============================================================================
N = NUM_PATIENTS_TO_GENERATE
B = HOSPITAL_BED_CAPACITY
D = NUM_DEPOTS_TO_USE

# These filenames will automatically update when you change N, B, or D above.
DISTANCE_MATRIX_FILE = f"{SCENARIO_FILENAME_BASE}_N{N}_D{D}_dist.npy"
TIME_MATRIX_FILE = f"{SCENARIO_FILENAME_BASE}_N{N}_D{D}_time.npy"
SOLUTION_RESULTS_FILE = f"{SCENARIO_FILENAME_BASE}_N{N}_B{B}_D{D}.pkl"


# =============================================================================
# --- Section 2: General Model & Gurobi Parameters ---
# =============================================================================
# --- Model Parameters ---
PLANNING_HORIZON_DAYS = 14
HAH_ELIGIBLE_RATIO = 0.85
NUM_SUPPLY_BUNDLES = 5

# --- Cost Parameters ---
COST_HOSPITAL_PER_DAY = 300.0
COST_NURSE_VISIT_PER_DAY = 250.0
COST_INVENTORY_PER_UNIT_DAY = 3.0
COST_DELIVERY_PER_KM = 2.2

# --- VRP & Nurse Capacity Parameters ---
NURSE_CAPACITY_PATIENTS_PER_SHIFT = 4
VRP_BETA_COEFFICIENT = 1.2

# --- Gurobi Solver Parameters ---
GUROBI_TIME_LIMIT = 45
GUROBI_NON_CONVEX = 2
GUROBI_BIG_M = 1e6

# --- Random Seed for Reproducibility ---
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


# =============================================================================
# --- Section 3: Data Generation ---
# This section uses the parameters above to generate all necessary data structures
# and index sets for the optimization model.
# =============================================================================

print(f"Loading configuration for: {SCENARIO_NAME} (N={N}, B={B}, D={D})")

# 3.1. Master List of 20 Potential Depot Coordinates for Boston
ALL_BOSTON_DEPOTS = [
    # --- The 2 original depots ---
    {"id": "MGH", "name": "Massachusetts General Hospital", "coords": [42.3629, -71.0689]},
    {"id": "TMC", "name": "Tufts Medical Center", "coords": [42.3495, -71.0633]},
    
    # --- Other major hospitals in the core Boston/Cambridge area ---
    {"id": "BWH", "name": "Brigham and Women's Hospital", "coords": [42.3364, -71.1068]},
    {"id": "BIDMC", "name": "Beth Israel Deaconess Medical Center", "coords": [42.3366, -71.1094]},
    {"id": "BMC", "name": "Boston Medical Center", "coords": [42.3349, -71.0735]},
    {"id": "BCH", "name": "Boston Children's Hospital", "coords": [42.3372, -71.1064]},
    {"id": "DFCI", "name": "Dana-Farber Cancer Institute", "coords": [42.3376, -71.1082]},
    {"id": "MAH", "name": "Mount Auburn Hospital", "coords": [42.3744, -71.1338]}, # Cambridge
    {"id": "CHA", "name": "Cambridge Health Alliance", "coords": [42.3736, -71.1055]}, # Cambridge
    {"id": "SRH", "name": "Spaulding Rehabilitation Hospital", "coords": [42.3789, -71.0492]}, # Charlestown
    {"id": "MEE", "name": "Massachusetts Eye and Ear", "coords": [42.3606, -71.0700]},
    
    # --- Hospitals in surrounding towns for wider geographic coverage ---
    {"id": "SEM", "name": "St. Elizabeth's Medical Center", "coords": [42.3491, -71.1486]}, # Brighton
    {"id": "BWFH", "name": "Brigham and Women's Faulkner Hospital", "coords": [42.3168, -71.1416]}, # Jamaica Plain
    {"id": "NWH", "name": "Newton-Wellesley Hospital", "coords": [42.3328, -71.2462]}, # Newton
    {"id": "WH", "name": "Winchester Hospital", "coords": [42.4658, -71.1221]}, # Winchester
    {"id": "MWH", "name": "MelroseWakefield Hospital", "coords": [42.4603, -71.0614]}, # Melrose
    {"id": "CH", "name": "Carney Hospital", "coords": [42.2773, -71.0652]}, # Dorchester
    {"id": "SSH", "name": "South Shore Hospital", "coords": [42.1758, -70.9542]}, # South Weymouth
    {"id": "GSMC", "name": "Good Samaritan Medical Center", "coords": [42.0977, -71.0626]}, # Brockton
    {"id": "LHM", "name": "Lahey Hospital & Medical Center", "coords": [42.4848, -71.2015]}, # Burlington
]

# Select the depots to use for this specific experiment
if NUM_DEPOTS_TO_USE > len(ALL_BOSTON_DEPOTS):
    raise ValueError(f"NUM_DEPOTS_TO_USE ({NUM_DEPOTS_TO_USE}) cannot be greater than the number of available depots ({len(ALL_BOSTON_DEPOTS)}).")
selected_depots = ALL_BOSTON_DEPOTS[:NUM_DEPOTS_TO_USE]
depot_coords = [d["coords"] for d in selected_depots]


# 3.2. Generate Simulated Patient Coordinates around the selected Depots
patient_coords = []
for _ in range(NUM_PATIENTS_TO_GENERATE):
    center = random.choice(depot_coords)
    lat = center[0] + np.random.randn() * 0.03
    lng = center[1] + np.random.randn() * 0.03
    patient_coords.append([lat, lng])

# 3.3. Define Final Index Sets based on generated data
num_P = len(patient_coords)
num_E = int(num_P * HAH_ELIGIBLE_RATIO)
num_H = num_P - num_E
num_J = len(depot_coords) 

P = list(range(num_P))
E = sorted(random.sample(P, num_E))
H = sorted(list(set(P) - set(E)))
S = list(range(NUM_SUPPLY_BUNDLES))
J = list(range(num_J))
T = list(range(PLANNING_HORIZON_DAYS))

# 3.4. Define Final Parameters based on generated data
B = HOSPITAL_BED_CAPACITY
c_Hosp = COST_HOSPITAL_PER_DAY
c_N = COST_NURSE_VISIT_PER_DAY
c_V = COST_INVENTORY_PER_UNIT_DAY
c_D = COST_DELIVERY_PER_KM
c_P = {s: 50.0 + s * 10.0 for s in S} # Procurement cost for each bundle
gamma = NURSE_CAPACITY_PATIENTS_PER_SHIFT
beta = VRP_BETA_COEFFICIENT
avg_q = {j: 15.0 for j in J} # This is used as a simplified distance in the model

# 3.5. Generate Patient-Specific Data (LOS and Demand)
L_hosp = {i: random.randint(3, 8) for i in P}
L_home = {i: random.randint(5, 12) if i in E else 0 for i in P}

demand = defaultdict(int)
for i in E:
    num_bundles_needed = random.randint(1, 2)
    demanded_bundles = random.sample(S, num_bundles_needed)
    for s in demanded_bundles:
        for t_day in range(L_home[i]):
            demand[s, i, t_day] = 1 # Assume 1 unit per day is needed

print(f"Configuration loaded successfully.")