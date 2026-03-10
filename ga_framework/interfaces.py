from abc import ABC, abstractmethod
from typing import List, Tuple, Callable


class SelectionStrategy(ABC):
    """Interface for choosing parents."""
    @abstractmethod
    def select(self, population: List[List[int]], fitnesses: List[float], num_parents: int) -> List[List[int]]:
        pass


class CrossoverStrategy(ABC):
    """Interface for reproduction."""
    @abstractmethod
    def crossover(self, parent1: List[int], parent2: List[int]) -> Tuple[List[int], List[int]]:
        pass


class MutationStrategy(ABC):
    """Interface for genetic alteration."""
    @abstractmethod
    def mutate(self, individual: List[int]) -> List[int]:
        pass


class FitnessFunction(ABC):
    """Decoupled interface for the objective function to allow isolated execution."""
    @abstractmethod
    def evaluate(self, individual: List[int]) -> float:
        pass


class ParallelBackend(ABC):
    """Interface handling the distribution of tasks or populations."""
    @abstractmethod
    def map_evaluate(self, evaluate_func: Callable[[List[int]], float], population: List[List[int]]) -> List[float]:
        pass
