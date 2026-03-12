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
        mutation_rate=0.5, min_val=-100, max_val=100)
    fitness = strategies.NonagaTournamentFitness(k_opponents=50, max_moves=30)

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
        print(f"[{args.mode.upper()}] Running parallel backend with fixed 4 workers.")
        backend = MasterSlaveBackend(max_workers=4)

    # 3. Inject dependencies into GA orchestrator
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
    final_population = ga.run(generations=300, pop_size=100, genome_length=8)

    print("\nOptimization Complete. View ga_metrics.csv for generation logs.")
