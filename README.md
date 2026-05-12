# Nonaga Algorithm

Nonaga Algorithm is a Python implementation of the Nonaga board game with a Cython-accelerated rules bitboard engine and AI opponent. This repository also includes a genetic algorithm (GA) workflow for tuning AI parameters, plus benchmarking utilities and experiment outputs.

## Quick start

- Python 3
- Install dependencies: `pip install -r requirements.txt`

## Run the game

From the repo root:

`python NonagaGame/main.py`

This launches the menu where you can start a two-player game or play against the AI.

## Run the GA

From the repo root:

`python ga_framework/main.py --run-name my_run`

Outputs are written to `GA results/my_run.csv`. Run `python ga_framework/main.py --help` for tuning options.

## Profiling

Game:

`python -m cProfile -o program.prof NonagaGame/main.py`

GA:

`python -m cProfile -o program.prof ga_framework/main.py --run-name prof_run`

View the report:

`snakeviz program.prof`

Note: Profiling the underlying C functions might require using pyspy, running it in a seperate terminal to track the process of the python process running the algorithm.

## Repository structure

- NonagaGame/ - game entry point, UI windows, and Cython-accelerated core logic.
- ga_framework/ - modular GA framework, strategies, backends, and the staged GA launcher.
- benchmark_feature/ - feature-level benchmark runner and results.
- benchmark_version/ - version-to-version benchmark runner and results.
- GA results/ - generated GA run logs (CSV).
- Aire/ - Slurm/HPC batch scripts for automated runs.
- build/ - Cython build artifacts.
- legacy files/ - archived code and older experiments.