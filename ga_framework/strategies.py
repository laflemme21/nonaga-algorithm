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
    Evaluates an individual by making it play K games against randomly selected 
    opponents from the current generation. Points are awarded based on wins.
    """

    def __init__(self, k_opponents: int, max_moves: int):
        self.k_opponents = k_opponents
        self.max_moves = max_moves
        self.population = []  # Will be dynamically injected by ModularGA

    def evaluate(self, individual: List[int]) -> float:
        import sys
        import os

        # Ensure NonagaGame is in the path for evaluating AI logic
        my_nonaga_path = os.path.abspath("NonagaGame")
        if my_nonaga_path not in sys.path:
            sys.path.append(my_nonaga_path)

        try:
            from AI import AI
            from nonaga_logic import NonagaLogic
            from nonaga_constants import RED, BLACK
        except ImportError as e:
            print(f"Error importing Nonaga modules: {e}")
            return 0.0

        if not self.population:
            return 0.0

        # Select K random opponents from the current generation
        opponents = random.choices(self.population, k=self.k_opponents)

        score = 0.0

        for opponent in opponents:
            # We fix the individual to RED and opponent to BLACK for each match to simplify,
            # or could randomly flip the colors to be fair. Let's stick to RED (starts first)
            # but ideally it should alternate.
            color_ind, color_opp = RED, BLACK

            # Using depth=1 to keep GA evaluations reasonably fast
            ai_ind = AI(parameter=individual, depth=1, color=color_ind)
            ai_opp = AI(parameter=opponent, depth=1, color=color_opp)

            game = NonagaLogic(player_red=ai_ind,
                               player_black=ai_opp, new_game=True)

            moves = 0
            while moves < self.max_moves:
                current_color = game.get_current_player()
                active_ai = ai_ind if current_color == color_ind else ai_opp

                try:
                    # get_best_move determines what the AI does without executing it directly
                    best_piece_move, best_tile_move = active_ai.get_best_move(
                        game)
                    # Excute in the real logic board
                    game.move_piece(best_piece_move[0], best_piece_move[1])
                    game.move_tile(best_tile_move[0], best_tile_move[1])
                except Exception as e:
                    # Invalid move or AI crashed, break and count as a loss/draw
                    break

                if game.check_win_condition(color_ind):
                    score += 1.0
                    break
                elif game.check_win_condition(color_opp):
                    score -= 1.0  # Penalize for losing
                    break

                moves += 1

        return score
