#!/bin/bash
#SBATCH --job-name=nonaga-test
#SBATCH --time=00:20:00
#SBATCH --nodes=1
#SBATCH --ntasks=1          # Number of tasks for OpenMP
#SBATCH --cpus-per-task=16  # Number of CPU cores per task

# 1. Load Miniforge instead of the bare Python module
module purge
module load miniforge

# 2. Create the environment (only if it doesn't exist)
# We use --prefix to keep it in your project folder
if [ ! -d "./conda_env" ]; then
    conda create --prefix ./conda_env python=3.11 cython -y
fi

source activate ./conda_env
pip install -r requirements.txt

# Tell OpenMP how many resources it has been given
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

# Run the job
python -u evaluate_parameters.py --mode slurm
