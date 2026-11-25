#!/bin/bash
# Submit the six HPCFlow pilot test jobs. They use about 2.5 core-hours in total.
cd "$(dirname "$0")"
for f in hpcflow_*.sh; do
  sbatch "$f"
done
# hpcflow.py is next to this folder when copied as in docs/pilot-guide.md, or in ../dist in the repository
HPCFLOW=../hpcflow.py
[ -f "$HPCFLOW" ] || HPCFLOW=../dist/hpcflow.py
echo
echo "Submitted. Wait until no hpcflow_* jobs are listed by: squeue -u \$USER"
echo "Then run:"
echo "  python3 $HPCFLOW --days 1 --json > pilot_result.json"
echo "  python3 check_pilot.py pilot_result.json"
