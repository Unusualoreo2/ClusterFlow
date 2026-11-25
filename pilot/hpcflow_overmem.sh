#!/bin/bash
#SBATCH --job-name=hpcflow_overmem
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --output=hpcflow_overmem_%j.out
# Set these for your cluster if required (see its documentation):
##SBATCH --partition=<partition>
##SBATCH --account=<account>
# HPCFlow pilot test job: ~500 MB used of 8 GB. Expected: memory ~6%, suggest --mem of about 625M.
python3 -c "b = b\"x\" * (500 * 1024 * 1024); import time; t=time.time()
while time.time()-t<600: pass"
