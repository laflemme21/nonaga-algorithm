#!/bin/bash
#SBATCH --job-name=run_5_python_scripts     # A name for your job
#SBATCH --output=output_%j.out              # Standard output log (%j will be replaced by the Job ID)
#SBATCH --error=error_%j.err                # Standard error log
#SBATCH --time=05:00:00                     # Requested runtime (HH:MM:SS) - Adjust to your needs
#SBATCH --nodes=1                           # Number of nodes
#SBATCH --ntasks=1                          # Number of tasks
#SBATCH --cpus-per-task=1                   # CPU cores requested per task (adjust if scripts use multiprocessing)
#SBATCH --mem=4G                            # Total memory requested (adjust depending on your scripts' needs)

# 1. Load the Miniforge module to access Python
module load miniforge/24.7.1

# 2. (Optional) Activate your custom Conda environment if you have created one. 
# Remove the '#' from the line below and replace 'myenv' with your environment name.
# conda activate myenv

# 3. Run the 5 Python scripts consecutively
echo "Starting GA run with 20 generations..."
python ga_framework/main.py --mode slurm --run-name "ga_gen_20" --final-generations 20 --stage-generations 0

echo "Starting GA run with 100 generations..."
python ga_framework/main.py --mode slurm --run-name "ga_gen_100" --final-generations 100 --stage-generations 0

echo "Starting GA run with 200 generations..."
python ga_framework/main.py --mode slurm --run-name "ga_gen_200" --final-generations 200 --stage-generations 0

echo "Starting GA run with 500 generations..."
python ga_framework/main.py --mode slurm --run-name "ga_gen_500" --final-generations 500 --stage-generations 0

echo "Starting GA run with 1000 generations..."
python ga_framework/main.py --mode slurm --run-name "ga_gen_1000" --final-generations 1000 --stage-generations 0

echo "All scripts have completed."