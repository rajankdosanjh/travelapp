import os
import random
import requests
import numpy as np
from deap import base, creator, tools
from app.models import Location

# --- Configuration ---
api_key_ors = os.environ.get('ORS_API_KEY')
api_key_google = os.environ.get('GOOGLE_MAPS_API_KEY')
min_locations = 5
max_locations = 8
population = 100 #number of locations in the database
no_of_generations = 50
crossover = 0.9
mutation = 0.2

#DEAP Core Functions - defines Fitness Function in relation to minimising distance and maximising satisfaction, defines what an Individual is and how it is represented - a list of location IDs
creator.create("FitnessMulti", base.Fitness, weights=(-1.0, 1.0))
creator.create("Individual", list, fitness=creator.FitnessMulti)


#Data and API Functions
def locations_to_dict(category_filter=None): #Fetches all locations from the database and returns them as a dictionary
    query = Location.query
    if category_filter:
        query = query.filter(Location.category_id.in_(category_filter))
    locations = query.all()

    locations_data = {}
    for loc in locations:
        avg_sentiment = loc.avg_sentiment

        locations_data[loc.id] = {
            'name': loc.name,
            'latitude': loc.latitude,
            'longitude': loc.longitude,
            'category_id': loc.category_id,
            'sentiment': avg_sentiment,
        }
    return locations_data


def get_category_colour(category_id): #Maps the category ID to a colour name for the map markers - see below for key/value pairs
    id_to_name_map = {1: 'Food and Drink', 2: 'History', 3: 'Shopping', 4: 'Nature', 5: 'Culture', 6: 'Nightlife'}
    category_name = id_to_name_map.get(category_id)
    colour_map = {
        'Food and Drink': '#ff6b35',
        'History': '#4f46e5',
        'Shopping': '#f59e0b',
        'Nature': '#10b981',
        'Culture': '#ec4899',
        'Nightlife': '#0ea5e9'
    }
    return colour_map.get(category_name, 'grey') #if location does not fit in any of the categories, marker colour is grey

def get_ors_url_mode(travel_mode = 'walking'):
    base_url = 'https://api.openrouteservice.org/v2/directions/'
    profiles = {
        'walking': 'foot-walking',
        'driving': 'driving-car',
        'cycling': 'cycling-regular'
    }
    profile= profiles.get(travel_mode, 'foot-walking')
    return f"{base_url}{profile}/geojson"


def get_ors_route(coordinates, travel_mode = 'walking'):
    if len(coordinates) < 2:
        return None
    if not api_key_ors:
        print("ORS Request Error: ORS_API_KEY is not configured.")
        return None
    ors_url = get_ors_url_mode(travel_mode)

    headers = {
        'Authorization': api_key_ors,
        'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8', #API call to get ORS routes
        'Content-Type': 'application/json; charset=utf-8'
    }
    try: #error handling, in case API call does not work - TRY block is if the call works as planned
        response = requests.post(ors_url, headers=headers, json={'coordinates': coordinates}) #API response to call stored here
        response.raise_for_status() #checks HTTP status
        data = response.json()
        # Correctly parse the 'features' key from the ORS response
        if data and data.get('features'):
            return data['features'][0]
        else:
            print("ORS Response Error: 'features' key not found or is empty in the response.")
            return None
    except requests.exceptions.RequestException as e: #catches data connection/HTTP errors
        print(f"ORS Request Error: {e}")
        return None
    except (IndexError, KeyError, ValueError) as e: #catches errors with data parsing from data sent back by API
        print(f"ORS Response Error: Could not parse route from response. {e}")
        return None


def decode_polyline(encoded):
    index = 0
    lat = 0
    lng = 0
    coordinates = []
    while index < len(encoded):
        shift = 0
        result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        delta_lat = ~(result >> 1) if result & 1 else (result >> 1)
        lat += delta_lat

        shift = 0
        result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        delta_lng = ~(result >> 1) if result & 1 else (result >> 1)
        lng += delta_lng

        coordinates.append([lng / 1e5, lat / 1e5])
    return coordinates


