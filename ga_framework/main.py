import argparse
import csv
import os
import sys
from datetime import datetime

from typing import Any, List, Tuple


# Move this OUTSIDE __main__ so child worker processes also get the correct path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)
if current_dir not in sys.path:
    sys.path.append(current_dir)
my_nonaga_path = os.path.join(project_root, "NonagaGame")
if my_nonaga_path not in sys.path:
    sys.path.append(my_nonaga_path)


DEFAULT_STAGE_RANGES: List[Tuple[int, int]] = [(0, 13), (13, 25), (25, 37), (37, 50)]
DEFAULT_FINAL_RANGE: Tuple[int, int] = (0, 50)
GA_RESULTS_DIR_NAME = "GA results"
METRIC_HEADERS = ["Generation", "Best_Fitness", "Average_Fitness",
                  "Worst_Fitness"] + [f"Top_{i}_Genome" for i in range(1, 6)]


def _parse_run_name(raw_name: str) -> str:
    cleaned = raw_name.strip()
    if not cleaned:
        raise argparse.ArgumentTypeError("--run-name cannot be empty.")

    invalid_chars = '<>:"/\\|?*'
    if any(char in cleaned for char in invalid_chars):
        raise argparse.ArgumentTypeError(
            "--run-name contains invalid filename characters.")

    return cleaned


