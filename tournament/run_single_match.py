import argparse
import csv
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from tournament.evaluate_parameters import load_parameters, run_match


def load_task(schedule_path: str, task_id: int) -> tuple[int, int, int]:
    with open(schedule_path, "r", newline="") as f:
        for row in csv.DictReader(f):
            if int(row["task_id"]) == task_id:
                return int(row["idx1"]), int(row["idx2"]), int(row["max_moves"])
    raise ValueError(f"Task ID {task_id} not found in {schedule_path}.")


def write_result(result: dict, results_dir: str, task_id: int) -> str:
    os.makedirs(results_dir, exist_ok=True)
    path = os.path.join(results_dir, f"match_{task_id}_result.json")
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(result, f, indent=2)
    os.replace(tmp, path)
    return path


def main() -> int:
    p = argparse.ArgumentParser(description="Run a single Nonaga match.")
    p.add_argument("--task_id", type=int, required=True)
    p.add_argument("--schedule", default="match_schedule.csv")
    p.add_argument("--parameters", default="parameters.json")
    p.add_argument("--results-dir", default="results")
    a = p.parse_args()

    idx1, idx2, max_moves = load_task(a.schedule, a.task_id)
    genomes = load_parameters(a.parameters)[0]

    score1, score2 = run_match(
        genomes[idx1], genomes[idx2], max_moves=max_moves)
    winner = idx1 if score1 > score2 else idx2 if score2 > score1 else "Draw"
    result = {
        "task_id": a.task_id,
        "idx1": idx1,
        "idx2": idx2,
        "score1": score1,
        "score2": score2,
        "max_moves": max_moves,
        "winner": winner,
    }
    path = write_result(result, a.results_dir, a.task_id)
    print(f"Wrote result to {path}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
