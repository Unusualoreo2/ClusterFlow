#!/bin/bash
#SBATCH --job-name=hpcflow_good
#SBATCH --cpus-per-task=4
#SBATCH --mem=2G
#SBATCH --time=00:15:00
#SBATCH --output=hpcflow_good_%j.out
# Set these for your cluster if required (see its documentation):
##SBATCH --partition=<partition>
##SBATCH --account=<account>
# HPCFlow pilot test job: 4 busy CPUs, ~1.6 GB of 2 GB, 10 of 15 minutes. Expected: no recommendations.
for i in 1 2 3 4; do python3 -c "import time,sys; t=time.time(); d=float(sys.argv[1])
while time.time()-t<d: pass" 600 & done
python3 -c "b = b\"x\" * (1600 * 1024 * 1024); import time; time.sleep(590)" &
wait
