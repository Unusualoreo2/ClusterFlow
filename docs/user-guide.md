# HPCFlow User Guide

Welcome to HPCFlow — a lightweight tool to analyze HPC job performance using Slurm logs and the Roofline model.

## 📌 What It Does

- Parses `sacct` output from Slurm.
- Computes CPU utilization and memory bandwidth.
- Applies Roofline logic to classify jobs as:
  - Memory-bound
  - Compute-bound
  - Balanced
- Recommends optimization strategies.

## 🛠️ How to Use

### 1. Prepare Your Data

Run on your HPC cluster:
```bash
sacct -j <jobid> --format=JobID,Elapsed,MaxRSS,MaxCPU,MaxVMSize,AllocNodes --noheader > job.csv
```

### 2. Upload the CSV

1. Open `frontend/index.html` in a browser.
2. Click "Choose File" and select your `job.csv`.
3. Click "Analyze Job".

### 3. Read the Insight

You’ll see:
- Job ID
- Elapsed time
- CPU utilization
- Memory bandwidth
- **Insight**: e.g., "Memory-bound: optimize data layout"

## 🧠 Example

Input (`job.csv`):
```
JobID,Elapsed,MaxRSS,MaxCPU,MaxVMSize,AllocNodes
12345,01:05:30,4200,80.5,5000,1
```

Output:
```
Insight: Memory-bound: optimize data layout, reduce cache misses
CPU Utilization: 80.5%
Memory Bandwidth: 0.007 GB/s
```

## ⚙️ Technical Details

- **Hardware Assumptions**:
  - Peak FLOPS: 1e12
  - Peak Memory Bandwidth: 100e9 GB/s
- Adjust these in `analysis.py` for your cluster.

## 📌 Troubleshooting

- **File not found?** Ensure it’s a `.csv`.
- **Invalid format?** Check `sacct` output has correct headers.
- **500 error?** Verify `MaxRSS` is in MB, `Elapsed` in HH:MM:SS.

## 📈 Next Steps

- Add real-time monitoring.
- Integrate with Slurm via API.
- Build a dashboard with charts.
- Monetize via freemium SaaS.

---

> This tool is open-source under MIT License. Built for researchers, students, and HPC engineers.

© 2026 HPCFlow