#!/bin/bash
# Submit the six HPCFlow pilot test jobs. They use about 2.5 core-hours in total.
cd "$(dirname "$0")"
for f in hpcflow_*.sh; do
  sbatch "$f"
done
echo
echo "Submitted. When all six have finished (check with: squeue --me), run:"
echo "  python3 ../dist/hpcflow.py --days 1 --json > pilot_result.json"
echo "  python3 check_pilot.py pilot_result.json"
