#!/bin/bash
#SBATCH --job-name=nonaga-test
#SBATCH --time=00:20:00
#SBATCH --nodes=1
#SBATCH --ntasks=1          # Number of tasks for OpenMP
#SBATCH --cpus-per-task=16  # Number of CPU cores per task

# Load any necessary modules
module load miniforge       
conda activate .venv

# Tell OpenMP how many resources it has been given
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

# Run the job
python ga_framework/main.py --mode slurm
