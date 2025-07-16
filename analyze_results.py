import os
import pickle
import config
from utils import plot_cost_breakdown, create_delivery_gif

class MockVar:
    def __init__(self, value):
        self.X = value

def main():
    """
    This script loads a saved optimization solution and generates plots.
    """
    print("--- Analysis Script Started ---")
    
    solution_filename = config.SOLUTION_RESULTS_FILE

    if not os.path.exists(solution_filename):
        print(f"Error: Solution file '{solution_filename}' not found.")
        print("Please run main.py with the corresponding configuration first.")
        return

    with open(solution_filename, 'rb') as f:
        solution_data = pickle.load(f)
    
    print(f"Successfully loaded solution for: '{solution_data.get('config_scenario_name', 'N/A')}'")
    print(f"Total Cost: ${solution_data['total_cost']:,.2f}")

    variables_for_plotting = {}
    for key, var_dict in solution_data['variables'].items():
        variables_for_plotting[key] = {}
        for k, v_val in var_dict.items():
            variables_for_plotting[key][k] = MockVar(v_val)

    cost_components = solution_data['cost_components']
    
    # Get all necessary parameters from the config file for labeling
    patient_count = config.NUM_PATIENTS_TO_GENERATE
    bed_count = config.HOSPITAL_BED_CAPACITY
    depot_count = config.NUM_DEPOTS_TO_USE # Get depot count

    print("\nGenerating plots...")
    
    # 1. Plot cost breakdown with dynamic filename
    plot_cost_breakdown(cost_components, patient_count, bed_count, depot_count)

    # 2. Create delivery network GIF for the entire planning horizon
    create_delivery_gif(
        config.depot_coords, 
        config.patient_coords, 
        variables_for_plotting,
        patient_count,
        bed_count,
        depot_count
    )

if __name__ == "__main__":
    main()