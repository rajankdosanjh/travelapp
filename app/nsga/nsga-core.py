#this algorithm uses the DEAP library, built using my own code and the DEAP documentation
import random
import numpy as np
from deap import base, creator, tools
import requests
from flask import request, jsonify
from app import app
from app.models import Location

ors_api_key = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImRhNjdmYWZhYmE2ZTQ1MzA5ZjNlMDBmYTllMjkwMGJjIiwiaCI6Im11cm11cjY0In0='
ors_api_url = 'https://api.openrouteservice.org/v2/directions/foot-walking/geojson'

# NSGA-II Algorithm parameters
MIN_LOCATIONS = 5  # Minimum stops per route
MAX_LOCATIONS = 8  # Maximum stops per route
POPULATION_SIZE = 100  # Number of candidate solutions in each generation
GENERATIONS = 50  # Number of evaluation iterations
CXPB = 0.9  # 90% chance of crossover
MUTPB = 0.1  # 10% chance of insert mutation

def get_locations_dict(): #Fetch locations from data.sqlite and return as a dictionary
    with app.app_context():
        locations = Location.query.all()
        return {
            loc.id: {
                'name': loc.name,
                'latitude': loc.latitude,
                'longitude': loc.longitude,
                'category': loc.category,
                'tiktok_rating': loc.tiktok_rating
            }
            for loc in locations
        }

LOCATIONS = get_locations_dict()  # creates a dictionary of locations, so data can be accessed as fast as possible


#Initializing the NSGA-II Algorithm
creator.create("FitnessMulti", base.Fitness, weights=(-1.0, -1.0))  # Define multi-objective fitness (minimize distance, maximize satisfaction)

# An individual is a list of location IDs with a fitness attribute
creator.create("Individual", list, fitness=creator.FitnessMulti)

def generate_individual(): #Create a random route with 5-8 unique locations
    loc_ids = list(LOCATIONS.keys())
    size = random.randint(MIN_LOCATIONS, MAX_LOCATIONS)  # generates the random route length, based on parameters from 'NSGA-II Algorithm parameters' block
    return random.sample(loc_ids, size)

# Toolbox setup
toolbox = base.Toolbox()
toolbox.register("individual", tools.initIterate, creator.Individual, generate_individual)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

def mutInsert(individual, indpb=0.1): #function to implement Insert Mutation, as per NSGA 22 July Document
    if random.random() < indpb and len(individual) > 1:
        idx1, idx2 = random.sample(range(len(individual)), 2)  # Pick 2 distinct locations (indices)
        gene = individual.pop(idx1)  # Remove location at index 1
        individual.insert(idx2, gene)  # Reinsert the location at index 1 at index 2
    return individual,  # Return as a tuple (DEAP convention)


def cxOrdered(ind1, ind2): #Ordered Crossover: Preserves relative order from parents
    size = min(len(ind1), len(ind2))
    a, b = sorted(random.sample(range(size), 2))

    def ox(parent1, parent2):
        child = [None] * size
        child[a:b] = parent1[a:b]  # Keep segment from parent1
        remaining = [item for item in parent2 if item not in child]  # Fill from parent2
        ptr = b % size
        for item in remaining:
            child[ptr] = item
            ptr = (ptr + 1) % size
        return child

    ind1[:], ind2[:] = ox(ind1, ind2), ox(ind2, ind1)  # Update both children
    return ind1, ind2

def haversine_distance(lat1, lon1, lat2, lon2): #Calculates distance between two points (km) using haversine formula, quickest way to calculate approximate distance for evolution
    earth_radius = 6371  # Earth radius in km
    distance_lat = np.radians(lat2 - lat1)
    distance_lon = np.radians(lon2 - lon1)
    a = (np.sin(distance_lat/2)**2 + np.cos(np.radians(lat1)) *
         np.cos(np.radians(lat2)) * np.sin(distance_lon/2)**2)
    return earth_radius * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

def compute_distance(individual): #Calculate total route distance
    total = 0
    for i in range(len(individual)-1):
        loc1 = LOCATIONS[individual[i]]  # Current location
        loc2 = LOCATIONS[individual[i+1]]  # Next location
        total += haversine_distance(
            loc1['latitude'], loc1['longitude'],
            loc2['latitude'], loc2['longitude']
        )
    return total

def compute_satisfaction(individual, user_prefs): #Calculate % of locations matching user preferences
    matches = sum(1 for loc_id in individual
                 if LOCATIONS[loc_id]['category'] in user_prefs)
    return matches / len(individual)

def evaluate(individual, user_prefs): #NSGA-II evaluation: Returns (distance, -satisfaction)
    distance = compute_distance(individual)
    satisfaction = compute_satisfaction(individual, user_prefs)
    return distance, -satisfaction  # Minimize both


def run_nsga(user_prefs): #Execute NSGA-II using above functions
    pop = toolbox.population(n=POPULATION_SIZE)  # Initialize population

    # Evaluate initial population
    fitnesses = [toolbox.evaluate(ind, user_prefs) for ind in pop]
    for ind, fit in zip(pop, fitnesses):
        ind.fitness.values = fit

    for gen in range(GENERATIONS):  # Evolution loop
        # Selection
        offspring = toolbox.select(pop, len(pop))  # Tournament selection
        offspring = [toolbox.clone(ind) for ind in offspring]  # Clone parents

        # Crossover
        for child1, child2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < CXPB:  # 90% chance
                toolbox.mate(child1, child2)  # Apply OX crossover
                del child1.fitness.values  # Force re-evaluation
                del child2.fitness.values

        # Mutation (Insert)
        for mutant in offspring:
            toolbox.mutate(mutant)  # Calls mutInsert
            del mutant.fitness.values

        # Evaluate new individuals
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = [toolbox.evaluate(ind, user_prefs) for ind in invalid_ind]
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit

        # Next generation
        pop = toolbox.select(pop + offspring, POPULATION_SIZE)  # Elitism

    return pop

def get_ors_route(coordinates): #Fetch actual walking path from ORS - use API and url
    headers = {'Authorization': ors_api_key}
    body = {'coordinates': coordinates, 'geometry': True}
    try:
        response = requests.post(ors_api_url, headers=headers, json=body)
        return response.json()['routes'][0]  # Extract route data
    except Exception as e:
        print(f"ORS Error: {e}")
        return None