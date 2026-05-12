#!/bin/bash
#SBATCH --job-name=run_5_python_scripts     # A name for your job
#SBATCH --output=output_GA_bench_%j.out              # Standard output log
#SBATCH --error=error_%j.err                # Standard error log
#SBATCH --time=14:00:00                     # Requested runtime (HH:MM:SS)

#SBATCH --ntasks=1                          # Number of tasks
#SBATCH --nodes=20                           # Number of nodes
#SBATCH --cpus-per-task=20               # CPU cores requested per task
#SBATCH --mem=16G                            # Total memory requested
#SBATCH --mail-type=BEGIN,END
#SBATCH --mail-user=sc23ksk@leeds.ac.uk

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


cd ..

# 3. Run the 5 Python scripts consecutively
# echo "Starting GA run with 20 generations..."
# python ga_framework/main.py --mode slurm --run-name "ga_gen_20" --final-generations 20 --stage-generations 0 --stage-pop-size 14

# echo "Starting GA run with 100 generations..."
# python ga_framework/main.py --mode slurm --run-name "ga_gen_100" --final-generations 100 --stage-generations 0 --stage-pop-size 14

echo "Starting GA run with 200 generations..."
python ga_framework/main.py --mode slurm --run-name "ga_gen_200" --final-generations 200 --stage-generations 0 --stage-pop-size 14

echo "Starting GA run with 500 generations..."
python ga_framework/main.py --mode slurm --run-name "ga_gen_500" --final-generations 500 --stage-generations 0 --stage-pop-size 14


echo "All scripts have completed."
