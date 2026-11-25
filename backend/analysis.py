"""
Slurm job efficiency analysis functions.
"""

import re
from math import ceil

SKIP_STATES = ("RUNNING", "PENDING", "REQUEUED", "SUSPENDED", "RESIZING")


def parse_duration(text):
    """
    Parse Slurm duration strings into seconds.
    
    Args:
        text: Duration string in formats like "MM:SS", "MM:SS.fff", "HH:MM:SS", "D-HH:MM:SS"
        
    Returns:
        float | None: Duration in seconds, or None for None, "", "UNLIMITED", "Partition_Limit", "INVALID" or unparseable
    """
    if text is None or text == "" or text in ("UNLIMITED", "Partition_Limit", "INVALID"):
        return None
    
    # Handle D-HH:MM:SS format
    if "-" in text:
        days, time_part = text.split("-", 1)
        days = int(days)
        hours, minutes, seconds = map(float, time_part.split(":"))
        total_seconds = days * 24 * 3600 + hours * 3600 + minutes * 60 + seconds
    # Handle HH:MM:SS format
    elif text.count(":") == 2:
        hours, minutes, seconds = map(float, text.split(":"))
        total_seconds = hours * 3600 + minutes * 60 + seconds
    # Handle MM:SS or MM:SS.fff format
    else:
        minutes, seconds = map(float, text.split(":"))
        total_seconds = minutes * 60 + seconds
    
    return total_seconds


def parse_mem_mb(text):
    """
    Parse memory strings with optional suffixes into MB.
    
    Args:
        text: Memory string like "4200M", "3.5G", "2048K", "1T", or "512"
        
    Returns:
        float | None: Memory in MB, or None for None, "" or unparseable
    """
    if text is None or text == "":
        return None
    
    # Remove whitespace
    text = text.strip()
    
    # Handle suffixes
    if text.endswith("K"):
        value = float(text[:-1])
        result = value / 1024
    elif text.endswith("M"):
        value = float(text[:-1])
        result = value
    elif text.endswith("G"):
        value = float(text[:-1])
        result = value * 1024
    elif text.endswith("T"):
        value = float(text[:-1])
        result = value * 1024 * 1024
    else:
        # No suffix, assume MB
        try:
            result = float(text)
        except ValueError:
            return None
    
    return result


def parse_req_mem(text, alloc_cpus, nodes=1):
    """
    Parse memory request with optional per-CPU or per-node suffix.
    
    Args:
        text: Memory string like "4000Mc", "16Gn", "16G"
        alloc_cpus: Number of allocated CPUs
        nodes: Number of nodes (default 1)
        
    Returns:
        float | None: Memory in MB, or None for None, "" or unparseable
    """
    if text is None or text == "":
        return None
    
    # Remove whitespace
    text = text.strip()
    
    # Check for suffixes
    if text.endswith("c"):
        # Per CPU
        mem_mb = parse_mem_mb(text[:-1])
        if mem_mb is not None:
            return mem_mb * alloc_cpus
    elif text.endswith("n"):
        # Per node
        mem_mb = parse_mem_mb(text[:-1])
        if mem_mb is not None:
            return mem_mb * nodes
    else:
        # Plain memory request
        return parse_mem_mb(text)
    
    return None


def read_sacct(text):
    """
    Read sacct output into list of dictionaries.
    
    Args:
        text: sacct output with header line and rows
        
    Returns:
        list[dict]: List of row dictionaries with stripped keys and values
    """
    if not text:
        return []
    
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    if not lines:
        return []
    
    # Determine delimiter from header
    header_line = lines[0]
    delimiter = "|" if "|" in header_line else ","
    
    # Parse header
    headers = [h.strip() for h in header_line.split(delimiter)]
    
    # Parse rows
    result = []
    for line in lines[1:]:
        values = [v.strip() for v in line.split(delimiter)]
        # Skip if this line's values match the header names exactly
        if values == headers:
            continue
        row_dict = {}
        for i, header in enumerate(headers):
            if i < len(values):
                row_dict[header] = values[i]
            else:
                row_dict[header] = ""
        result.append(row_dict)
    
    return result


