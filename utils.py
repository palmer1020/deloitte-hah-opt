# utils.py
import os
import pickle
import time
import googlemaps
import numpy as np
import config
import matplotlib.pyplot as plt
import imageio
from PIL import Image
import math
import datetime

# --- 1. Pre-processing and Data Gathering Functions ---

def get_unified_distance_time_matrix(patient_coords, depot_coords, traffic_mode='F'):
    """
    Calculates a unified distance and time matrix for depots and patients.
    This robust version handles any number of locations by chunking BOTH 
    origins and destinations to always respect the 100-element API limit.

    Args:
        patient_coords (list): A list of patient coordinates.
        depot_coords (list): A list of depot coordinates.
        traffic_mode (str): 'F' for historical, 'T' for real-time traffic.

    Returns:
        tuple: A tuple of (distance_matrix, time_matrix) as numpy arrays.
    """
    api_key = config.Maps_API_KEY
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print("Error: Google Maps API key not found or not set in config.py.")
        return None, None
            
    all_coords = depot_coords + patient_coords
    
    gmaps = googlemaps.Client(key=api_key)
    n_points = len(all_coords)
    distance_matrix = np.zeros((n_points, n_points))
    time_matrix = np.zeros((n_points, n_points))

    if n_points == 0:
        return distance_matrix, time_matrix

    chunk_size = 10
    
    print(f"Calculating a {n_points}x{n_points} matrix using {chunk_size}x{chunk_size} chunks...")

    # Outer loop for origins
    for i in range(0, n_points, chunk_size):
        origins_chunk = all_coords[i : i + chunk_size]
        
        # Inner loop for destinations
        for j in range(0, n_points, chunk_size):
            destinations_chunk = all_coords[j : j + chunk_size]
            
            print(f"  - Processing origins {i}-{i+len(origins_chunk)-1} to destinations {j}-{j+len(destinations_chunk)-1}...")

            api_params = {
                "origins": origins_chunk,
                "destinations": destinations_chunk,
                "mode": "driving"
            }
            if traffic_mode.upper() == 'T':
                api_params["departure_time"] = datetime.datetime.now()

            try:
                result = gmaps.distance_matrix(**api_params)

                for origin_idx, row in enumerate(result['rows']):
                    global_origin_idx = i + origin_idx
                    for dest_idx, element in enumerate(row['elements']):
                        global_dest_idx = j + dest_idx
                        if element['status'] == 'OK':
                            distance_matrix[global_origin_idx, global_dest_idx] = element['distance']['value'] / 1000.0
                            time_matrix[global_origin_idx, global_dest_idx] = element['duration']['value'] / 60.0
                        else:
                            distance_matrix[global_origin_idx, global_dest_idx] = -1
                
                time.sleep(1)

            except Exception as e:
                print(f"An error occurred during API call: {e}")
                return None, None

    print("Matrix calculation complete.")
    return distance_matrix, time_matrix

def save_matrix(matrix, filename):
    """Saves a numpy matrix to a file."""
    np.save(filename, matrix)
    print(f"Matrix successfully saved to {filename}")

def load_matrix(filename):
    """Loads a numpy matrix from a file."""
    if os.path.exists(filename):
        print(f"Loading matrix from {filename}...")
        return np.load(filename)
    else:
        print(f"Error: File {filename} not found.")
        return None

# --- 2. Post-processing, Plot, and Analysis Functions ---

def plot_cost_breakdown(cost_components, patient_count, bed_count, depot_count):
    """
    Generates and saves a bar chart for the cost breakdown with a dynamic filename.
    """
    names = list(cost_components.keys())
    values = list(cost_components.values())

    plt.figure(figsize=(10, 7))
    bars = plt.bar(names, values, color='skyblue')
    
    plt.ylabel('Cost ($)')
    plt.title(f'Cost Breakdown (N={patient_count}, B={bed_count}, D={depot_count})')
    plt.xticks(rotation=30, ha="right")
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval, f'${yval:,.2f}', va='bottom', ha='center')

    plt.tight_layout()
    filename = f"cost_breakdown_N{patient_count}_B{bed_count}_D{depot_count}.png"
    plt.savefig(filename)
    print(f"\nCost breakdown chart saved to {filename}")
    plt.close()

def create_delivery_gif(depot_coords, patient_coords, solution_vars, patient_count, bed_count, depot_count):
    """
    Generates a GIF animation of the delivery network for the entire planning horizon.
    """
    a_vars = solution_vars['a']
    depots_np = np.array(depot_coords)
    patients_np = np.array(patient_coords)
    
    image_files = []
    
    print("\nGenerating frames for GIF animation...")
    for t in config.T:
        plt.figure(figsize=(10, 10))
        
        plt.scatter(depots_np[:, 1], depots_np[:, 0], c='red', marker='s', s=100, label='Depots')
        plt.scatter(patients_np[:, 1], patients_np[:, 0], c='blue', marker='o', label='Patients')

        deliveries_made = 0
        for j in config.J:
            for i in config.E:
                if (i, j, t) in a_vars and a_vars[i, j, t].X > 0.5:
                    deliveries_made += 1
                    depot_loc = depot_coords[j]
                    patient_loc = patient_coords[i]
                    plt.plot([depot_loc[1], patient_loc[1]], [depot_loc[0], patient_loc[0]], 'g--', alpha=0.7)
        
        plt.xlabel("Longitude")
        plt.ylabel("Latitude")
        plt.title(f'Delivery Network (N={patient_count}, B={bed_count}, D={depot_count}) - Day {t}')
        plt.legend()
        plt.grid(True)
        plt.axis('equal')
        
        frame_filename = f"_temp_frame_day_{t}.png"
        plt.savefig(frame_filename)
        plt.close()
        image_files.append(frame_filename)
        print(f"  - Frame for Day {t} created.")

    gif_filename = f"delivery_animation_N{patient_count}_B{bed_count}_D{depot_count}.gif"
    with imageio.get_writer(gif_filename, mode='I', duration=500, loop=0) as writer:
        for filename in image_files:
            image = imageio.imread(filename)
            writer.append_data(image)
    
    for filename in image_files:
        os.remove(filename)
        
    print(f"\nDelivery animation successfully saved to {gif_filename}")