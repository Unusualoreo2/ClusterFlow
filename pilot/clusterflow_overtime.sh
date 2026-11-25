#!/bin/bash
#SBATCH --job-name=clusterflow_overtime
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=02:00:00
#SBATCH --output=clusterflow_overtime_%j.out
# Set these for your cluster if required (see its documentation):
##SBATCH --partition=<partition>
##SBATCH --account=<account>
# ClusterFlow pilot test job: 5 minutes used of 2 hours. Expected: time ~4%, suggest --time=00:15:00.
python3 -c "import time,sys; t=time.time(); d=float(sys.argv[1])
while time.time()-t<d: pass" 300
