#!/bin/bash
#SBATCH --job-name=nonaga_tournament
#SBATCH --output=slurm_tournament_%A_%a.out
#SBATCH --error=slurm_tournament_%A_%a.err
#SBATCH --time=02:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --mail-type=BEGIN,END
#SBATCH --mail-user=sc23ksk@leeds.ac.uk

set -euo pipefail

module load miniforge/24.7.1

cd "${SLURM_SUBMIT_DIR:-$PWD}"
cd ..




GA_FILES=("GA results/ga_gen_20.csv" "GA results/ga_gen_100.csv" "GA results/ga_gen_200.csv" "GA results/ga_gen_500.csv")
EVERY=${EVERY:-2}

# Anchor everything to home directory
PROJECT_ROOT="$HOME/nonaga-algorithm"
PARAMETERS="$PROJECT_ROOT/tournament/rr_parameters.json"
SOURCES="$PROJECT_ROOT/tournament/rr_sources.csv"
SCHEDULE="$PROJECT_ROOT/tournament/rr_match_schedule.csv"
RESULTS_DIR="$PROJECT_ROOT/tournament/results"

# Add the root to PYTHONPATH 
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

cd "$PROJECT_ROOT"
mkdir -p "$RESULTS_DIR"

# Define how many matches each core should process
CHUNK_SIZE=100

if [ -z "${SLURM_ARRAY_TASK_ID:-}" ]; then
        echo "Running pre-processing and generating match schedule..."
        python tournament/rr_from_ga_metrics.py "${GA_FILES[@]}" --every "$EVERY" --emit --parameters-out "$PARAMETERS" --sources-out "$SOURCES"
        python tournament/setup_tournament.py --parameters "$PARAMETERS" --output "$SCHEDULE"

        # Calculate total matches and the required number of array tasks
        NUM_MATCHES=$(( $(wc -l < "$SCHEDULE") - 1 ))
        NUM_TASKS=$(( (NUM_MATCHES + CHUNK_SIZE - 1) / CHUNK_SIZE ))
        
        echo "Schedule generated! Submitting $NUM_TASKS array tasks (each handling $CHUNK_SIZE matches) to the Aire queue..."
        sbatch --array=1-$NUM_TASKS "Aire/$(basename "$0")"
        exit 0
fi

# ==========================================
# WORKER BLOCK (Runs on compute nodes)
# ==========================================
NUM_MATCHES=$(( $(wc -l < "$SCHEDULE") - 1 ))
START_MATCH=$(( (SLURM_ARRAY_TASK_ID - 1) * CHUNK_SIZE + 1 ))
END_MATCH=$(( START_MATCH + CHUNK_SIZE - 1 ))

# Prevent the very last array task from trying to run matches that don't exist
if [ "$END_MATCH" -gt "$NUM_MATCHES" ]; then
    END_MATCH=$NUM_MATCHES
fi

echo "Array Task $SLURM_ARRAY_TASK_ID executing matches $START_MATCH through $END_MATCH..."

# Loop through this task's assigned chunk of the CSV schedule
for i in $(seq $START_MATCH $END_MATCH); do
    python tournament/run_single_match.py --task_id "$i" --schedule "$SCHEDULE" --parameters "$PARAMETERS" --results-dir "$RESULTS_DIR"
done
