if __name__ == '__main__':
    import os
    import sys
    
    # Add NonagaGame to path and compile Cython files before importing GA logic
    my_nonaga_path = os.path.abspath("NonagaGame")
    if my_nonaga_path not in sys.path:
        sys.path.append(my_nonaga_path)
    
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
    fitness = strategies.NonagaTournamentFitness(k_opponents=10, max_moves=30)

    # 2. Initialize parallel backend
    # Note: On Windows multiprocessing, testing within __main__ is required
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
    final_population = ga.run(generations=20, pop_size=20, genome_length=8)

    print("\nOptimization Complete. View ga_metrics.csv for generation logs.")
