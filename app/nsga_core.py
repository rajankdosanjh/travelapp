import random
import requests
import numpy as np
from deap import base, creator, tools
from app.models import Location

# --- Configuration ---
api_key_ors = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjVhNTBiMzU5NzRkYjkxYTU5MDkzNDRiNTZkMTRiZWQxYTI2ZmQ1M2NhY2I3MmViOWRiZmJjODNlIiwiaCI6Im11cm11cjY0In0='
ors_url = 'https://api.openrouteservice.org/v2/directions/foot-walking/geojson'
MINIMUM_LOCATIONS = 5
MAXIMUM_LOCATIONS = 8
POP_SIZE = 100 #number of locations in the database
GENERATIONS = 50
CROSSOVER_PROB = 0.9
MUTATION_PROB = 0.2

# --- DEAP Global Setup ---
creator.create("FitnessMulti", base.Fitness, weights=(-1.0, 1.0))
creator.create("Individual", list, fitness=creator.FitnessMulti)


# --- Data and API Functions ---

def get_locations_dict(): #Fetches all locations from the database and returns them as a dictionary
    locations = Location.query.all()
    return {loc.id: {'name': loc.name, 'latitude': loc.latitude, 'longitude': loc.longitude, 'category_id': loc.category_id}
            for loc in locations}


def get_category_colour_name(category_id): #Maps the category ID to a color name for the map markers - see below for key/value pairs
    id_to_name_map = {1: 'Food and Drink', 2: 'History', 3: 'Shopping', 4: 'Nature', 5: 'Culture', 6: 'Nightlife'}
    category_name = id_to_name_map.get(category_id)
    colour_map = {'Food and Drink': 'red', 'History': 'blue', 'Shopping': 'yellow', 'Nature': 'green',
                 'Culture': 'purple', 'Nightlife': 'black'}
    return colour_map.get(category_name, 'grey')


