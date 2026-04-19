import random
import csv
import os
from typing import List, Tuple
from interfaces import SelectionStrategy, CrossoverStrategy, MutationStrategy, FitnessFunction, ParallelBackend


class ModularGA:
    def __init__(self,
                 selection: SelectionStrategy,
                 crossover: CrossoverStrategy,
                 mutation: MutationStrategy,
                 fitness: FitnessFunction,
                 backend: ParallelBackend,
                 log_file: str = "ga_metrics.csv",
                 initialize_log: bool = True):
        """Initialize the Genetic Algorithm with strategy injection."""
        self.selection = selection
        self.crossover = crossover
        self.mutation = mutation
        self.fitness = fitness
        self.backend = backend
        self.log_file = log_file
        self.initialize_log = initialize_log

        # Init the CSV headers if it's new
        if self.initialize_log and not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                headers = ["Generation", "Best_Fitness", "Average_Fitness",
                           "Worst_Fitness"] + [f"Top_{i}_Genome" for i in range(1, 6)]
                writer.writerow(headers)

    def _generate_initial_population(self, pop_size: int, genome_length: int, min_val: int = -100, max_val: int = 100) -> List[List[int]]:
        """Creates the initial population of integer lists."""
        return [[random.randint(min_val, max_val) for _ in range(genome_length)] for _ in range(pop_size)]

    def run(self, generations: int, pop_size: int = 100, genome_length: int = 8, min_gene_val: int = -100, max_gene_val: int = 100, mutation_prob: float = 0.2, population: List[List[int]] = None) -> List[List[int]]:
        """Execute the genetic algorithm search."""
        if population is None:
            population = self._generate_initial_population(
                pop_size, genome_length, min_gene_val, max_gene_val)

        for generation in range(generations):
            # 0. Inject current population into fitness function if needed (for tournaments/k-matchups)
            if hasattr(self.fitness, 'population'):
                self.fitness.population = list(population)

            if hasattr(self.fitness, 'set_generation_index'):
                self.fitness.set_generation_index(generation)

            # 1. Map Evaluation (Delegated to Backend)
            fitnesses = self.fitness.evaluate_population(
                population, self.backend)

            # 2. Extract metrics
            best_fitness = max(fitnesses)
            worst_fitness = min(fitnesses)
            avg_fitness = sum(fitnesses) / len(fitnesses)

            # Sort population by fitness to get top 5 genomes
            pop_with_fitness = list(zip(population, fitnesses))
            pop_with_fitness.sort(key=lambda x: x[1], reverse=True)
            top_5_genomes = [str(x[0]) for x in pop_with_fitness[:5]]
            while len(top_5_genomes) < 5:
                top_5_genomes.append("")

            # 3. Log Generation State (append to CSV)
            with open(self.log_file, "a", newline='') as f:
                writer = csv.writer(f)
                writer.writerow([generation, best_fitness,
                                avg_fitness, worst_fitness] + top_5_genomes)

            print(
                f"Gen {generation} | Best: {best_fitness:.2f} | Avg: {avg_fitness:.2f} | Worst: {worst_fitness:.2f}")

            # 4. Generate new population
            new_population = []

            # Keep best individual (Elitism - Optional, doing it simply here)
            best_index = fitnesses.index(best_fitness)
            new_population.append(list(population[best_index]))

            # Generate the rest
            while len(new_population) < pop_size:
                # Select parents
                parents = self.selection.select(population, fitnesses, 2)
                parent1, parent2 = parents[0], parents[1]

                # Crossover
                child1, child2 = self.crossover.crossover(parent1, parent2)

                # Mutation
                if random.random() < mutation_prob:
                    child1 = self.mutation.mutate(child1)
                if random.random() < mutation_prob:
                    child2 = self.mutation.mutate(child2)

                new_population.append(child1)
                if len(new_population) < pop_size:
                    new_population.append(child2)

            population = new_population

        return population
