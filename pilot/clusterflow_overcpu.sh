#!/bin/bash
#SBATCH --job-name=clusterflow_overcpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=1G
#SBATCH --time=00:15:00
#SBATCH --output=clusterflow_overcpu_%j.out
# Set these for your cluster if required (see its documentation):
##SBATCH --partition=<partition>
##SBATCH --account=<account>
# ClusterFlow pilot test job: 1 busy CPU out of 8 for 10 minutes. Expected: CPU ~12%, suggest --cpus-per-task=2.
python3 -c "import time,sys; t=time.time(); d=float(sys.argv[1])
while time.time()-t<d: pass" 600
