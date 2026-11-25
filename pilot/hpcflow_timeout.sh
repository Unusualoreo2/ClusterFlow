#!/bin/bash
#SBATCH --job-name=hpcflow_timeout
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:02:00
#SBATCH --output=hpcflow_timeout_%j.out
# Set these for your cluster if required (see its documentation):
##SBATCH --partition=<partition>
##SBATCH --account=<account>
# HPCFlow pilot test job: runs longer than its 2-minute limit. Expected: state TIMEOUT and a request for more time.
python3 -c "import time,sys; t=time.time(); d=float(sys.argv[1])
while time.time()-t<d: pass" 600
