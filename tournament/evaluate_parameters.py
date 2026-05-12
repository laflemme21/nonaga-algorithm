
import json
import csv
import sys
import os
import itertools
import concurrent.futures
from typing import List

# Ensure NonagaGame is in the path context so models import cleanly
my_nonaga_path = os.path.abspath("NonagaGame")
if my_nonaga_path not in sys.path:
    sys.path.append(my_nonaga_path)

from nonaga_constants import RED, BLACK
from nonaga_logic import NonagaLogic
from AI import AI
from compiler import compile_cython_files

def _has_any_destinations(move_map: object) -> bool:
    """Return True when a move map contains at least one legal destination."""
    if not move_map:
        return False
    if not isinstance(move_map, dict):
        return False
    for destinations in move_map.values():
        if destinations:
            return True
    return False


def load_parameters(filepath: str) -> List[List[int]]:
    with open(filepath, "r") as f:
        return json.load(f)


def run_match(ai_1_params: List[int], ai_2_params: List[int], max_moves: int = 150) -> tuple[float, float]:
    """
    Simulates a match between two AI parameter sets.
    Returns a tuple of points (score1, score2) where:
    Win = 1, Draw/Timeout = 0, Loss = 0
    """
    ai_red = AI(parameter=ai_1_params, depth=3, color=RED)
    ai_black = AI(parameter=ai_2_params, depth=3, color=BLACK)

    game = NonagaLogic(player_red=ai_red, player_black=ai_black, new_game=True)

    moves = 0
    while moves < max_moves:
        piece_moves = game.get_all_valid_piece_moves()
        tile_moves = game.get_all_valid_tile_moves()
        if not _has_any_destinations(piece_moves) or not _has_any_destinations(tile_moves):
            return 0.5, 0.5  # Draw
        current_color = game.get_current_player()
        active_ai = ai_red if current_color == RED else ai_black

        try:
            best_piece_move, best_tile_move = active_ai.get_best_move(game)
            game.move_piece_py(best_piece_move[0], best_piece_move[1])
            game.move_tile_py(best_tile_move[0], best_tile_move[1])
        except Exception as e:
            # If an AI crashes or makes an invalid move, print it so we know!
            print(f"Match error: {e}")
            break

        if game.check_win_condition_py(RED):
            return 1, 0  # AI 1 wins
        elif game.check_win_condition_py(BLACK):
            return 0, 1  # AI 2 wins

        moves += 1

    # Draw limits reached
    return 0.5, 0.5


def evaluate_matchup(task: tuple[int, int, List[int], List[int], int]) -> tuple[int, int, float, float]:
    idx1, idx2, ai_1_params, ai_2_params, max_moves = task
    score1, score2 = run_match(ai_1_params, ai_2_params, max_moves=max_moves)
    return idx1, idx2, score1, score2


def tournament():
    print("Starting tournament setup...")

    param_file = os.path.abspath("parameters.json")
    if not os.path.exists(param_file):
        print(f"Error: {param_file} does not exist.")
        return

    genomes = load_parameters(param_file)[0]
    num_genomes = len(genomes)
    print(f"Loaded {num_genomes} AI parameters from {param_file}.")

    if num_genomes < 2:
        print("Need at least 2 AIs in parameters.json to run a tournament!")
        return

    # Keep track of points arrays
    scores = {i: 0 for i in range(num_genomes)}
    match_results = []
    max_moves = 50

    # Generate round-robin matchups (everyone plays everyone exactly once)
    matchups = list(itertools.permutations(range(num_genomes), 2))
    print(f"Running {len(matchups)} total matches...\n")

    max_workers = int(os.environ.get(
        "SLURM_CPUS_PER_TASK", os.cpu_count() or 1))
    tasks = [
        (idx1, idx2, genomes[idx1], genomes[idx2], max_moves)
        for idx1, idx2 in matchups
    ]

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        for idx1, idx2, score1, score2 in executor.map(evaluate_matchup, tasks):
            print(f"Match: AI {idx1} vs AI {idx2} ...")

            if score1 > 0:
                print(f" -> AI {idx1} Wins!")
                scores[idx1] += 1
                match_results.append((idx1, idx2, idx1))
            elif score2 > 0:
                print(f" -> AI {idx2} Wins!")
                scores[idx2] += 1
                match_results.append((idx1, idx2, idx2))
            else:
                print(" -> Draw / Timeout")
                match_results.append((idx1, idx2, "Draw"))

    # Log results to CSV
    log_file = "tournament_results.csv"
    with open(log_file, "w", newline="") as f:
        writer = csv.writer(f)

        # Write scoreboard header
        writer.writerow(["AI_ID", "Genome", "Total_Wins"])
        for i in range(num_genomes):
            writer.writerow([i, str(genomes[i]), scores[i]])

        writer.writerow([])
        writer.writerow([])

    print(f"\nTournament complete! Results successfully logged to {log_file}.")


if __name__ == "__main__":
    tournament()
