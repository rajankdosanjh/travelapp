#this algorithm uses the DEAP library, built using my own code and the DEAP documentation
from deap import base, creator, tools
import random
import numpy as np
from app import app
from app.models import Location

# --- Configuration ---
ORS_API_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImRhNjdmYWZhYmE2ZTQ1MzA5ZjNlMDBmYTllMjkwMGJjIiwiaCI6Im11cm11cjY0In0='
ORS_API_URL = 'https://api.openrouteservice.org/v2/directions/foot-walking/geojson'
MIN_LOCATIONS = 5
MAX_LOCATIONS = 8
POPULATION_SIZE = 100
GENERATIONS = 50
CXPB = 0.9
MUTPB = 0.1

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

def generate_individual():
    loc_ids = list(get_locations_dict().keys())
    return random.sample(loc_ids, random.randint(MIN_LOCATIONS, MAX_LOCATIONS))


def mutInsert(individual, indpb=0.1):
    if random.random() < indpb and len(individual) > 1:
        idx1, idx2 = random.sample(range(len(individual)), 2)
        individual.insert(idx2, individual.pop(idx1))
    return individual,


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dLat = np.radians(lat2 - lat1)
    dLon = np.radians(lon2 - lon1)
    a = (np.sin(dLat / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dLon / 2) ** 2)
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def compute_distance(individual):
    LOCATIONS = get_locations_dict()
    return sum(
        haversine_distance(
            LOCATIONS[individual[i]]['latitude'], LOCATIONS[individual[i]]['longitude'],
            LOCATIONS[individual[i + 1]]['latitude'], LOCATIONS[individual[i + 1]]['longitude']
        ) for i in range(len(individual) - 1)
    )


def compute_satisfaction(individual, user_prefs):
    LOCATIONS = get_locations_dict()
    matches = sum(1 for loc_id in individual if LOCATIONS[loc_id]['category'] in user_prefs)
    return matches / len(individual)


def get_ors_route(coordinates):
    headers = {'Authorization': ORS_API_KEY}
    try:
        response = requests.post(ORS_API_URL, headers=headers, json={'coordinates': coordinates})
        return response.json()['routes'][0]
    except Exception as e:
        print(f"ORS Error: {e}")
        return None


# --- Optimization Controller ---
def get_optimized_routes(user_prefs):
    """Main function to call from views.py"""
    LOCATIONS = get_locations_dict()

    # DEAP setup
    creator.create("FitnessMulti", base.Fitness, weights=(-1.0, -1.0))
    creator.create("Individual", list, fitness=creator.FitnessMulti)

    toolbox = base.Toolbox()
    toolbox.register("individual", tools.initIterate, creator.Individual, generate_individual)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("mate", tools.cxOrdered)
    toolbox.register("mutate", mutInsert, indpb=MUTPB)
    toolbox.register("select", tools.selNSGA2)

    def evaluate(individual):
        distance = compute_distance(individual)
        satisfaction = compute_satisfaction(individual, user_prefs)
        return distance, -satisfaction

    toolbox.register("evaluate", evaluate)

    # Run algorithm
    pop = toolbox.population(n=POPULATION_SIZE)
    for ind in pop:
        ind.fitness.values = toolbox.evaluate(ind)

    for gen in range(GENERATIONS):
        offspring = toolbox.select(pop, len(pop))
        offspring = [toolbox.clone(ind) for ind in offspring]

        # Crossover
        for child1, child2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < CXPB:
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

        pop = toolbox.select(pop + offspring, POPULATION_SIZE)

    # Get top 3 routes
    pareto_front = tools.ParetoFront()
    pareto_front.update(pop)

    routes = []
    for i, ind in enumerate(list(pareto_front)[:3]):
        coordinates = [
            [LOCATIONS[loc_id]['longitude'], LOCATIONS[loc_id]['latitude']]
            for loc_id in ind
        ]
        ors_route = get_ors_route(coordinates) if len(coordinates) > 1 else None

        routes.append({
            'id': i + 1,
            'distance': ind.fitness.values[0],
            'satisfaction': -ind.fitness.values[1],
            'locations': [{'id': loc_id, **LOCATIONS[loc_id]} for loc_id in ind],
            'geometry': ors_route['geometry'] if ors_route else None
        })

    return routes