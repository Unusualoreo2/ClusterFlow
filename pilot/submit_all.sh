#!/bin/bash
# Submit the six ClusterFlow pilot test jobs. They use about 2.5 core-hours in total.
cd "$(dirname "$0")"
for f in clusterflow_*.sh; do
  sbatch "$f"
done
# clusterflow.py is next to this folder when copied as in docs/pilot-guide.md, or in ../dist in the repository
CLUSTERFLOW=../clusterflow.py
[ -f "$CLUSTERFLOW" ] || CLUSTERFLOW=../dist/clusterflow.py
echo
echo "Submitted. Wait until no clusterflow_* jobs are listed by: squeue -u \$USER"
echo "Then run:"
echo "  python3 $CLUSTERFLOW --days 1 --json > pilot_result.json"
echo "  python3 check_pilot.py pilot_result.json"
