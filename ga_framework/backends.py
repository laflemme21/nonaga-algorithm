from typing import List, Callable
import concurrent.futures
from interfaces import ParallelBackend


class MasterSlaveBackend(ParallelBackend):
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers

    def map_evaluate(self, evaluate_func: Callable[[List[int]], float], population: List[List[int]]) -> List[float]:
        # Using a ProcessPoolExecutor to map the evaluate function to the population
        # This provides a Master-Slave parallelization architecture.
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            fitnesses = list(executor.map(evaluate_func, population))
        return fitnesses
