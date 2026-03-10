import random
from typing import List, Tuple
from interfaces import SelectionStrategy, CrossoverStrategy, MutationStrategy, FitnessFunction


# =========================== SelectionStrategy ===========================


class RandomSelection(SelectionStrategy):
    """Simple random selection of parents. For MVP phase."""

    def select(self, population: List[List[int]], fitnesses: List[float], num_parents: int) -> List[List[int]]:
        return random.choices(population, k=num_parents)


class RouletteWheelSelection(SelectionStrategy):
    """
    Roulette wheel selection maps all the possible strings onto a wheel with a portion of the
    wheel allocated to them according to their fitness value.
    Note: Requires fitness values to be strictly positive to work correctly.
    """

    def select(self, population: List[List[int]], fitnesses: List[float], num_parents: int) -> List[List[int]]:
        # Shift fitnesses so the minimum is a small positive value if there are negatives
        # This guarantees everyone has a strictly positive fitness portion
        min_fit = min(fitnesses)
        if min_fit <= 0:
            adjusted_fitnesses = [f - min_fit + 1.0 for f in fitnesses]
        else:
            adjusted_fitnesses = fitnesses

        # random.choices implements roulette wheel natively using the 'weights' parameter
        return random.choices(population, weights=adjusted_fitnesses, k=num_parents)


# =========================== CrossoverStrategy ===========================


class SinglePointCrossover(CrossoverStrategy):
    """Crosses over two parents at a single, random point."""

    def crossover(self, parent1: List[int], parent2: List[int]) -> Tuple[List[int], List[int]]:
        if len(parent1) < 2:
            return list(parent1), list(parent2)

        point = random.randint(1, len(parent1) - 1)
        child1 = parent1[:point] + parent2[point:]
        child2 = parent2[:point] + parent1[point:]

        return child1, child2


class ArithmeticCrossover(CrossoverStrategy):
    """
    Creates offspring via a linear combination of two parents.
    Specifically: 
    child1 = alpha * parent1 + (1 - alpha) * parent2
    child2 = (1 - alpha) * parent1 + alpha * parent2
    Since genes in this framework are integers, the results are converted to integers.
    """

    def __init__(self, alpha: float = None):
        # If alpha is None, a random alpha between 0 and 1 is chosen per crossover
        self.alpha = alpha

    def crossover(self, parent1: List[int], parent2: List[int]) -> Tuple[List[int], List[int]]:
        alpha = self.alpha if self.alpha is not None else random.random()

        child1 = []
        child2 = []

        for g1, g2 in zip(parent1, parent2):
            c1_val = int(round(alpha * g1 + (1 - alpha) * g2))
            c2_val = int(round((1 - alpha) * g1 + alpha * g2))
            child1.append(c1_val)
            child2.append(c2_val)

        return child1, child2


# =========================== MutationStrategy ===========================


class RandomIntMutation(MutationStrategy):
    """Mutates a random gene in the genome to a random integer within a specified range."""

    def __init__(self, mutation_rate: float = 0.1, min_val: int = 0, max_val: int = 10):
        self.mutation_rate = mutation_rate
        self.min_val = min_val
        self.max_val = max_val

    def mutate(self, individual: List[int]) -> List[int]:
        mutated = list(individual)
        for i in range(len(mutated)):
            if random.random() < self.mutation_rate:
                mutated[i] = random.randint(self.min_val, self.max_val)
        return mutated


# =========================== FitnessFunction ===========================


class DummyFitness(FitnessFunction):
    """Placeholder fitness function that encourages sums of gene values to be close to 100."""

    def evaluate(self, individual: List[int]) -> float:
        return -abs(100 - sum(individual))
