#!/bin/bash
#SBATCH --job-name=clusterflow_oom
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:15:00
#SBATCH --output=clusterflow_oom_%j.out
# Set these for your cluster if required (see its documentation):
##SBATCH --partition=<partition>
##SBATCH --account=<account>
# ClusterFlow pilot test job: tries to use 3 GB with 1 GB requested. Expected: state OUT_OF_MEMORY and a request for more memory.
python3 -c "b = b\"x\" * (3 * 1024 * 1024 * 1024)"