def merge_steps(rows):
    """
    Group rows by JobID prefix and merge steps into parent jobs.
    
    Args:
        rows: List of job dictionaries from read_sacct
        
    Returns:
        list[dict]: Merged job dictionaries with max MaxRSS
    """
    # Group by base JobID (before first ".")
    job_groups = {}
    for row in rows:
        job_id = row["JobID"]
        # Split on "." to get base job ID
        base_job_id = job_id.split(".", 1)[0]
        
        if base_job_id not in job_groups:
            job_groups[base_job_id] = []
        job_groups[base_job_id].append(row)
    
    # Merge steps into parents
    merged_jobs = []
    for base_job_id, job_list in job_groups.items():
        # Find parent (job without ".")
        parent_row = None
        step_rows = []
        
        for row in job_list:
            if "." not in row["JobID"]:
                parent_row = row
            else:
                step_rows.append(row)
        
        # If no parent, skip this group
        if parent_row is None:
            continue
            
        # Create merged job (copy parent)
        merged_job = dict(parent_row)
        
        # Find max MaxRSS among all steps and parent, keeping original text format
        max_rss_mb = None
        winning_row = None
        for row in [parent_row] + step_rows:
            if "MaxRSS" in row and row["MaxRSS"]:
                rss_mb = parse_mem_mb(row["MaxRSS"])
                if rss_mb is not None:
                    if max_rss_mb is None or rss_mb > max_rss_mb:
                        max_rss_mb = rss_mb
                        winning_row = row
        
        # Set the MaxRSS to the original text of the row with maximum value
        if winning_row is not None and "MaxRSS" in winning_row and winning_row["MaxRSS"]:
            merged_job["MaxRSS"] = winning_row["MaxRSS"]
        else:
            merged_job["MaxRSS"] = ""
        
        merged_jobs.append(merged_job)
    
    return merged_jobs


