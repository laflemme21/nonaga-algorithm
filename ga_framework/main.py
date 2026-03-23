import os
import sys

# Move this OUTSIDE __main__ so child worker processes also get the correct path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
my_nonaga_path = os.path.join(project_root, "NonagaGame")
if my_nonaga_path not in sys.path:
    sys.path.append(my_nonaga_path)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description="Run Nonaga Genetic Algorithm")
    parser.add_argument("--mode", type=str, choices=["local", "slurm"], default="local",
                        help="Execution mode: 'local' (fixed cores) or 'slurm' (dynamic cores)")
    parser.add_argument("--k-opponents", type=int, default=5,
                        help="Number of distinct opponents each individual faces per generation")
    
    parser.add_argument("--schedule-seed", type=int, default=7777777,
                        help="Optional seed for deterministic tournament scheduling")
    args = parser.parse_args()
        

    # Compile Cython files before importing GA logic
    from compiler import compile_cython_files
    print("Ensuring Cython core components are compiled...")
    compile_cython_files()

    import strategies
    from backends import MasterSlaveBackend
    from core import ModularGA

    print("Initializing Modular GA...")

    # 1. Initialize concrete strategies
    selection = strategies.RouletteWheelSelection()
    crossover = strategies.ArithmeticCrossover()
    mutation = strategies.RandomIntMutation(
        mutation_rate=0.5, min_val=0, max_val=50)
    fitness = strategies.NonagaTournamentFitness(
        k_opponents=args.k_opponents,
        max_moves=30,
        depth=2,
        schedule_seed=args.schedule_seed,
    )

    # 2. Initialize parallel backend
    if args.mode == "slurm":
        # Try to read from Slurm environment variable first
        slurm_cpus = os.environ.get('SLURM_CPUS_PER_TASK')
        if slurm_cpus:
            num_cores = int(slurm_cpus)
        elif hasattr(os, 'sched_getaffinity'):
            # Use sched_getaffinity if available (most reliable on Linux clusters)
            num_cores = len(os.sched_getaffinity(0))
        else:
            # raise error
            raise EnvironmentError(
                "Unable to determine number of CPU cores for Slurm mode. Please set SLURM_CPUS_PER_TASK or ensure os.sched_getaffinity is available.")

        print(
            f"[{args.mode.upper()}] Running parallel backend with {num_cores} workers.")
        backend = MasterSlaveBackend(max_workers=num_cores)
    else:
        # Default local mode with a fixed number of workers
        print(f"[{args.mode.upper()}] Running parallel backend with fixed 6 workers.")
        backend = MasterSlaveBackend(max_workers=6)

    # 3. Inject dependencies into GA orchestrator
    fitness = strategies.NonagaTournamentFitness(
        k_opponents=4,
        max_moves=30,
        depth=2,
        schedule_seed=args.schedule_seed,
    )
    ga = ModularGA(
        selection=selection,
        crossover=crossover,
        mutation=mutation,
        fitness=fitness,
        backend=backend,
        log_file="ga_metrics.csv"
    )

    # 4. Run the GA for n generations as MVP
    print("Running GA optimization...")
    population_1 = ga.run(generations=10, pop_size=5, genome_length=8,min_gene_val=0, max_gene_val=13, mutation_prob=0.4)
    population_2 = ga.run(generations=10, pop_size=5, genome_length=8,min_gene_val=13, max_gene_val=25, mutation_prob=0.4)
    population_3 = ga.run(generations=10, pop_size=5, genome_length=8,min_gene_val=25, max_gene_val=37, mutation_prob=0.4)
    population_4 = ga.run(generations=10, pop_size=5, genome_length=8,min_gene_val=37, max_gene_val=50, mutation_prob=0.4)
    all_pops = population_1+ population_2 + population_3 + population_4
    fitness = strategies.NonagaTournamentFitness(
        k_opponents=6,
        max_moves=30,
        depth=3,
        schedule_seed=args.schedule_seed,
    )
    ga = ModularGA(
        selection=selection,
        crossover=crossover,
        mutation=mutation,
        fitness=fitness,
        backend=backend,
        log_file="ga_metrics.csv"
    )
    final = ga.run(generations=15, pop_size=len(all_pops), genome_length=8,min_gene_val=0, max_gene_val=50, mutation_prob=0.4, population=all_pops)

    print("\nOptimization Complete. View ga_metrics.csv for generation logs.")