def _google_transit_request(origin, destination):
    params = {
        "origin": origin,
        "destination": destination,
        "mode": "transit",
        "departure_time": "now",
        "key": api_key_google,
    }
    response = requests.get(
        "https://maps.googleapis.com/maps/api/directions/json",
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def get_google_transit_route(coordinates):
    if len(coordinates) < 2:
        return None
    if not api_key_google:
        print("Google Directions Error: GOOGLE_MAPS_API_KEY is not configured.")
        return None

    combined_coords = []
    total_distance = 0

    for start, end in zip(coordinates[:-1], coordinates[1:]):
        origin = f"{start[1]},{start[0]}"
        destination = f"{end[1]},{end[0]}"
        data = _google_transit_request(origin, destination)
        if data.get("status") != "OK":
            print(f"Google Directions Error: {data.get('status')}")
            return None

        routes = data.get("routes", [])
        if not routes:
            print("Google Directions Error: No routes found.")
            return None

        route = routes[0]
        overview = route.get("overview_polyline", {}).get("points")
        if not overview:
            print("Google Directions Error: Missing overview polyline.")
            return None

        segment_coords = decode_polyline(overview)
        if combined_coords and segment_coords:
            if combined_coords[-1] == segment_coords[0]:
                segment_coords = segment_coords[1:]
        combined_coords.extend(segment_coords)

        for leg in route.get("legs", []):
            if leg.get("distance"):
                total_distance += leg["distance"].get("value", 0)

    if not combined_coords:
        return None

    return {
        "distance": total_distance,
        "geometry": {
            "type": "LineString",
            "coordinates": combined_coords,
        },
    }


def get_route_data(coordinates, travel_mode='walking'):
    if travel_mode == 'transit':
        return get_google_transit_route(coordinates)

    ors_route = get_ors_route(coordinates, travel_mode)
    if not ors_route:
        return None

    accurate_distance = 0
    if 'properties' in ors_route and 'summary' in ors_route['properties']:
        accurate_distance = ors_route['properties']['summary']['distance']

    return {
        'distance': accurate_distance,
        'geometry': ors_route.get('geometry')
    }


# Objective Functions, distance and satisfaction

def compute_distance(individual, locations_dict): #Calculates the total distance of a route (to be minimized). Calculates the total straight-line distance between the points - ORS route distance for 100 routes would call the api a lot = computationally intensive
    if not individual or len(individual) < 2:
        return float('inf')
    distance = 0
    for i in range(len(individual) - 1):
        loc1 = locations_dict[individual[i]]
        loc2 = locations_dict[individual[i + 1]]
        distance += np.sqrt((loc1['latitude'] - loc2['latitude']) ** 2 + (loc1['longitude'] - loc2['longitude']) ** 2)
    return distance

def compute_satisfaction(individual, locations_dict, user_preferences):
    """
    Calculates a combined satisfaction score for a route based on two factors:
    1. How well the locations match the user's category preferences.
    2. The average sentiment score of all locations in the route.
    """
    if not individual:
        return 0

    # This score is 1 if a location matches the user's preference, and 0 otherwise.
    category_match_score = sum(1 for loc_id in individual if locations_dict[loc_id]['category_id'] in user_preferences)
    category_satisfaction = category_match_score / len(individual) if individual else 0

    # This aggregates the pre-calculated sentiment scores for each location in the route.
    route_sentiments = [locations_dict[loc_id].get('sentiment', 0) for loc_id in individual]
    sentiment_satisfaction = sum(route_sentiments) / len(route_sentiments) if route_sentiments else 0

    # The final score is the average of the category and sentiment satisfactions.
    combined_satisfaction = (category_satisfaction + sentiment_satisfaction) / 2

    return combined_satisfaction

# DEAP Algorithm Set up - creating individuals

def generate_individual(location_ids, required_stops): #Generates an individual route with a variable number of locations - come back to this
    individual = list(required_stops)

    remaining_slots = random.randint(min_locations, max_locations) - len(individual)

    if remaining_slots > 0:
        possible_additions = [loc_id for loc_id in location_ids if loc_id not in individual]
        if len(possible_additions) >= remaining_slots:
            individual.extend(random.sample(possible_additions, remaining_slots))

    random.shuffle(individual)
    return individual

def enforce_required_stops(individual, required_stops): #Ensures required stops always remain in the individual
    required_set = set(required_stops)
    for stop_id in required_stops:
        if stop_id not in individual:
            individual.append(stop_id)

    if len(individual) > max_locations:
        removable = [loc for loc in individual if loc not in required_set]
        while len(individual) > max_locations and removable:
            individual.remove(removable.pop())
    return individual


#Crossover and Mutation Operators

def ox_crossover(ind1, ind2): #A robust ordered crossover (OX) for variable-length routes - combines 2 parent routes (ind1 and ind2) to create a child route
    parent1, parent2 = (ind1, ind2) if len(ind1) < len(ind2) else (ind2, ind1) #shorter route is parent 1, longer route is parent 2
    slice_start, slice_end = sorted(random.sample(range(len(parent1)), 2)) #selects two indices in parent 1, orders them and uses that 'slice' of the parent to add to the child
    child_slice = parent1[slice_start:slice_end + 1] #starts to create child by copying ids between indices specified in parent 1
    remaining = [item for item in parent2 if item not in child_slice] #locations in parent 2 that are not already in the child_slice, prevents duplicates
    child = remaining[:slice_start] + child_slice + remaining[slice_start:]
    if len(child) > max_locations:
        child = child[:max_locations]
    elif len(child) < min_locations: #if child is less than 5 locations, adds more from parent2 (the longer individual) until it gets to 5 (min length)
        needed = min_locations - len(child)
        for loc in parent2:
            if needed == 0: break
            if loc not in child:
                child.append(loc)
                needed -= 1
    ind1[:] = child #ind(ividual)1 becomes the child, ind2 is unchanged
    ind2[:] = ind2
    return ind1, ind2


def random_mutation(individual, all_location_ids, required_stops): #Selects one of three mutation types (add, remove, or swap) at random, suggested in NSGA 22 July File
    mutable_indices = [i for i, loc_id in enumerate(individual) if loc_id not in required_stops]
    rand = random.random()
    if rand < 0.33 and len(individual) < max_locations: #add mutation
        possible_additions = [loc for loc in all_location_ids if loc not in individual]
        if possible_additions:
            individual.append(random.choice(possible_additions)) #randomly appends a new location to the end of the individual (ie the route)
    elif rand < 0.66 and len(individual) > min_locations and mutable_indices: #remove mutation
        index_to_remove = random.choice(mutable_indices)
        individual.pop(index_to_remove)
    elif mutable_indices: #swap mutation
        idx_to_replace = random.choice(mutable_indices)
        possible_swaps = [loc for loc in all_location_ids if loc not in individual]
        if possible_swaps:
            individual[idx_to_replace] = random.choice(possible_swaps)
    return individual


#Runs NSGA-II Algorithm and generates routes

def get_optimized_routes(user_preferences, required_stops=[], travel_mode = 'walking'): #Runs the NSGA-II algorithm to find the best routes
    user_preferences = [int(p) for p in user_preferences]
    required_stops = [int(rs) for rs in required_stops]

    locations_dict = locations_to_dict()
    for stop_id in required_stops:
        if stop_id not in locations_dict:
            print(f"Error: Required stop {stop_id} is not in the selected category.")
            return []

    location_ids = list(locations_dict.keys())

    toolbox = base.Toolbox() #sets up DEAP Toolbox - holds each function defined above so can be used by NSGA-II algorithm, ie whenever a new individual needs to be created, use line145
    toolbox.register("individual", tools.initIterate, creator.Individual, lambda: generate_individual(location_ids, required_stops))
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("mate", ox_crossover) #DEAP alias for crossover is 'mate'
    toolbox.register("mutate", random_mutation, all_location_ids=location_ids, required_stops=required_stops)
    toolbox.register("select", tools.selNSGA2)
    toolbox.register("evaluate", lambda ind: (
        compute_distance(ind, locations_dict),
        compute_satisfaction(ind, locations_dict, user_preferences)
    ))

    #Learning Loop
    pop = toolbox.population(n=population) #creates 100 random routes

    # Evaluate the first generation - goes through database evaluating fitness of these routes
    for ind in pop:
        if ind: ind.fitness.values = toolbox.evaluate(ind)

    # Main evolution loop
    for gen in range(no_of_generations):
        offspring = toolbox.select(pop, len(pop)) #chooses best individuals from current population to be parents
        offspring = [toolbox.clone(ind) for ind in offspring]   #these parents are cloned so the next generation can be changed without affecting the original parents

        for child1, child2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < crossover:
                toolbox.mate(child1, child2) #if condition met, performs order crossover (see above)
                del child1.fitness.values
                del child2.fitness.values #deletes old fitness values, so they can be updated when order crossover occurs
            enforce_required_stops(child1, required_stops)
            enforce_required_stops(child2, required_stops)

        for mutant in offspring:
            if random.random() < mutation:
                toolbox.mutate(mutant)
                del mutant.fitness.values
            enforce_required_stops(mutant, required_stops)

        invalid_ind = [ind for ind in offspring if not ind.fitness.valid] #this block updates all fitness values with the updated ones
        for ind in invalid_ind:
            if ind: ind.fitness.values = toolbox.evaluate(ind)

        pop = toolbox.select(pop + offspring, population)
        # Print progress every 10 generations
        if (gen + 1) % 10 == 0:
            print(f"Generation {gen + 1}/{no_of_generations} complete.")

    pareto_front = tools.ParetoFront()
    pareto_front.update(pop) #updates Pareto Front with the new non-dominated solutions from the most recent evaluation

    valid_solutions = [ind for ind in pareto_front if ind]
    if not valid_solutions:
        print("!!! No valid solutions found in Pareto front. Returning empty list.")
        return []

    sorted_pareto = sorted(valid_solutions, key=lambda x: x.fitness.values[1], reverse=True) #sorts solutions in the pareto front in descending order by satisfaction, so best ones appear first

    if len(sorted_pareto) < 3: #fixes bug where less than 3 solutions are suggested by algorithm, changes to ONLY 3 (as per requirements)
        extras = [ind for ind in sorted(pop, key=lambda x: x.fitness.values[1], reverse=True)
                  if ind not in sorted_pareto]
        sorted_pareto.extend(extras[:3 - len(sorted_pareto)])
    top_routes = sorted_pareto[:3]

    routes = []
    print(f"\n--- Top {min(3, len(sorted_pareto))} Routes for {travel_mode}---")
    for i, ind in enumerate(top_routes):
        coordinates = [[locations_dict[loc_id]['longitude'], locations_dict[loc_id]['latitude']] for loc_id in ind]
        route_data = get_route_data(coordinates, travel_mode) or {}
        accurate_distance = route_data.get('distance', 0)

        route_info = {
            'id': i + 1,
            'distance': accurate_distance,
            'satisfaction': ind.fitness.values[1],
            'locations': [
                {
                    'id': loc_id,
                    'name': locations_dict[loc_id]['name'],
                    'latitude': locations_dict[loc_id]['latitude'],
                    'longitude': locations_dict[loc_id]['longitude'],
                    'color': get_category_colour(locations_dict[loc_id]['category_id']),
                } for loc_id in ind
            ],
            'geometry': route_data.get('geometry')
        }
        routes.append(route_info)
        print(
            f"Route {i + 1}: Satisfaction = {route_info['satisfaction']:.2f}, Distance = {route_info['distance']:.2f}, Locations ({len(route_info['locations'])}): {[loc['name'] for loc in route_info['locations']]}")

    print("--- Optimization Finished ---")
    return routes

def recalculate_route_geometry(location_ids, travel_mode='walking'): #Takes a list of location IDs and a travel mode, returns route details.
    locations_dict = locations_to_dict()
    coordinates = []
    for loc_id in location_ids:
        int_loc_id = int(loc_id)
        if int_loc_id in locations_dict:
            coordinates.append([locations_dict[int_loc_id]['longitude'], locations_dict[int_loc_id]['latitude']])

    if len(coordinates) < 2:
        return None

    route_data = get_route_data(coordinates, travel_mode)
    if not route_data:
        return None

    return {
        'distance': route_data.get('distance', 0),
        'geometry': route_data.get('geometry')
    }