def analyze_job(job):
    """
    Analyze a single job and generate metrics and recommendations.
    
    Args:
        job: Dictionary with job data
        
    Returns:
        dict: Analysis results with metrics and recommendations
    """
    # Extract values
    job_id = job.get("JobID", "")
    name = job.get("JobName", "")
    state = job.get("State", "")
    elapsed_str = job.get("Elapsed", "")
    timelimit_str = job.get("Timelimit", "")
    alloc_cpus_str = job.get("AllocCPUS", "")
    total_cpu_str = job.get("TotalCPU", "")
    req_mem_str = job.get("ReqMem", "")
    max_rss_str = job.get("MaxRSS", "")
    
    # Parse durations
    elapsed_s = parse_duration(elapsed_str)
    timelimit_s = parse_duration(timelimit_str)
    total_cpu_s = parse_duration(total_cpu_str)
    
    # Parse CPU count
    try:
        alloc_cpus = int(alloc_cpus_str) if alloc_cpus_str else 0
    except ValueError:
        alloc_cpus = 0
    
    # Parse memory values
    req_mem_mb = parse_req_mem(req_mem_str, alloc_cpus)
    max_rss_mb = parse_mem_mb(max_rss_str)
    
    # Calculate metrics
    cpu_efficiency = None
    memory_efficiency = None
    time_used = None
    wasted_core_hours = None
    
    if elapsed_s is not None and elapsed_s > 0:
        if total_cpu_s is not None:
            cpu_efficiency = (total_cpu_s / (elapsed_s * alloc_cpus)) * 100 if alloc_cpus > 0 else None
        
        if req_mem_mb is not None and req_mem_mb > 0:
            memory_efficiency = (max_rss_mb / req_mem_mb) * 100 if max_rss_mb is not None else None
    
    if timelimit_s is not None and timelimit_s > 0:
        time_used = (elapsed_s / timelimit_s) * 100
    
    if elapsed_s is not None and total_cpu_s is not None:
        wasted_core_hours = max(0, (elapsed_s * alloc_cpus - total_cpu_s) / 3600)
    
    # Generate recommendations
    recommendations = []
    
    # Check for out of memory or timeout states
    if state.startswith("OUT_OF_MEMORY"):
        rec = "Job ran out of memory: request more memory"
        if max_rss_mb is not None:
            mem_req = ceil(max_rss_mb * 1.5)
            rec += f" (e.g. --mem={mem_req}M)."
        else:
            rec += "."
        recommendations.append(rec)
    elif state.startswith("TIMEOUT"):
        recommendations.append("Job hit its time limit: request more time or add checkpointing.")
    
    # CPU efficiency recommendation
    if cpu_efficiency is not None and cpu_efficiency < 50 and alloc_cpus > 1:
        new_cpus = max(1, ceil(alloc_cpus * cpu_efficiency / 100 * 1.2))
        recommendations.append(f"CPU efficiency is {cpu_efficiency:.1f}%: request --cpus-per-task={new_cpus} CPUs instead of {alloc_cpus}, or check the code really runs in parallel.")
    
    # Memory efficiency recommendation
    if memory_efficiency is not None and memory_efficiency < 50:
        if max_rss_mb is not None:
            new_mem = ceil(max_rss_mb * 1.25)
            recommendations.append(f"Memory efficiency is {memory_efficiency:.1f}%: request --mem={new_mem}M instead.")
    
    # High memory efficiency warning
    if memory_efficiency is not None and memory_efficiency > 90 and not state.startswith("OUT_OF_MEMORY"):
        recommendations.append(f"Peak memory is {memory_efficiency:.1f}% of the request: the job is close to its memory limit, request a little more to be safe.")
    
    # Time usage recommendation
    if elapsed_s is not None and elapsed_s > 0 and time_used is not None and time_used < 25:
        # Calculate new time limit (elapsed * 1.5 rounded up to next 15 min)
        new_time_limit_s = elapsed_s * 1.5
        # Round up to next multiple of 900 seconds (15 minutes)
        rounded_seconds = ceil(new_time_limit_s / 900) * 900
        
        # Convert back to HH:MM:SS format
        hours = int(rounded_seconds // 3600)
        minutes = int((rounded_seconds % 3600) // 60)
        seconds = int(rounded_seconds % 60)
        new_limit_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        recommendations.append(f"Only {time_used:.1f}% of the time limit was used: request --time={new_limit_str} instead.")
    
    return {
        "job_id": job_id,
        "name": name,
        "state": state,
        "elapsed_s": elapsed_s,
        "alloc_cpus": alloc_cpus,
        "cpu_efficiency": cpu_efficiency,
        "memory_efficiency": memory_efficiency,
        "time_used": time_used,
        "wasted_core_hours": wasted_core_hours,
        "recommendations": recommendations,
        "user": job.get("User", "") or "",
        "partition": job.get("Partition", "") or ""
    }


def summarize_groups(results, key):
    """Group analysed jobs by results[i][key]; return a list of dicts sorted by wasted_core_hours (desc), then name."""
    # name = the value, or "(unknown)" if it is "".
    # each group dict: {"name", "job_count", "avg_cpu_efficiency", "avg_memory_efficiency", "wasted_core_hours"}
    # averages ignore None values and are None if nothing to average; wasted_core_hours sums non-None values (0.0 if none).
    # sort: key=lambda g: (-g["wasted_core_hours"], g["name"])
    
    groups = {}
    for job in results:
        value = job.get(key, "")
        if value == "":
            name = "(unknown)"
        else:
            name = value
        if name not in groups:
            groups[name] = {
                "name": name,
                "job_count": 0,
                "avg_cpu_efficiency": None,
                "avg_memory_efficiency": None,
                "wasted_core_hours": 0.0,
                "_cpu_n": 0,
                "_mem_n": 0
            }
        group = groups[name]
        group["job_count"] += 1
        
        # Handle wasted core hours (sum)
        wasted_core_hours = job.get("wasted_core_hours")
        if wasted_core_hours is not None:
            group["wasted_core_hours"] += wasted_core_hours
        
        # Handle averages
        cpu_eff = job.get("cpu_efficiency")
        mem_eff = job.get("memory_efficiency")
        
        if cpu_eff is not None:
            if group["avg_cpu_efficiency"] is None:
                group["avg_cpu_efficiency"] = cpu_eff
            else:
                group["avg_cpu_efficiency"] += cpu_eff
            group["_cpu_n"] += 1
        
        if mem_eff is not None:
            if group["avg_memory_efficiency"] is None:
                group["avg_memory_efficiency"] = mem_eff
            else:
                group["avg_memory_efficiency"] += mem_eff
            group["_mem_n"] += 1
    
    # Convert sums to averages where applicable
    for group in groups.values():
        if group["avg_cpu_efficiency"] is not None:
            group["avg_cpu_efficiency"] /= group["_cpu_n"]
        if group["avg_memory_efficiency"] is not None:
            group["avg_memory_efficiency"] /= group["_mem_n"]
        
        # Remove helper keys
        del group["_cpu_n"]
        del group["_mem_n"]
    
    # Convert to list and sort
    result = list(groups.values())
    result.sort(key=lambda g: (-g["wasted_core_hours"], g["name"]))
    
    return result


def analyze(text):
    """
    Analyze sacct output and return job analysis.
    
    Args:
        text: sacct output
        
    Returns:
        dict: Analysis results with jobs, skipped count, and summary statistics
        
    Raises:
        ValueError: If required columns are missing from the header
    """
    rows = read_sacct(text)
    
    # Check for required columns
    headers = set()
    if rows:
        headers = set(rows[0].keys())
    
    required_columns = {"JobID", "State", "Elapsed", "AllocCPUS", "TotalCPU"}
    missing_columns = required_columns - headers
    
    if missing_columns:
        raise ValueError(f"Missing columns in sacct header: {', '.join(missing_columns)}")
    
    # Merge steps
    jobs = merge_steps(rows)
    
    # Skip running, pending, requeued, suspended, and resizing jobs
    skipped = 0
    filtered_jobs = []
    for job in jobs:
        state = job.get("State", "")
        if any(state.startswith(skip_state) for skip_state in SKIP_STATES):
            skipped += 1
        else:
            filtered_jobs.append(job)
    
    # Analyze jobs
    analyzed_jobs = [analyze_job(job) for job in filtered_jobs]
    
    # Calculate summary statistics
    job_count = len(analyzed_jobs)
    total_wasted_core_hours = 0
    
    avg_cpu_efficiency = None
    avg_memory_efficiency = None
    
    cpu_efficiencies = []
    memory_efficiencies = []
    
    for job in analyzed_jobs:
        if job["wasted_core_hours"] is not None:
            total_wasted_core_hours += job["wasted_core_hours"]
        
        if job["cpu_efficiency"] is not None:
            cpu_efficiencies.append(job["cpu_efficiency"])
        
        if job["memory_efficiency"] is not None:
            memory_efficiencies.append(job["memory_efficiency"])
    
    if cpu_efficiencies:
        avg_cpu_efficiency = sum(cpu_efficiencies) / len(cpu_efficiencies)
    
    if memory_efficiencies:
        avg_memory_efficiency = sum(memory_efficiencies) / len(memory_efficiencies)
    
    # Get header columns from rows to check for User and Partition
    headers = set()
    if rows:
        headers = set(rows[0].keys())
    
    # Build by_user and by_partition summaries
    by_user = []
    by_partition = []
    
    if "User" in headers:
        by_user = summarize_groups(analyzed_jobs, "user")
    
    if "Partition" in headers:
        by_partition = summarize_groups(analyzed_jobs, "partition")
    
    return {
        "jobs": analyzed_jobs,
        "skipped": skipped,
        "summary": {
            "job_count": job_count,
            "avg_cpu_efficiency": avg_cpu_efficiency,
            "avg_memory_efficiency": avg_memory_efficiency,
            "total_wasted_core_hours": total_wasted_core_hours,
            "by_user": by_user,
            "by_partition": by_partition
        }
    }