import config
from model import build_and_solve_model

def main():
    model, variables = build_and_solve_model()
    if model and model.SolCount > 0:
        print(f"\nOptimization finished. A solution was found.")
        print(f"Total optimal cost = ${model.objVal:,.2f}")

        # Extracting and printing the list of selected patients
        x_vars = variables['x']
        selected_for_hah = sorted([i for i in config.E if x_vars[i].X > 0.5])
        
        print(f"\nNumber of patients selected for HaH: {len(selected_for_hah)}")
        print(f"HaH Patient IDs: {selected_for_hah}")

    else:
        print("\nNo solution was found within the time limit.")
        print("The model may be infeasible or too complex to solve in the time allowed.")

if __name__ == "__main__":
    main()