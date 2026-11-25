# ClusterFlow pilot on Kelvin2 (or any Slurm cluster)

Goal: in one short session, check ClusterFlow against jobs whose correct verdict we already know, then try it on your own jobs. Total cost: about 2.5 core-hours.

Cluster-specific details (login address, partition names, whether `--account` is needed, how to load Python) are **not** filled in here: take them from the QUB HPC documentation or your access approval email.

## 1. Copy the files to the cluster

From the `ClusterFlow/MVP` folder on your PC (replace `<user>` and `<login-address>`):

```powershell
scp dist/clusterflow.py <user>@<login-address>:~/clusterflow/
scp -r pilot <user>@<login-address>:~/clusterflow/
```

## 2. Check Python on the login node

```bash
cd ~/clusterflow
python3 --version          # 3.6 or newer is fine
python3 clusterflow.py --days 7
```

If `python3` is missing, load it with the cluster's module system (e.g. `module avail python`). The second command should print a report of your recent jobs (or "0 jobs analysed").

## 3. Set partition/account if the cluster requires them

Open each `pilot/clusterflow_*.sh` file. If the cluster needs a partition or account, remove one `#` from the matching line and fill in the value:

```
#SBATCH --partition=<partition>
```

## 4. Submit the six test jobs

```bash
cd ~/clusterflow/pilot
bash submit_all.sh
squeue -u $USER            # wait until none of the clusterflow_* jobs are listed (about 15 minutes)
```

| Job | Requests | Actually uses | ClusterFlow should say |
|---|---|---|---|
| clusterflow_good | 4 CPUs, 2 GB, 15 min | 4 CPUs, ~1.6 GB, 10 min | nothing to change |
| clusterflow_overcpu | 8 CPUs | 1 CPU | request fewer CPUs |
| clusterflow_overmem | 8 GB | ~0.5 GB | request less memory |
| clusterflow_overtime | 2 hours | 5 minutes | request less time |
| clusterflow_oom | 1 GB | tries 3 GB | ran out of memory |
| clusterflow_timeout | 2 minutes | wants 10 | hit the time limit |

## 5. Check the verdicts automatically

```bash
cd ~/clusterflow/pilot
python3 ../clusterflow.py --days 1 --json > pilot_result.json
python3 check_pilot.py pilot_result.json
```

You get one line per job (`PASS`, `FAIL`, `MISSING` or `INCONCLUSIVE`) and a total such as `6/6 passed`.

- `MISSING`: the job has not finished yet, or failed to submit. Check `squeue -u $USER` and the `clusterflow_*.out` files.
- `INCONCLUSIVE` for `oom`: the cluster let the job use more memory than requested. That is a cluster setting, not an ClusterFlow error.
- `FAIL`: ClusterFlow gave the wrong verdict. This is what the pilot is for.

## 6. Share the results safely

```bash
python3 ../clusterflow.py --days 1 --anonymise
```

`--anonymise` replaces your username, job names and job IDs with `user1`, `job1`, `J1`. Paste that output and the `check_pilot.py` output to the developer. Do not share reports without `--anonymise`, and never run `--all-users` without the HPC team's permission.

## 7. Try it on your own work

```bash
python3 ~/clusterflow/clusterflow.py --days 30
```

The most useful feedback is any recommendation that looks wrong for a job you know well.
