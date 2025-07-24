#this algorithm uses the DEAP library, built using my own code and the DEAP documentation
from deap import base, creator, tools
import random

import numpy as np
from numpy.ma import count
from pip._internal import locations

from app import app, data
from app.models import Location



# --- Configuration ---
ors_api_key = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImRhNjdmYWZhYmE2ZTQ1MzA5ZjNlMDBmYTllMjkwMGJjIiwiaCI6Im11cm11cjY0In0='
ors_api_url = 'https://api.openrouteservice.org/v2/directions/foot-walking/geojson'
minimum_locations = 5
maximum_locations = 8
pop_size = count(locations)
generations = 50 #no of iterations
crossover = 0.9
mutation = 0.1

def get_locations_dict():
    with app.app_context():
        locations = Location.query.all()
        return {loc.id: {
            'name': loc.name,
            'latitude': loc.latitude,
            'longitude': loc.longitude,
            'category': loc.category,
            'tiktok_rating': loc.tiktok_rating
        } for loc in locations}

def get_category_color(category):
    color_map = {
        1: '#FF0000',  # Food - Red
        2: '#0000FF',  # History - Blue
        3: '#00FF00',  # Shopping - Green
        4: '#FFA500',  # Nature - Orange
        5: '#800080',  # Art - Purple
        6: '#FFFF00'   # Nightlife - Yellow
    }
    return color_map.get(category, '#999999')  # Default gray

def generate_individual():
    location_ids = list(get_locations_dict().keys())
    return random.sample(location_ids, random.randint(minimum_locations, maximum_locations))


def mutInsert(individual, indpb=0.1):
    if random.random() < indpb and len(individual) > 1:
        idx1, idx2 = random.sample(range(len(individual)), 2)
        individual.insert(idx2, individual.pop(idx1))
    return individual,


def haversine_distance(lat1, lon1, lat2, lon2): #unsure if i need this if i am using the walking distance
    radius = 6371
    latitude_distance = np.radians(lat2 - lat1)
    longitude_distance = np.radians(lon2 - lon1)
    a = (np.sin(latitude_distance / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(longitude_distance / 2) ** 2)
    return radius * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def compute_distance(individual):
    locations = get_locations_dict()
    return sum(
        haversine_distance(
            locations[individual[i]]['latitude'], locations[individual[i]]['longitude'],
            locations[individual[i + 1]]['latitude'], locations[individual[i + 1]]['longitude']
        ) for i in range(len(individual) - 1)
    )


def compute_satisfaction(individual, user_prefs):
    locations = get_locations_dict()
    matches = sum(1 for loc_id in individual if locations[loc_id]['category'] in user_prefs)
    return matches / len(individual)


def get_ors_route(coordinates):
    headers = {'Authorization': ors_api_key}
    try:
        response = requests.post(ors_api_url, headers=headers, json={'coordinates': coordinates})
        return response.json()['routes'][0]
    except Exception as e:
        print(f"ORS Error: {e}")
        return None


# --- Optimization Controller ---
def get_optimized_routes(user_prefs):
    locations = get_locations_dict()


    # DEAP setup
    creator.create("FitnessMulti", base.Fitness, weights=(-1.0, -1.0))
    creator.create("Individual", list, fitness=creator.FitnessMulti)

    toolbox = base.Toolbox()
    toolbox.register("individual", tools.initIterate, creator.Individual, generate_individual)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("mate", tools.cxOrdered)
    toolbox.register("mutate", mutInsert, indpb=mutation)
    toolbox.register("select", tools.selNSGA2)

    def evaluate(individual):
        distance = compute_distance(individual)
        satisfaction = compute_satisfaction(individual, user_prefs)
        return distance, -satisfaction

    toolbox.register("evaluate", evaluate)

    # Run algorithm
    pop = toolbox.population(n=pop_size)
    for ind in pop:
        ind.fitness.values = toolbox.evaluate(ind)

    for gen in range(generations):
        offspring = toolbox.select(pop, len(pop))
        offspring = [toolbox.clone(ind) for ind in offspring]

        # Crossover
        for child1, child2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < crossover:
                toolbox.mate(child1, child2)
                del child1.fitness.values
                del child2.fitness.values

        # Mutation
        for mutant in offspring:
            toolbox.mutate(mutant)
            del mutant.fitness.values

        # Evaluate
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        for ind in invalid_ind:
            ind.fitness.values = toolbox.evaluate(ind)

        pop = toolbox.select(pop + offspring, pop_size)

    # Get top 3 routes
    pareto_front = tools.ParetoFront()
    pareto_front.update(pop)

    routes = []
    for i, ind in enumerate(list(pareto_front)[:3]):
        coordinates = [
            [locations[loc_id]['longitude'], locations[loc_id]['latitude']]
            for loc_id in ind
        ]
        ors_route = get_ors_route(coordinates) if len(coordinates) > 1 else None

        routes.append({
            'id': i + 1,
            'distance': ind.fitness.values[0],
            'satisfaction': -ind.fitness.values[1],
            'locations': [{
                'id': loc_id,
                'name': locations[loc_id]['name'],
                'latitude': locations[loc_id]['latitude'],
                'longitude': locations[loc_id]['longitude'],
                'category': locations[loc_id]['category'],  # Include category
                'color': get_category_color(locations[loc_id]['category'])  # Add colour
            } for loc_id in ind],
            'geometry': ors_route['geometry'] if ors_route else None
        })

    return routes