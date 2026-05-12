from tournament.evaluate_parameters import load_parameters
import argparse
import csv
import glob
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))


def main() -> int:
    p = argparse.ArgumentParser(description="Aggregate tournament results.")
    p.add_argument("--results-dir", default="results")
    p.add_argument("--parameters", default="parameters.json")
    p.add_argument("--sources")
    p.add_argument("--output", default="tournament_results.csv")
    a = p.parse_args()

    genomes = load_parameters(a.parameters)[0]
    n = len(genomes)

    stats = [[0, 0, 0] for _ in range(n)]
    sources = None
    if a.sources:
        with open(a.sources, newline="") as f:
            sources = {int(r["AI_ID"]): r.get("Sources", "")
                       for r in csv.DictReader(f)}
    files = glob.glob(os.path.join(a.results_dir, "match_*_result.json"))

    processed = 0
    for path in files:
        try:
            with open(path, "r") as f:
                result = json.load(f)
            idx1 = int(result["idx1"])
            idx2 = int(result["idx2"])
            s1 = float(result["score1"])
            s2 = float(result["score2"])
        except (OSError, KeyError, ValueError, TypeError):
            continue
        if idx1 >= n or idx2 >= n:
            continue
        if s1 > s2:
            stats[idx1][0] += 1
            stats[idx2][1] += 1
        elif s2 > s1:
            stats[idx2][0] += 1
            stats[idx1][1] += 1
        else:
            stats[idx1][2] += 1
            stats[idx2][2] += 1
        processed += 1

    with open(a.output, "w", newline="") as f:
        w = csv.writer(f)
        header = ["AI_ID", "Genome", "Total_Wins",
                  "Total_Losses", "Total_Draws", "Points"]
        if sources is not None:
            header = ["AI_ID", "Genome", "Sources", "Total_Wins",
                      "Total_Losses", "Total_Draws", "Points"]
        w.writerow(header)
        for i, gene in enumerate(genomes):
            row = [i, str(gene)]
            if sources is not None:
                row.append(sources.get(i, ""))
            points = stats[i][0] + 0.5 * stats[i][2]
            row.extend([stats[i][0], stats[i][1], stats[i][2], points])
            w.writerow(row)

    print(f"Aggregated {processed} match results into {a.output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
