import os
import googlemaps
import numpy as np


def get_Maps_matrices(patient_coords, depot_coords, api_key=None):
    """
    Calculates distance and time matrices between patient homes and depots 
    using the Google Maps Distance Matrix API.

    Args:
        patient_coords (list): A list of patient coordinates, e.g., [[lat1, lng1], ...].
        depot_coords (list): A list of depot coordinates, e.g., [[lat_A, lng_A], ...].
        api_key (str, optional): Your Google Maps API key. If None, it tries to read 
                                 from the 'GMAPS_API_KEY' environment variable.

    Returns:
        tuple: A tuple of (distance_matrix, time_matrix) in numpy arrays.
               Distance is in kilometers, Time is in minutes.
               Returns (None, None) if an error occurs.
    """
    if not api_key:
        api_key = os.environ.get('GMAPS_API_KEY')
        if not api_key:
            print("Error: Google Maps API key not found.")
            return None, None

    try:
        gmaps = googlemaps.Client(key=api_key)
        num_patients = len(patient_coords)
        num_depots = len(depot_coords)

        distance_matrix = np.zeros((num_patients, num_depots))
        time_matrix = np.zeros((num_patients, num_depots))

        matrix_result = gmaps.distance_matrix(origins=patient_coords,
                                              destinations=depot_coords,
                                              mode="driving")

        for i, row in enumerate(matrix_result['rows']):
            for j, element in enumerate(row['elements']):
                if element['status'] == 'OK':
                    distance_matrix[i, j] = element['distance']['value'] / 1000.0
                    time_matrix[i, j] = element['duration']['value'] / 60.0
                else:
                    distance_matrix[i, j] = -1  # Use -1 to indicate no route found
                    time_matrix[i, j] = -1
        
        return distance_matrix, time_matrix

    except Exception as e:
        print(f"An error occurred while calling Google Maps API: {e}")
        return None, None

# --- Add Main Model Optimization Helper Functions ---

# --- Post-processing, Plot, and Analysis Functions ---



if __name__ == '__main__':
    print("--- Testing get_Maps_matrices function ---")
    
    # IMPORTANT: Replace with your key or set it as an environment variable
    MY_API_KEY = "AIzaSyAd0ZBfbXuXqfxlRYGtkbPJJ6w1RxdUc-A"#YOUR_API_KEY_HERE" 

    # Sample data
    test_patients = [[40.7484, -73.9857], [40.7580, -73.9855]]
    test_depots = [[40.7628, -73.9680]]

    dist_matrix, dur_matrix = get_Maps_matrices(test_patients, test_depots, api_key=MY_API_KEY)

    if dist_matrix is not None:
        print("\nTest successful!")
        print("Distance Matrix (km):\n", np.round(dist_matrix, 2))
        print("Time Matrix (min):\n", np.round(dur_matrix, 2))