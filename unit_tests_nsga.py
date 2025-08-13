import unittest
import csv
import os
from app.nsga_core import (
    generate_individual,
    compute_distance,
    compute_satisfaction,
    min_locations,
    max_locations
)


class TestNSGACoreFunctions(unittest.TestCase): #testsuite
    #Class variables will be loaded once and then can be accessed by all tests
    locations_dict = {}
    all_location_ids = []
    run_config = {}

    @classmethod
    def setUpClass(cls): #Loads the location data from locations.csv once before any tests are run - done before to increase efficiency

        locations_csv_path = os.path.join('app', 'data', 'locations.csv')
        if not os.path.exists(locations_csv_path):
            raise FileNotFoundError(f"{locations_csv_path} not found.")

        with open(locations_csv_path, mode='r', encoding='utf-8') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                loc_id = int(row['id'])
                cls.locations_dict[loc_id] = {
                    'latitude': float(row['latitude']),
                    'longitude': float(row['longitude']),
                    'category_id': int(row['category_id']),
                    'sentiment': float(row['rating']) / 5.0
                }
                cls.all_location_ids.append(loc_id)
        print(f"\nLoaded {len(cls.all_location_ids)} locations for testing.")

#--TESTING GENERATE_INDIVIDUAL() --
    def test_generate_individual_validity(self): #Tests that generate_individual creates valid routes

        scenarios = self.run_config.get("individual_scenarios", {})
        self.assertNotEqual(len(scenarios), 0, "Individual scenarios not loaded for this run.")

        print("\nTesting generate_individual()...")
        for name, required_stops in scenarios.items(): #'with self.subTest(...)' treats each scenario as a separate test -  allows all scenarios to run even if one fails.
            with self.subTest(name=name, required_stops=required_stops):
                individual = generate_individual(self.all_location_ids, required_stops)
                self.assertGreaterEqual(len(individual), min_locations, "Individual is too short.")
                self.assertLessEqual(len(individual), max_locations, "Individual is too long.")
                self.assertEqual(len(individual), len(set(individual)), "Individual contains duplicates.")
                for stop in required_stops:
                    self.assertIn(stop, individual, "A required stop is missing.")
        print("generate_individual() passed all scenarios for this run.")

    def test_compute_distance(self): #Tests the distance calculation with a known route (defined below)
        test_route = self.run_config.get("distance_route")
        expected_dist = self.run_config.get("expected_distance")
        self.assertIsNotNone(test_route, "Distance route not loaded for this run.")

        print("\nTesting compute_distance()...")
        distance = compute_distance(test_route, self.locations_dict)
        self.assertIsInstance(distance, float)
        self.assertGreater(distance, 0) #checks that distance is positive
        self.assertAlmostEqual(distance, expected_dist, places=5, msg="Distance calculation is incorrect.") #Checks that the calculated distance is almost equal to the expected correct answer
        print(f"compute_distance() passed. Calculated distance: {distance:.4f}")

    def test_compute_satisfaction(self):# Tests satisfaction with a route and preferences (defined below)
        test_route = self.run_config.get("satisfaction_route")
        user_prefs = self.run_config.get("user_preferences")
        expected_sat = self.run_config.get("expected_satisfaction")
        self.assertIsNotNone(test_route, "Satisfaction route not loaded for this run.")

        print("\nTesting compute_satisfaction()...")
        satisfaction = compute_satisfaction(test_route, self.locations_dict, user_prefs)
        self.assertIsInstance(satisfaction, float)
        self.assertAlmostEqual(satisfaction, expected_sat, places=5) #same as distance, compares output to expected answer
        print(f"compute_satisfaction() passed. Calculated satisfaction: {satisfaction:.4f}")


if __name__ == '__main__':
    # Define the 3 different sets of scenarios
    test_configurations = [
        {
            "name": "General & Foodie Focus",
            "individual_scenarios": {
                "two_required_stops": [7, 17],
                "no_required_stops": [],
                "four_required_stops": [1, 10, 32, 52]
            },
            "distance_route": [7, 12],  # Tower of London -> Tower Bridge
            "expected_distance": 0.0026476,
            "satisfaction_route": [17, 18],  # Borough Market, Dishoom
            "user_preferences": [1],  # Foodie
            "expected_satisfaction": 0.975
        },
        {
            "name": "Historical & Arts Focus",
            "individual_scenarios": {
                "historical_route": [8, 9, 14],  # Westminster, St. Paul's, War Rooms
                "single_art_stop": [3]  # National Gallery
            },
            "distance_route": [1, 3],  # British Museum -> National Gallery
            "expected_distance": 0.0105929,
            "satisfaction_route": [3, 5, 63],  # National Gallery, V&A, Tate Britain
            "user_preferences": [5],  # Arts & Culture
            "expected_satisfaction": 0.9633333333333334
        },
        {
            "name": "Nature & Nightlife Focus",
            "individual_scenarios": {
                "nature_route": [42, 52],  # Hyde Park, Greenwich Park
                "nightlife_route": [53, 59, 61]  # Fabric, Heaven, Electric Brixton
            },
            "distance_route": [42, 44],  # Hyde Park -> St. James's Park
            "expected_distance": 0.0341174,
            "satisfaction_route": [53, 54, 59],  # Fabric, Ministry of Sound, Heaven
            "user_preferences": [6],  # Nightlife
            "expected_satisfaction": 0.94
        }
    ]
    # ... rest of the file remains the same

    # --- THIS BLOCK RUNS ALL TESTS AND REPORT FAILURES ---

    failed_runs = [] #Keeps track of which configurations fail

    # Loop through each configuration and run the test suite
    for i, config in enumerate(test_configurations):
        print(f"\n{'=' * 25} RUN {i + 1}: {config['name']} {'=' * 25}")

        #Dynamically set the configuration for the current run, so tests use the right/relevant data
        TestNSGACoreFunctions.run_config = config

        #Takes test cases and executes them
        suite = unittest.TestLoader().loadTestsFromTestCase(TestNSGACoreFunctions) #Finds the tests by looking in the TestNSGACoreFunctions class, saves them in suite
        runner = unittest.TextTestRunner(verbosity=2) #Executes tests, verbosity increased to 2 to allow for ease of comprehension of test results
        result = runner.run(suite)

        # If the run was not successful, record the name of the failed configuration
        if not result.wasSuccessful():
            failed_runs.append(config['name'])
            print(f"--- !!! RUN {i + 1} FAILED. CONTINUING TO NEXT RUN... !!! ---")

    # --- FINAL SUMMARY REPORT ---
    print(f"---FINAL TEST SUMMARY---")
    if not failed_runs:
        print("✅ All test runs passed successfully!")
    else:
        print("❌ Some test runs failed. See details below:")
        for failed_run in failed_runs:
            print(f"  - FAILED: {failed_run}")