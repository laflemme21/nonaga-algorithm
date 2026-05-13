from evaluate_parameters import load_parameters
import argparse
import csv
import itertools
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))


def main() -> int:
    p = argparse.ArgumentParser(description="Generate round-robin schedule.")
    p.add_argument("--parameters", default="parameters.json")
    p.add_argument("--output", default="match_schedule.csv")
    p.add_argument("--max-moves", type=int, default=50)
    a = p.parse_args()

    genomes = load_parameters(a.parameters)[0]
    n = len(genomes)

    total = n * (n - 1)
    with open(a.output, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["task_id", "idx1", "idx2", "max_moves"])
        for t, (i, j) in enumerate(itertools.permutations(range(n), 2), 1):
            w.writerow([t, i, j, a.max_moves])
    print(f"Wrote {total} matches to {a.output}.")
    print(f"Set your Slurm array range to 1-{total}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
