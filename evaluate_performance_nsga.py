import matplotlib.pyplot as plt
import numpy as np
import time
from platypus import Problem, Solution, Hypervolume

from app.nsga_core import get_optimized_routes
import app.nsga_core as core
from app import app


def setup_database_context(): #Allows the file to access databases on Flask without using a web request
    ctx = app.app_context()
    ctx.push()
    return ctx


def run_greedy_baseline(locations_dict, start_node, category_pref):
    """
    Implements a simple greedy algorithm as a baseline. The algorithm starts
    at a given location and always travels to the next closest one that matches
    the category preference. It calculates a combined satisfaction score.
    """
    if start_node not in locations_dict:
        return None, None

    route = [start_node]
    current_loc = start_node
    total_distance = 0

    # Initialize scores for both satisfaction metrics
    total_sentiment_score = locations_dict[start_node].get('sentiment', 0)
    category_matches = 1 if locations_dict[start_node]['category_id'] == category_pref else 0

    # Create a pool of potential next stops from the preferred category
    pool = {k: v for k, v in locations_dict.items() if k != start_node and v['category_id'] == category_pref}

    while len(route) < core.min_locations and pool:
        # Find the closest location in the pool to the current location
        next_loc_id = min(pool.keys(), key=lambda loc_id:
        np.sqrt((locations_dict[loc_id]['latitude'] - locations_dict[current_loc]['latitude']) ** 2 +
                (locations_dict[loc_id]['longitude'] - locations_dict[current_loc]['longitude']) ** 2)
                          )

        # Calculate the distance to that next location
        dist_to_next = np.sqrt(
            (locations_dict[next_loc_id]['latitude'] - locations_dict[current_loc]['latitude']) ** 2 +
            (locations_dict[next_loc_id]['longitude'] - locations_dict[current_loc]['longitude']) ** 2
        )

        # Add the new location's data to the totals
        total_distance += dist_to_next
        total_sentiment_score += locations_dict[next_loc_id].get('sentiment', 0)
        if locations_dict[next_loc_id]['category_id'] == category_pref:
            category_matches += 1

        # Update the current state for the next iteration
        current_loc = next_loc_id
        route.append(current_loc)
        del pool[current_loc]  # Remove the location from the pool so it's not visited again

    # Calculate the final average scores for each satisfaction component
    sentiment_satisfaction = total_sentiment_score / len(route) if route else 0
    category_satisfaction = category_matches / len(route) if route else 0

    # Combine the two scores into the final satisfaction metric
    combined_satisfaction = (sentiment_satisfaction + category_satisfaction) / 2

    return total_distance, combined_satisfaction


def run_experiment(params, user_preferences): #Runs the NSGA-II algorithm with a given set of parameters
    print(f"--- Running experiment with params: {params} ---")

    for key, value in params.items():
        setattr(core, key, value)

    start_time = time.time()
    pareto_front = get_optimized_routes(user_preferences)
    end_time = time.time()

    execution_time = end_time - start_time
    print(f"Finished in {execution_time:.2f} seconds.")

    return pareto_front, execution_time


def create_comparison_plot(best_nsga_front, greedy_result, best_config_name): #Generates a plot comparing the best 3 NSGA-II fronts to the greedy baseline
    plt.figure(figsize=(10, 7))

    nsga_distances = [r['distance'] / 1000 for r in best_nsga_front]
    nsga_satisfactions = [r['satisfaction'] for r in best_nsga_front]
    plt.scatter(nsga_distances, nsga_satisfactions, c='blue', label=f'NSGA-II Solutions ({best_config_name})', zorder=5)

    if greedy_result[0] is not None:
        greedy_dist_km = greedy_result[0] * 111
        plt.scatter([greedy_dist_km], [greedy_result[1]], c='red', marker='X', s=150, label='Greedy Algorithm Solution',
                    zorder=10)

    plt.title('NSGA-II vs. Greedy Algorithm Performance')
    plt.xlabel('Total Distance (km)')
    plt.ylabel('Average Satisfaction Score')
    plt.legend()
    plt.grid(True)
    plt.savefig('nsga_vs_greedy_comparison.png')
    print("NSGA-II vs. Greedy comparison plot saved to nsga_vs_greedy_comparison.png")