def get_ors_route(coordinates):
    if len(coordinates) < 2:
        return None
    headers = {
        'Authorization': api_key_ors,
        'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
        'Content-Type': 'application/json; charset=utf-8'
    }
    try:
        response = requests.post(ors_url, headers=headers, json={'coordinates': coordinates})
        response.raise_for_status()
        data = response.json()
        # Correctly parse the 'features' key from the ORS response
        if data and data.get('features'):
            # Return the first feature, which contains the geometry
            return data['features'][0]
        else:
            print("ORS Response Error: 'features' key not found or is empty in the response.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"ORS Request Error: {e}")
        return None
    except (IndexError, KeyError, ValueError) as e:
        print(f"ORS Response Error: Could not parse route from response. {e}")
        return None


# --- Objective Functions ---

def compute_distance(individual, locations_dict):
    """Calculates the total distance of a route (to be minimized)."""
    if not individual or len(individual) < 2:
        return float('inf')
    distance = 0
    for i in range(len(individual) - 1):
        loc1 = locations_dict[individual[i]]
        loc2 = locations_dict[individual[i + 1]]
        distance += np.sqrt((loc1['latitude'] - loc2['latitude']) ** 2 + (loc1['longitude'] - loc2['longitude']) ** 2)
    return distance


def compute_satisfaction(individual, locations_dict, user_prefs):
    """Calculates the satisfaction score of a route (to be maximized)."""
    if not user_prefs or not individual:
        return 0
    matches = sum(1 for loc_id in individual if locations_dict[loc_id]['category_id'] in user_prefs)
    return matches / len(individual) if len(individual) > 0 else 0


# --- DEAP Genetic Algorithm Setup ---

def generate_individual(location_ids):
    """Generates an individual route with a variable number of locations."""
    if not location_ids or len(location_ids) < MINIMUM_LOCATIONS:
        return []
    max_len = min(len(location_ids), MAXIMUM_LOCATIONS)
    min_len = min(len(location_ids), MINIMUM_LOCATIONS)
    if min_len >= max_len:
        return random.sample(location_ids, min_len)
    return random.sample(location_ids, random.randint(min_len, max_len))


# --- Custom Genetic Operators for Variable-Length Routes ---

def custom_crossover(ind1, ind2):
    """A robust ordered crossover (OX) for variable-length routes."""
    parent1, parent2 = (ind1, ind2) if len(ind1) < len(ind2) else (ind2, ind1)
    slice_start, slice_end = sorted(random.sample(range(len(parent1)), 2))
    child_slice = parent1[slice_start:slice_end + 1]
    remaining = [item for item in parent2 if item not in child_slice]
    child = remaining[:slice_start] + child_slice + remaining[slice_start:]
    if len(child) > MAXIMUM_LOCATIONS:
        child = child[:MAXIMUM_LOCATIONS]
    elif len(child) < MINIMUM_LOCATIONS:
        needed = MINIMUM_LOCATIONS - len(child)
        for loc in parent2:
            if needed == 0: break
            if loc not in child:
                child.append(loc)
                needed -= 1
    ind1[:] = child
    ind2[:] = ind2
    return ind1, ind2


def custom_mutation(individual, all_location_ids):
    """Selects one of three mutation types (add, remove, or swap) at random."""
    if not individual: return individual,
    rand = random.random()
    if rand < 0.33 and len(individual) < MAXIMUM_LOCATIONS:
        possible_additions = [loc for loc in all_location_ids if loc not in individual]
        if possible_additions:
            individual.append(random.choice(possible_additions))
    elif rand < 0.66 and len(individual) > MINIMUM_LOCATIONS:
        individual.pop(random.randrange(len(individual)))
    else:
        if len(individual) > 0:
            idx_to_replace = random.randrange(len(individual))
            possible_swaps = [loc for loc in all_location_ids if loc not in individual]
            if possible_swaps:
                individual[idx_to_replace] = random.choice(possible_swaps)
    return individual,


# --- Main Optimization Controller ---

def get_optimized_routes(user_prefs):
    """Runs the NSGA-II algorithm to find the best routes."""
    print("--- Starting NSGA-II Optimization ---")
    user_prefs = [int(p) for p in user_prefs]
    print(f"User Preferences (Category IDs): {user_prefs}")

    locations_dict = get_locations_dict()
    location_ids = list(locations_dict.keys())
    print(f"Total locations available: {len(location_ids)}")

    toolbox = base.Toolbox()
    toolbox.register("individual", tools.initIterate, creator.Individual, lambda: generate_individual(location_ids))
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("mate", custom_crossover)
    toolbox.register("mutate", custom_mutation, all_location_ids=location_ids)
    toolbox.register("select", tools.selNSGA2)
    toolbox.register("evaluate", lambda ind: (
        compute_distance(ind, locations_dict),
        compute_satisfaction(ind, locations_dict, user_prefs)
    ))

    pop = toolbox.population(n=POP_SIZE)
    print(f"Initial population size: {len(pop)}")

    # Evaluate the first generation
    for ind in pop:
        if ind: ind.fitness.values = toolbox.evaluate(ind)

    # Main evolution loop
    for gen in range(GENERATIONS):
        offspring = toolbox.select(pop, len(pop))
        offspring = [toolbox.clone(ind) for ind in offspring]

        for child1, child2 in zip(offspring[::2], offspring[1::2]):
            if len(child1) > 0 and len(child2) > 0 and random.random() < CROSSOVER_PROB:
                toolbox.mate(child1, child2)
                del child1.fitness.values
                del child2.fitness.values

        for mutant in offspring:
            if random.random() < MUTATION_PROB:
                toolbox.mutate(mutant)
                del mutant.fitness.values

        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        for ind in invalid_ind:
            if ind: ind.fitness.values = toolbox.evaluate(ind)

        pop = toolbox.select(pop + offspring, POP_SIZE)
        # Print progress every 10 generations
        if (gen + 1) % 10 == 0:
            print(f"Generation {gen + 1}/{GENERATIONS} complete.")

    pareto_front = tools.ParetoFront()
    pareto_front.update(pop)

    print(f"Pareto front size after evolution: {len(pareto_front)}")

    valid_solutions = [ind for ind in pareto_front if ind]
    if not valid_solutions:
        print("!!! No valid solutions found in Pareto front. Returning empty list.")
        return []

    sorted_pareto = sorted(valid_solutions, key=lambda x: x.fitness.values[1], reverse=True)

    routes = []
    print(f"\n--- Top {min(3, len(sorted_pareto))} Routes ---")
    for i, ind in enumerate(sorted_pareto[:3]):
        coordinates = [[locations_dict[loc_id]['longitude'], locations_dict[loc_id]['latitude']] for loc_id in ind]
        ors_route = get_ors_route(coordinates)

        route_info = {
            'id': i + 1,
            'distance': ind.fitness.values[0],
            'satisfaction': ind.fitness.values[1],
            'locations': [
                {
                    'id': loc_id,
                    'name': locations_dict[loc_id]['name'],
                    'latitude': locations_dict[loc_id]['latitude'],
                    'longitude': locations_dict[loc_id]['longitude'],
                    'color': get_category_colour_name(locations_dict[loc_id]['category_id'])
                } for loc_id in ind
            ],
            'geometry': ors_route.get('geometry') if ors_route else None
        }
        routes.append(route_info)
        print(
            f"Route {i + 1}: Satisfaction = {route_info['satisfaction']:.2f}, Distance = {route_info['distance']:.2f}, Locations = {len(route_info['locations'])}")

    print("--- Optimization Finished ---")
    return routes