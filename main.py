import os
import pickle
import config
from utils import get_unified_distance_time_matrix, load_matrix, save_matrix
from model import build_and_solve_model

def main():
    """
    Main execution function for the HaH-Opt project.
    1. Pre-processes data: Calculates or loads the distance/time matrices.
    2. Solves the main optimization model.
    3. Saves the solution to a file for later analysis.
    """
    # --- Step 1: Prepare Geographic Data ---
    print("--- Step 1: Preparing Geographic Data ---")
    
    # Use filenames dynamically generated in the config file
    dist_matrix_file = config.DISTANCE_MATRIX_FILE
    time_matrix_file = config.TIME_MATRIX_FILE

    if os.path.exists(dist_matrix_file) and os.path.exists(time_matrix_file):
        distance_matrix = load_matrix(dist_matrix_file)
        # time_matrix is loaded but not used in the current model version
        time_matrix = load_matrix(time_matrix_file) 
    else:
        # If matrix files are not found, call the API to generate them
        print("Matrices not found locally. Calculating via Google Maps API...")
        distance_matrix, time_matrix = get_unified_distance_time_matrix(
            patient_coords=config.patient_coords, 
            depot_coords=config.depot_coords,
            traffic_mode='F' # Use 'F' for stable, savable results
        )
        
        # If the API call was successful, save the results for future use
        if distance_matrix is not None and time_matrix is not None:
            save_matrix(distance_matrix, dist_matrix_file)
            save_matrix(time_matrix, time_matrix_file)
        else:
            print("Failed to generate matrices from API. Exiting.")
            return

    # --- Step 2: Solve the Optimization Model ---
    print("\n--- Step 2: Building and Solving the Optimization Model ---")
    
    # Pass the prepared distance_matrix to the model function
    model, variables, cost_components = build_and_solve_model(distance_matrix)

    # --- Step 3: Save Solution for Offline Analysis ---
    print("\n--- Step 3: Saving Results ---")
    if model and model.SolCount > 0:
        print(f"Optimization finished. A solution was found with cost ${model.objVal:,.2f}.")
        
        # Extract numerical values from Gurobi variables for saving
        solution_vars_values = {}
        for key, var_dict in variables.items():
            solution_vars_values[key] = {}
            for k, v in var_dict.items():
                solution_vars_values[key][k] = v.X

        # Package all necessary data into a single dictionary
        solution_data = {
            "total_cost": model.objVal,
            "variables": solution_vars_values,
            "cost_components": cost_components,
            "config_scenario_name": config.SCENARIO_NAME,
            "patient_count": config.NUM_PATIENTS_TO_GENERATE,
            "bed_count": config.HOSPITAL_BED_CAPACITY
        }

        # Use the dynamic solution filename from the config file
        with open(config.SOLUTION_RESULTS_FILE, 'wb') as f:
            pickle.dump(solution_data, f)
        print(f"Solution data successfully saved to {config.SOLUTION_RESULTS_FILE}")

    else:
        print("\nNo solution was found. No results to save.")

if __name__ == "__main__":
    main()