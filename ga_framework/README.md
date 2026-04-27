# Modular Genetic Algorithm Framework

This is a highly modular, dependency-injected Genetic Algorithm (GA) framework designed for High-Performance Computing (HPC) workflows. It utilizes standard Python lists for genome representation and adheres to the Strategy Design Pattern, allowing you to easily swap out genetic operators and parallel execution backends.

## Core Components

The framework is driven by `ModularGA`, which requires concrete implementations of the following Abstract Base Classes (ABCs) defined in `interfaces.py`:

- **`SelectionStrategy`**: Defines how parents are selected from the population.
- **`CrossoverStrategy`**: Defines how genes are combined from two parents to produce offspring.
- **`MutationStrategy`**: Defines how an individual's genes are randomly altered.
- **`FitnessFunction`**: Evaluates an individual and returns a fitness score.
- **`ParallelBackend`**: Manages the distribution of fitness evaluations across multiple processes/nodes.

## Basic Usage

Here is how to initialize and run the standard Master-Slave parallelized GA:

```python
from ga_framework.strategies import RandomSelection, SinglePointCrossover, RandomIntMutation, DummyFitness
from ga_framework.backends import MasterSlaveBackend
from ga_framework.core import ModularGA

if __name__ == '__main__':
    # 1. Initialize concrete strategies
    selection = RandomSelection()
    crossover = SinglePointCrossover()
    mutation = RandomIntMutation(mutation_rate=0.1, min_val=0, max_val=10)

    # Replace with your actual objective function
    fitness = DummyFitness()

    # 2. Initialize parallel backend (e.g., 4 processes)
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

    # 4. Run the optimization
    # pop_size: Number of individuals per generation
    # genome_length: Number of integer genes per individual
    final_population = ga.run(generations=10, pop_size=20, genome_length=8)
```

## Staged Search Launcher

The repository's `ga_framework/main.py` entrypoint now runs the GA in stages by default. It evaluates several search-space slices separately, keeps the resulting survivors, and then performs one final combined GA round over the merged population.

The default partitioning matches the existing launcher behavior:

```text
0:13,13:25,25:37,37:50
```

You can change the staged search slices and the final search range from the command line:

```bash
python ga_framework/main.py --run-name experiment_01 --partition-ranges 0:10,10:20,20:35,35:50 --final-range 0:50
```

Useful knobs include:

- `--stage-generations` and `--stage-pop-size` for the partitioned rounds.
- `--final-generations` for the final merged round.
- `--stage-k-opponents` / `--final-k-opponents` to tune the tournament evaluation for each phase.
- `--run-name` to choose the output filename for this run.

## Creating Custom Strategies

To implement your own logic for the game or evaluation workflow, simply subclass the relevant interface from `interfaces.py`.

For example, to attach your specific game simulation as the fitness function:

```python
from ga_framework.interfaces import FitnessFunction
from typing import List

class GameFitness(FitnessFunction):
    def evaluate(self, individual: List[int]) -> float:
        # 1. Parse the genome (individual) into game parameters
        # 2. Run the game simulation
        # 3. Return the performance score
        score = sum(individual) # Example logic
        return float(score)
```

Then, inject `GameFitness()` into the `ModularGA` at instantiation.

## Logging

The staged launcher writes one file per top-level run into `GA results/<run-name>.csv`.

Each run file contains:

1. A top preamble with all run parameters provided on the command line.
2. Human-readable sections for each stage and the final combined round.
3. A CSV metrics header and generation rows for each section.

This keeps parallel fitness evaluation safe while preserving a single segmented log file for each run.
