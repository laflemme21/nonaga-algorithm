import random
from typing import List, Tuple, Dict, Any
from interfaces import SelectionStrategy, CrossoverStrategy, MutationStrategy, FitnessFunction


def _load_nonaga_modules() -> Tuple[Any, Any, int, int]:
    import os
    import sys

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    my_nonaga_path = os.path.join(project_root, "NonagaGame")
    if my_nonaga_path not in sys.path:
        sys.path.append(my_nonaga_path)

    from AI import AI
    from nonaga_logic import NonagaLogic
    from nonaga_constants import RED, BLACK
    return AI, NonagaLogic, RED, BLACK


def _simulate_nonaga_fixture(task: Dict[str, Any]) -> Dict[str, int]:
    """Simulates one fixture and returns winner plus participant indexes."""
    AI, NonagaLogic, RED, BLACK = _load_nonaga_modules()

    idx_red = task["idx_red"]
    idx_black = task["idx_black"]
    params_red = task["params_red"]
    params_black = task["params_black"]
    depth = task["depth"]
    max_moves = task["max_moves"]

    ai_red = AI(parameter=params_red, depth=depth, color=RED)
    ai_black = AI(parameter=params_black, depth=depth, color=BLACK)
    game = NonagaLogic(player_red=ai_red, player_black=ai_black, new_game=True)

    def has_available_moves(moves) -> bool:
        if moves is None:
            return False
        try:
            return len(moves) > 0
        except TypeError:
            return bool(moves)

    moves = 0
    while True:
        if moves > max_moves:
            return {"winner": -1, "idx_red": idx_red, "idx_black": idx_black}

        piece_moves = game.get_all_valid_piece_moves()
        tile_moves = game.get_all_valid_tile_moves()
        if (not has_available_moves(piece_moves)
                or not has_available_moves(tile_moves)):
            return {"winner": -1, "idx_red": idx_red, "idx_black": idx_black}

        current_color = game.get_current_player()
        active_ai = ai_red if current_color == RED else ai_black

        try:
            best_piece_move, best_tile_move = active_ai.get_best_move(game)
            if best_piece_move is None or best_tile_move is None:
                return {"winner": -1, "idx_red": idx_red, "idx_black": idx_black}

            game.move_piece_py(best_piece_move[0], best_piece_move[1])
            game.move_tile_py(best_tile_move[0], best_tile_move[1])
        except Exception:
            if current_color == RED:
                return {"winner": idx_black, "idx_red": idx_red, "idx_black": idx_black}
            return {"winner": idx_red, "idx_red": idx_red, "idx_black": idx_black}

        if game.check_win_condition_py(RED):
            return {"winner": idx_red, "idx_red": idx_red, "idx_black": idx_black}
        if game.check_win_condition_py(BLACK):
            return {"winner": idx_black, "idx_red": idx_red, "idx_black": idx_black}

        moves += 1


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
        # Shift fitnesses so the minimum is a small positive value if there are any non-positive fitnesses.
        # This translates negative/zero fitness values to strictly positive weights, where the
        # lowest original fitness gets the smallest positive weight, conserving relative magnitude distance.
        min_fit = min(fitnesses)

        # We need all values to be > 0. If min_fit is <= 0, adjust. Otherwise, just use the values.
        # Add slight epsilon (1e-6) so even the lowest score gets a tiny non-zero probability chance.
        if min_fit <= 0:
            shift_amount = abs(min_fit) + 1e-6
            adjusted_fitnesses = [f + shift_amount for f in fitnesses]
        else:
            adjusted_fitnesses = list(fitnesses)

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


class NonagaTournamentFitness(FitnessFunction):
    """
    Evaluates an entire generation with a balanced K-opponent schedule.
    Each scheduled pair plays two games (color swap), and fitness is wins/matches.
    """

    def __init__(self, k_opponents: int, max_moves: int, depth: int, schedule_seed: int = None):
        self.k_opponents = k_opponents
        self.max_moves = max_moves
        self.population = []  # Will be dynamically injected by ModularGA
        self.depth = depth
        self.schedule_seed = schedule_seed
        self.generation_index = 0

    def set_generation_index(self, generation_index: int) -> None:
        self.generation_index = generation_index

    def _build_balanced_pairs(self, population_size: int) -> List[Tuple[int, int]]:
        if population_size < 2:
            return []

        if self.k_opponents < 1 or self.k_opponents > population_size - 1:
            raise ValueError(
                f"k_opponents must be in [1, {population_size - 1}] for population size {population_size}, got {self.k_opponents}."
            )

        # A k-regular simple graph on n nodes exists iff 0 <= k < n and n*k is even.
        if (population_size * self.k_opponents) % 2 != 0:
            raise ValueError(
                "Balanced schedule is impossible for this (population_size, k_opponents) because n*k must be even. "
                f"Got n={population_size}, k={self.k_opponents}."
            )

        if self.schedule_seed is not None:
            generation_seed = self.schedule_seed + self.generation_index
            rng = random.Random(generation_seed)
        else:
            rng = random

        permuted = list(range(population_size))
        rng.shuffle(permuted)

        pairs_set = set()

        # Circulant construction for even component of k.
        for step in range(1, (self.k_opponents // 2) + 1):
            for i in range(population_size):
                j = (i + step) % population_size
                a = permuted[i]
                b = permuted[j]
                edge = (a, b) if a < b else (b, a)
                pairs_set.add(edge)

        # If k is odd, add one perfect matching (only possible when n is even).
        if self.k_opponents % 2 == 1:
            half = population_size // 2
            for i in range(half):
                a = permuted[i]
                b = permuted[(i + half) % population_size]
                edge = (a, b) if a < b else (b, a)
                pairs_set.add(edge)

        pairs = sorted(pairs_set)

        expected_pairs = (population_size * self.k_opponents) // 2
        if len(pairs) != expected_pairs:
            raise RuntimeError(
                f"Schedule construction failed: expected {expected_pairs} pairs, got {len(pairs)}."
            )

        return pairs

    def evaluate_population(self, population: List[List[int]], backend) -> List[float]:
        n = len(population)
        if n == 0:
            return []

        pairs = self._build_balanced_pairs(n)

        fixtures: List[Dict[str, Any]] = []
        for i, j in pairs:
            fixtures.append({
                "idx_red": i,
                "idx_black": j,
                "params_red": population[i],
                "params_black": population[j],
                "depth": self.depth,
                "max_moves": self.max_moves,
            })
            fixtures.append({
                "idx_red": j,
                "idx_black": i,
                "params_red": population[j],
                "params_black": population[i],
                "depth": self.depth,
                "max_moves": self.max_moves,
            })

        results = backend.map_tasks(_simulate_nonaga_fixture, fixtures)

        wins = [0 for _ in range(n)]
        matches = [0 for _ in range(n)]

        for result in results:
            idx_red = result["idx_red"]
            idx_black = result["idx_black"]
            winner = result["winner"]

            matches[idx_red] += 1
            matches[idx_black] += 1
            # Win
            if winner >= 0:
                wins[winner] += 1
            # Draw
            else:
                wins[idx_red] += 0.5
                wins[idx_black] += 0.5

        return [wins[i] / matches[i] if matches[i] > 0 else 0.0 for i in range(n)]

    def evaluate(self, individual: List[int]) -> float:
        # Tournament fitness is generation-level and should use evaluate_population.
        return 0.0
