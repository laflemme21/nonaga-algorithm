#!/bin/bash
#SBATCH --job-name=nonaga_tournament
#SBATCH --output=slurm_tournament_%A_%a.out
#SBATCH --error=slurm_tournament_%A_%a.err
#SBATCH --time=00:15:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G

set -euo pipefail

module load miniforge/24.7.1

cd "$SLURM_SUBMIT_DIR"

GA_FILES=("GA results/ga_gen_20.csv" "GA results/ga_gen_100.csv" "GA results/ga_gen_200.csv" "GA results/ga_gen_500.csv")
EVERY=${EVERY:-2}
PARAMETERS=${PARAMETERS:-tournament/rr_parameters.json}
SOURCES=${SOURCES:-tournament/rr_sources.csv}
SCHEDULE=${SCHEDULE:-tournament/rr_match_schedule.csv}
RESULTS_DIR=${RESULTS_DIR:-tournament/results}

mkdir -p "$RESULTS_DIR"

if [ -z "${SLURM_ARRAY_TASK_ID:-}" ]; then
	echo "Running pre-processing and generating match schedule..."
	python tournament/rr_from_ga_metrics.py "${GA_FILES[@]}" --every "$EVERY" --emit --parameters-out "$PARAMETERS" --sources-out "$SOURCES"
	python tournament/setup_tournament.py --parameters "$PARAMETERS" --output "$SCHEDULE"

	NUM_MATCHES=$(( $(wc -l < "$SCHEDULE") - 1 ))
	echo "Schedule generated! Submitting $NUM_MATCHES matches to the Aire queue..."
	sbatch --array=1-$NUM_MATCHES "$0"
	exit 0
fi

python tournament/run_single_match.py --task_id "$SLURM_ARRAY_TASK_ID" --schedule "$SCHEDULE" --parameters "$PARAMETERS" --results-dir "$RESULTS_DIR"
