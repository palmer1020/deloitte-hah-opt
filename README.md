# deloitte-hah-opt
The project has three .py files.

config.py: Contains all global parameters, cost data, and the logic for generating synthetic patient data (e.g., length of stay, daily demand).


model.py: Defines the core mathematical optimization model. This includes creating the decision variables, formulating the objective function (cost minimization), and setting all the constraints (bed capacity, demand fulfillment, etc.).

main.py: The main entry point for the project. Running this script will execute the entire process: it calls the model-building function from model.py and then prints the final results, such as the total cost and the list of patients selected for HaH.