#this algorithm uses the DEAP library, built using my own code and the DEAP documentation
import random
from deap import base, creator, tools
import numpy as np

# === MOCK DATABASE ===
TOTAL_LOCATIONS = 30
LOCATIONS = {
    i: {
        "x": random.uniform(0, 100),
        "y": random.uniform(0, 100),
        "category": random.choice(["museum", "park", "gallery", "restaurant"])
    }
    for i in range(TOTAL_LOCATIONS)
}

USER_PREFS = {"museum", "gallery"}  # example preferred categories

# === EVOLUTIONARY PARAMETERS ===
MIN_LOC = 5
MAX_LOC = 8
CXPB = 0.9
MUTPB = 0.02
NGEN = 50
POP_SIZE = 100

LOCATION_IDS = list(LOCATIONS.keys())

# === OBJECTIVES ===
def compute_distance(route):
    dist = 0
    for i in range(len(route) - 1):
        loc1 = LOCATIONS[route[i]]
        loc2 = LOCATIONS[route[i + 1]]
        dx = loc1["x"] - loc2["x"]
        dy = loc1["y"] - loc2["y"]
        dist += (dx**2 + dy**2) ** 0.5
    return dist

def compute_satisfaction(route):
    matches = sum(1 for loc_id in route if LOCATIONS[loc_id]["category"] in USER_PREFS)
    return matches / len(route)  # normalized satisfaction score

def evaluate(individual):
    D = compute_distance(individual)
    S = compute_satisfaction(individual)
    return D, -S  # S is negated to convert max to min

# === REPRESENTATION ===
creator.create("FitnessMulti", base.Fitness, weights=(-1.0, -1.0))  # Minimize both
creator.create("Individual", list, fitness=creator.FitnessMulti)

toolbox = base.Toolbox()

def generate_individual():
    size = random.randint(MIN_LOC, MAX_LOC)
    return random.sample(LOCATION_IDS, size)

toolbox.register("individual", tools.initIterate, creator.Individual, generate_individual)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

# === ORDER CROSSOVER (OX) ===
def cxOrdered(ind1, ind2):
    size = min(len(ind1), len(ind2))
    a, b = sorted(random.sample(range(size), 2))

    def ox(parent1, parent2):
        child = [None] * size
        child[a:b] = parent1[a:b]
        p2_filtered = [item for item in parent2 if item not in child]
        i = b % size
        for item in p2_filtered:
            child[i] = item
            i = (i + 1) % size
        return child

    child1 = ox(ind1, ind2)
    child2 = ox(ind2, ind1)
    ind1[:], ind2[:] = child1, child2
    return ind1, ind2

# === INSERT MUTATION ===
def insert_mutation(ind):
    if len(ind) < 2:
        return ind,
    i, j = sorted(random.sample(range(len(ind)), 2))
    gene = ind.pop(j)
    ind.insert(i, gene)
    return ind,

# === REGISTER OPERATORS ===
toolbox.register("evaluate", evaluate)
toolbox.register("mate", cxOrdered)
toolbox.register("mutate", insert_mutation)
toolbox.register("select", tools.selNSGA2)

# === MAIN RUN LOOP ===
def main():
    pop = toolbox.population(n=POP_SIZE)

    # Initial evaluation
    for ind in pop:
        ind.fitness.values = toolbox.evaluate(ind)

    for gen in range(NGEN):
        offspring = tools.selTournamentDCD(pop, len(pop))
        offspring = [toolbox.clone(ind) for ind in offspring]

        for ind1, ind2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < CXPB:
                toolbox.mate(ind1, ind2)
                del ind1.fitness.values
                del ind2.fitness.values

        for ind in offspring:
            if random.random() < MUTPB:
                toolbox.mutate(ind)
                del ind.fitness.values

        # Re-evaluate invalid individuals
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        for ind in invalid_ind:
            ind.fitness.values = toolbox.evaluate(ind)

        pop = toolbox.select(pop + offspring, k=POP_SIZE)

        print(f"Generation {gen + 1} completed.")

    return pop

    # Print Pareto front

print("\nFinal Pareto Front:")
for ind in final_pop:
    print(f"Route: {ind}, Distance: {ind.fitness.values[0]:.2f}, Satisfaction: {-ind.fitness.values[1]:.2f}")
