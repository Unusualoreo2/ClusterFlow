import pandas as pd
import io

def parse_sacct(df):
    """
    Parse Slurm sacct output and compute metrics.
    - Elapsed → seconds
    - MaxCPU → CPU utilization %
    - MaxRSS → memory bandwidth (GB/s)
    """
    # Convert Elapsed to seconds
    df["Elapsed_s"] = pd.to_timedelta(df["Elapsed"]).dt.total_seconds()
    
    # CPU utilization (MaxCPU is % of total time)
    # MaxCPU / 100 = total CPU seconds used
    df["CPU_util_percent"] = (df["MaxCPU"] / 100) / df["Elapsed_s"] * 100
    
    # Memory bandwidth: MaxRSS / Elapsed_s (in GB)
    # Assume MaxRSS is in MB → convert to GB
    df["Memory_bandwidth_GB"] = (df["MaxRSS"] / 1e6) / df["Elapsed_s"]
    
    return df

def roofline_analysis(df, peak_flops=1e12, peak_mem_bw=100e9):
    """
    Apply Roofline model logic to classify job.
    - peak_flops: theoretical peak FLOPS of target hardware
    - peak_mem_bw: theoretical peak memory bandwidth (GB/s)
    """
    # Normalize to ratio of peak
    flops_ratio = df["MaxCPU"].iloc[0] / peak_flops
    mem_bw_ratio = df["Memory_bandwidth_GB"].iloc[0] / peak_mem_bw
    
    # Rule-based classification
    if flops_ratio < 0.2 and mem_bw_ratio > 0.8:
        return "Memory-bound: optimize data layout, reduce cache misses"
    elif mem_bw_ratio < 0.2 and flops_ratio > 0.8:
        return "Compute-bound: consider vectorization, loop unrolling"
    else:
        return "Balanced: consider both"

# Example usage
if __name__ == "__main__":
    # Simulate input
    data = {
        "JobID": ["12345"],
        "Elapsed": ["01:05:30"],
        "MaxRSS": [4200],  # in MB
        "MaxCPU": [80.5],  # in %
        "MaxVMSize": [5000],
        "AllocNodes": [1]
    }
    df = pd.DataFrame(data)
    df = parse_sacct(df)
    insight = roofline_analysis(df)
    print("Insight:", insight)