def _parse_range_spec(range_spec: str) -> Tuple[int, int]:
    parts = [part.strip() for part in range_spec.split(":")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise argparse.ArgumentTypeError(
            f"Invalid range '{range_spec}'. Expected the form LOW:HIGH.")

    lower = int(parts[0])
    upper = int(parts[1])
    if lower > upper:
        raise argparse.ArgumentTypeError(
            f"Invalid range '{range_spec}'. LOW must be <= HIGH.")

    return lower, upper


def _parse_range_list(raw_ranges: str) -> List[Tuple[int, int]]:
    ranges: List[Tuple[int, int]] = []
    for raw_range in raw_ranges.split(","):
        cleaned = raw_range.strip()
        if not cleaned:
            continue
        ranges.append(_parse_range_spec(cleaned))

    if not ranges:
        raise argparse.ArgumentTypeError(
            "At least one partition range is required.")

    return ranges


def _resolve_run_log_file(run_name: str) -> str:
    results_dir = os.path.join(project_root, GA_RESULTS_DIR_NAME)
    os.makedirs(results_dir, exist_ok=True)
    return os.path.join(results_dir, f"{run_name}.csv")


def _initialize_run_log_file(log_file: str, args, raw_cli_args: List[str]) -> None:
    with open(log_file, "w", newline="", encoding="utf-8") as f:
        f.write("# Nonaga GA Run\n")
        f.write(f"# run_name: {args.run_name}\n")
        f.write(f"# timestamp: {datetime.now().isoformat(timespec='seconds')}\n")
        f.write(f"# raw_cli_args: {' '.join(raw_cli_args)}\n")
        f.write("# full_run_parameters:\n")
        for key in sorted(vars(args).keys()):
            f.write(f"#   {key}: {getattr(args, key)}\n")
        f.write("\n")


def _append_section_header(log_file: str, section_title: str, section_params: List[Tuple[str, Any]]) -> None:
    with open(log_file, "a", newline="", encoding="utf-8") as f:
        f.write(f"=== {section_title} ===\n")
        for key, value in section_params:
            f.write(f"{key}: {value}\n")
        writer = csv.writer(f)
        writer.writerow(METRIC_HEADERS)


def _build_backend(args):
    from ga_framework.backends import MasterSlaveBackend

    if args.mode == "slurm":
        slurm_cpus = os.environ.get("SLURM_CPUS_PER_TASK")
        if slurm_cpus:
            num_cores = int(slurm_cpus)
        elif hasattr(os, "sched_getaffinity"):
            num_cores = len(os.sched_getaffinity(0))
        else:
            raise EnvironmentError(
                "Unable to determine number of CPU cores for Slurm mode. Please set SLURM_CPUS_PER_TASK or ensure os.sched_getaffinity is available.")

        print(f"[{args.mode.upper()}] Running parallel backend with {num_cores} workers.")
        return MasterSlaveBackend(max_workers=num_cores)

    print(f"[{args.mode.upper()}] Running parallel backend with fixed 6 workers.")
    return MasterSlaveBackend(max_workers=6)


def _run_ga_round(
    ga,
    *,
    generations: int,
    pop_size: int,
    genome_length: int,
    min_gene_val: int,
    max_gene_val: int,
    mutation_prob: float,
    population=None,
):
    return ga.run(
        generations=generations,
        pop_size=pop_size,
        genome_length=genome_length,
        min_gene_val=min_gene_val,
        max_gene_val=max_gene_val,
        mutation_prob=mutation_prob,
        population=population,
    )


def _run_staged_search(
    *,
    args,
    selection,
    crossover,
    mutation,
    backend,
    stage_ranges: List[Tuple[int, int]],
    final_range: Tuple[int, int],
):
    from ga_framework import strategies
    from ga_framework.core import ModularGA

    stage_populations: List[List[int]] = []

    for stage_index, (min_gene_val, max_gene_val) in enumerate(stage_ranges, start=1):
        print(
            f"Running stage {stage_index}/{len(stage_ranges)} over search range [{min_gene_val}, {max_gene_val}]...")
        _append_section_header(
            args.log_file,
            section_title=f"Stage {stage_index}/{len(stage_ranges)}",
            section_params=[
                ("range", f"{min_gene_val}:{max_gene_val}"),
                ("generations", args.stage_generations),
                ("pop_size", args.stage_pop_size),
                ("mutation_prob", args.stage_mutation_prob),
                ("k_opponents", args.stage_k_opponents),
                ("depth", args.stage_depth),
                ("max_moves", args.stage_max_moves),
                ("genome_length", args.genome_length),
                ("mutation_rate", args.mutation_rate),
            ],
        )
        stage_fitness = strategies.NonagaTournamentFitness(
            k_opponents=args.stage_k_opponents,
            max_moves=args.stage_max_moves,
            depth=args.stage_depth,
            schedule_seed=args.schedule_seed,
        )
        stage_ga = ModularGA(
            selection=selection,
            crossover=crossover,
            mutation=mutation,
            fitness=stage_fitness,
            backend=backend,
            log_file=args.log_file,
            initialize_log=False,
        )
        stage_population = _run_ga_round(
            stage_ga,
            generations=args.stage_generations,
            pop_size=args.stage_pop_size,
            genome_length=args.genome_length,
            min_gene_val=min_gene_val,
            max_gene_val=max_gene_val,
            mutation_prob=args.stage_mutation_prob,
        )
        stage_populations.extend(stage_population)
        print(
            f"Stage {stage_index} complete. Collected {len(stage_population)} survivors.")

    final_fitness = strategies.NonagaTournamentFitness(
        k_opponents=args.final_k_opponents,
        max_moves=args.final_max_moves,
        depth=args.final_depth,
        schedule_seed=args.schedule_seed,
    )
    final_ga = ModularGA(
        selection=selection,
        crossover=crossover,
        mutation=mutation,
        fitness=final_fitness,
        backend=backend,
        log_file=args.log_file,
        initialize_log=False,
    )
    _append_section_header(
        args.log_file,
        section_title="Final Combined Round",
        section_params=[
            ("range", f"{final_range[0]}:{final_range[1]}"),
            ("generations", args.final_generations),
            ("pop_size", len(stage_populations)),
            ("mutation_prob", args.final_mutation_prob),
            ("k_opponents", args.final_k_opponents),
            ("depth", args.final_depth),
            ("max_moves", args.final_max_moves),
            ("genome_length", args.genome_length),
            ("mutation_rate", args.mutation_rate),
        ],
    )
    print(
        f"Running final combined GA round over search range [{final_range[0]}, {final_range[1]}] with {len(stage_populations)} merged survivors...")
    return _run_ga_round(
        final_ga,
        generations=args.final_generations,
        pop_size=len(stage_populations),
        genome_length=args.genome_length,
        min_gene_val=final_range[0],
        max_gene_val=final_range[1],
        mutation_prob=args.final_mutation_prob,
        population=stage_populations,
    )


if __name__ == '__main__':
    from ga_framework import strategies

    parser = argparse.ArgumentParser(
        description="Run Nonaga Genetic Algorithm")
    parser.add_argument("--mode", type=str, choices=["local", "slurm"], default="local",
                        help="Execution mode: 'local' (fixed cores) or 'slurm' (dynamic cores)")
    parser.add_argument("--run-name", type=_parse_run_name, required=True,
                        help="Unique run label used as the output filename inside GA results.")
    parser.add_argument("--partition-ranges", type=str, default=",".join(
        f"{lower}:{upper}" for lower, upper in DEFAULT_STAGE_RANGES),
        help="Comma-separated search-space slices to evaluate before the final combined round. Use LOW:HIGH pairs.")
    parser.add_argument("--final-range", type=str, default=f"{DEFAULT_FINAL_RANGE[0]}:{DEFAULT_FINAL_RANGE[1]}",
                        help="Search-space range for the final combined GA round. Use LOW:HIGH.")
    parser.add_argument("--stage-generations", type=int, default=10,
                        help="Number of generations per partitioned stage.")
    parser.add_argument("--stage-pop-size", type=int, default=5,
                        help="Population size per partitioned stage.")
    parser.add_argument("--stage-mutation-prob", type=float, default=0.4,
                        help="Mutation probability applied during partitioned stages.")
    parser.add_argument("--stage-k-opponents", type=int, default=4,
                        help="Number of opponents used for partitioned-stage fitness evaluation.")
    parser.add_argument("--stage-depth", type=int, default=2,
                        help="Search depth used for partitioned-stage fitness evaluation.")
    parser.add_argument("--stage-max-moves", type=int, default=30,
                        help="Max moves allowed during partitioned-stage fitness evaluation.")
    parser.add_argument("--final-generations", type=int, default=15,
                        help="Number of generations in the final combined GA round.")
    parser.add_argument("--final-mutation-prob", type=float, default=0.4,
                        help="Mutation probability applied during the final combined round.")
    parser.add_argument("--final-k-opponents", type=int, default=6,
                        help="Number of opponents used for final-round fitness evaluation.")
    parser.add_argument("--final-depth", type=int, default=3,
                        help="Search depth used for final-round fitness evaluation.")
    parser.add_argument("--final-max-moves", type=int, default=30,
                        help="Max moves allowed during final-round fitness evaluation.")
    parser.add_argument("--genome-length", type=int, default=8,
                        help="Genome length used for every GA run in the staged workflow.")
    parser.add_argument("--mutation-rate", type=float, default=0.5,
                        help="Mutation rate used by the integer mutation strategy.")
    parser.add_argument("--schedule-seed", type=int, default=7777777,
                        help="Optional seed for deterministic tournament scheduling")
    args = parser.parse_args()

    stage_ranges = _parse_range_list(args.partition_ranges)
    final_range = _parse_range_spec(args.final_range)
    args.log_file = _resolve_run_log_file(args.run_name)
    _initialize_run_log_file(args.log_file, args, sys.argv[1:])
    print(f"Logging this run to: {args.log_file}")

    # Compile Cython files before importing GA logic
    from NonagaGame.compiler import compile_cython_files
    print("Ensuring Cython core components are compiled...")
    compile_cython_files()

    print("Initializing Modular GA...")

    # 1. Initialize concrete strategies
    selection = strategies.RouletteWheelSelection()
    crossover = strategies.ArithmeticCrossover()
    mutation = strategies.RandomIntMutation(
        mutation_rate=args.mutation_rate, min_val=0, max_val=final_range[1])

    backend = _build_backend(args)

    # 2. Run the staged search and combine the survivors in one final GA round
    final_population = _run_staged_search(
        args=args,
        selection=selection,
        crossover=crossover,
        mutation=mutation,
        backend=backend,
        stage_ranges=stage_ranges,
        final_range=final_range,
    )

    print(f"Final merged population size: {len(final_population)}")
    print(f"\nOptimization Complete. View {args.log_file} for generation logs.")
