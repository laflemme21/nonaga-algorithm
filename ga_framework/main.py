if __name__ == '__main__':
    import strategies
    from backends import MasterSlaveBackend
    from core import ModularGA

    print("Initializing Modular GA...")

    # 1. Initialize concrete strategies
    selection = strategies.RouletteWheelSelection()
    crossover = strategies.ArithmeticCrossover()
    mutation = strategies.RandomIntMutation(mutation_rate=0.5, min_val=0, max_val=10)
    fitness = strategies.DummyFitness()

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

    # 4. Run the GA for 10 generations as MVP
    print("Running GA optimization...")
    final_population = ga.run(generations=30, pop_size=20, genome_length=8)

    print("\nOptimization Complete. View ga_metrics.csv for generation logs.")