def main(): #Main function -> runs all experiments
    ctx = setup_database_context()

    user_preferences = [1]

    experiments = {
        "Baseline": {"crossover": 0.9, "mutation": 0.2, "population": 100, "no_of_generations": 50},
        "High Crossover": {"crossover": 1.0, "mutation": 0.2, "population": 100, "no_of_generations": 50},
        "Low Crossover": {"crossover": 0.6, "mutation": 0.2, "population": 100, "no_of_generations": 50},
        "High Mutation": {"crossover": 0.9, "mutation": 0.5, "population": 100, "no_of_generations": 50},
        "Low Mutation": {"crossover": 0.9, "mutation": 0.05, "population": 100, "no_of_generations": 50},
        "Larger Population": {"crossover": 0.9, "mutation": 0.2, "population": 200, "no_of_generations": 50},
    }

    results = {}
    for name, params in experiments.items():
        pareto_front, exec_time = run_experiment(params, user_preferences)
        if pareto_front:
            results[name] = {'front': pareto_front, 'time': exec_time}

    problem = Problem(0, 2, 0)#Defines the problem structure for Platypus (0 variables, 2 objectives, 0 constraints)

    hypervolume_indicator = Hypervolume(minimum=[0, -1.0], maximum=[50, 0.0])#Initializes the Hypervolume indicator with the problem's bounds

    hypervolumes = {}
    for name, data in results.items():
        solutions = [] # Converts your algorithm's results into the 'Solution' format that Platypus expects.
        for r in data['front']:
            solution = Solution(problem)
            solution.objectives[:] = [r['distance'] / 1000, -r['satisfaction']]
            solutions.append(solution)

        #Calculates the hypervolume using the list of Solution objects
        hv = hypervolume_indicator.calculate(solutions)
        hypervolumes[name] = hv
        print(f"Hypervolume for {name}: {hypervolumes[name]}")

# --- Generate Visualizations---
    #1a. Plot all Pareto Fronts
    plt.figure(figsize=(12, 8))
    for name, data in results.items():
        distances = [r['distance'] / 1000 for r in data['front']]
        satisfactions = [r['satisfaction'] for r in data['front']]
        plt.scatter(distances, satisfactions, label=f"{name} (HV: {hypervolumes[name]:.4f})")

    #1b.Plots greedy baseline for comparison
    all_locations = core.locations_to_dict()
  #  if greedy_dist is not None:
   #     greedy_dist_km = greedy_dist * 111
    #    plt.scatter([greedy_dist_km], [greedy_sat], c='black', marker='x', s=100, label='Greedy Baseline')

    plt.title('Pareto Front Comparison Across Different Parameters')
    plt.xlabel('Total Distance (km)')
    plt.ylabel('Average Satisfaction Score')
    plt.legend()
    plt.grid(True)
    plt.savefig('pareto_front_comparison.png')
    print("\nPareto front comparison plot saved to pareto_front_comparison.png")

    #2. Bar chart for Hypervolume
    plt.figure(figsize=(12, 7))
    names = list(hypervolumes.keys())
    values = list(hypervolumes.values())
    plt.bar(names, values, color='skyblue')
    plt.ylim(bottom=0.5)
    plt.ylabel('Hypervolume Indicator')
    plt.title('Algorithm Performance by Hypervolume')
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig('hypervolume_comparison.png')
    print("Hypervolume comparison plot saved to hypervolume_comparison.png")

    #3. Create the focused comparison graph - Greedy vs NSGA-II
    if results and hypervolumes:
        best_config_name = min(hypervolumes, key=hypervolumes.get)
        best_nsga_front = results[best_config_name]['front']
        greedy_dist, greedy_sat = run_greedy_baseline(all_locations, start_node=17, category_pref=1)
        create_comparison_plot(best_nsga_front, (greedy_dist, greedy_sat), best_config_name)

    ctx.pop()


if __name__ == '__main__':
    main()