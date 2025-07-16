
import os
import googlemaps
import numpy as np
import datetime
import time

# Q1: Next step: How to lower the cost of API search? Pre-filter by distance?

def get_unified_distance_time_matrix(patient_coords, depot_coords, api_key=None, traffic_mode='F'):
    """
    Calculates a unified distance and time matrix for depots and patients.
    The function combines depot and patient coordinates, handles API query limits
    by chunking, and returns two square matrices.

    The final matrix layout will be:
        Rows/Cols: [Depot_0, Depot_1, ..., Patient_0, Patient_1, ...]

    Args:
        patient_coords (list): A list of patient coordinates, e.g., [[lat1, lng1], ...].
        depot_coords (list): A list of depot coordinates, e.g., [[lat_A, lng_A], ...].
        api_key (str, optional): Your Google Maps API key.
        traffic_mode (str): 'F' for historical/typical traffic (default), 
                            'T' for real-time traffic.

    Returns:
        tuple: A tuple of (distance_matrix, time_matrix) as square numpy arrays.
               Distance is in kilometers, Time is in minutes.
    """
    if not api_key:
        api_key = os.environ.get('GMAPS_API_KEY')
        if not api_key:
            print("Error: Google Maps API key not found.")
            return None, None
            
    all_coords = depot_coords + patient_coords
    
    gmaps = googlemaps.Client(key=api_key)
    n_points = len(all_coords)
    distance_matrix = np.zeros((n_points, n_points))
    time_matrix = np.zeros((n_points, n_points))

    # Google's server-side limit is 100 elements. We chunk by 10 origins at a time.
    chunk_size = 10 
    print(f"Calculating a {n_points}x{n_points} matrix. This may take some time...")

    for i in range(0, n_points, chunk_size):
        origins_chunk = all_coords[i : i + chunk_size]
        print(f"  - Processing origins {i} through {min(i + chunk_size - 1, n_points - 1)}...")

        api_params = {"origins": origins_chunk, "destinations": all_coords, "mode": "driving"}
        if traffic_mode.upper() == 'T':
            api_params["departure_time"] = datetime.datetime.now()

        try:
            result = gmaps.distance_matrix(**api_params)
            for origin_idx, row in enumerate(result['rows']):
                global_origin_idx = i + origin_idx
                for dest_idx, element in enumerate(row['elements']):
                    if element['status'] == 'OK':
                        distance_matrix[global_origin_idx, dest_idx] = element['distance']['value'] / 1000.0
                        time_matrix[global_origin_idx, dest_idx] = element['duration']['value'] / 60.0
                    else:
                        distance_matrix[global_origin_idx, dest_idx] = -1
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

# --- Example usage for testing ---
if __name__ == '__main__':
    MY_API_KEY = "AIzaSyAd0ZBfbXuXqfxlRYGtkbPJJ6w1RxdUc-A"#YOUR_API_KEY_HERE"

    # Sample data for testing
    test_depots = [[40.7628, -73.9680], [40.7401, -73.9904]]
    test_patients = [[40.7484, -73.9857], [40.7580, -73.9855], [40.7128, -74.0060]]
    
    dist_matrix_file = "distance_matrix.npy"
    time_matrix_file = "time_matrix.npy"

    if os.path.exists(dist_matrix_file):
        distance_matrix = load_matrix(dist_matrix_file)
        time_matrix = load_matrix(time_matrix_file)
    else:
        print("Matrices not found locally. Calculating via Google Maps API...")
        # --- The function call is now cleaner ---
        distance_matrix, time_matrix = get_unified_distance_time_matrix(
            patient_coords=test_patients, 
            depot_coords=test_depots, 
            api_key=MY_API_KEY, 
            traffic_mode='F'
        )
        if distance_matrix is not None:
            save_matrix(distance_matrix, dist_matrix_file)
            save_matrix(time_matrix, time_matrix_file)

    if distance_matrix is not None:
        print("\n--- Final Distance Matrix (km) ---")
        print("Rows/Cols: Depot_0, Depot_1, Patient_0, Patient_1, Patient_2")
        print(np.round(distance_matrix, 2))