from abc import ABC, abstractmethod
from typing import List, Tuple, Callable, Any


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

    def evaluate_population(self, population: List[List[int]], backend: "ParallelBackend") -> List[float]:
        """Default population evaluation delegates to backend.map_evaluate."""
        return backend.map_evaluate(self.evaluate, population)


class ParallelBackend(ABC):
    """Interface handling the distribution of tasks or populations."""
    @abstractmethod
    def map_evaluate(self, evaluate_func: Callable[[List[int]], float], population: List[List[int]]) -> List[float]:
        pass

    @abstractmethod
    def map_tasks(self, task_func: Callable[[Any], Any], tasks: List[Any]) -> List[Any]:
        """Maps a generic task function over an input task list in parallel."""
        pass
