from evaluate_parameters import run_match
import argparse
import csv
import itertools
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))


def _read_rows(path):
    with open(path, newline="") as f:
        lines = f.readlines()
    start = None
    for i, line in enumerate(lines):
        if line.lstrip().startswith("Generation,"):
            start = i
            break
    return None if start is None else csv.DictReader(lines[start:])


def main():
    parser = argparse.ArgumentParser(
        description="RR Top_1_Genome from GA CSVs")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--out", default="tournament_results.csv")
    parser.add_argument("--max-moves", type=int, default=50)
    parser.add_argument("--dedupe", action="store_true")
    parser.add_argument("--every", type=int, default=1)
    parser.add_argument("--emit", action="store_true")
    parser.add_argument("--parameters-out", default="rr_parameters.json")
    parser.add_argument("--sources-out", default="rr_sources.csv")
    args = parser.parse_args()

    genes, sources = [], []
    seen = {} if args.dedupe else None
    for path in args.files:
        if not os.path.exists(path):
            print(f"Missing file: {path}")
            return 1
        reader = _read_rows(path)
        if not reader or "Top_1_Genome" not in (reader.fieldnames or []):
            print(f"No Top_1_Genome column in {path}")
            return 1
        rows = list(reader)
        last_idx = len(rows) - 1
        for i, row in enumerate(rows):
            take = True
            if args.every > 1:
                try:
                    gen = int(row.get("Generation", ""))
                    take = (gen % args.every == 0)
                except ValueError:
                    take = True
                if i == last_idx:
                    take = True
            if not take:
                continue
            gene_str = row.get("Top_1_Genome")
            if not gene_str:
                continue
            try:
                gene = json.loads(gene_str)
            except json.JSONDecodeError:
                continue
            key = tuple(gene)
            src = f"{os.path.basename(path)}:gen{row.get('Generation', '')}"
            if seen is None:
                genes.append(gene)
                sources.append([src])
            else:
                if key not in seen:
                    seen[key] = len(genes)
                    genes.append(gene)
                    sources.append([src])
                else:
                    sources[seen[key]].append(src)

    if len(genes) < 2:
        print("Need at least 2 unique genes.")
        return 1

    if args.emit:
        with open(args.parameters_out, "w") as f:
            json.dump([genes], f)
        with open(args.sources_out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["AI_ID", "Genome", "Sources"])
            for i, gene in enumerate(genes):
                w.writerow([i, json.dumps(gene), ";".join(sources[i])])
        print(f"Wrote {len(genes)} unique genes to {args.parameters_out}.")
        print(f"Wrote sources to {args.sources_out}.")
        return 0

    n = len(genes)
    wins, losses, draws = [0] * n, [0] * n, [0] * n
    for i, j in itertools.permutations(range(n), 2):
        s1, s2 = run_match(genes[i], genes[j], max_moves=args.max_moves)
        if s1 > s2:
            wins[i] += 1
            losses[j] += 1
        elif s2 > s1:
            wins[j] += 1
            losses[i] += 1
        else:
            draws[i] += 1
            draws[j] += 1

    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["AI_ID", "Genome", "Sources",
                   "Wins", "Losses", "Draws", "Points"])
        for i, gene in enumerate(genes):
            points = wins[i] + 0.5 * draws[i]
            w.writerow([i, json.dumps(gene), ";".join(sources[i]),
                       wins[i], losses[i], draws[i], points])

    print(f"Wrote {len(genes)} unique genes to {args.out}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
