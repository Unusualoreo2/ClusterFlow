from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import FileResponse
import pandas as pd
import io
import os

# Import analysis module
from analysis import parse_sacct, roofline_analysis

# Initialize FastAPI app
app = FastAPI(title="HPCFlow - HPC Job Performance Analyzer")

# Optional: Add CORS if used with frontend
# from fastapi.middleware.cors import CORSMiddleware
# app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Define expected hardware peak values (can be updated)
PEAK_FLOPS = 1e12  # 1 TFLOPS
PEAK_MEM_BW = 100e9  # 100 GB/s

@app.get("/")
async def home():
    return {
        "message": "Welcome to HPCFlow - HPC Job Performance Analyzer",
        "endpoints": ["/analyze", "/docs", "/redoc"]
    }

@app.post("/analyze")
async def analyze_job(file: UploadFile):
    """
    Upload a Slurm sacct CSV file and return performance insight.
    """
    # Validate file type
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        # Read file content
        content = await file.read()
        df = pd.read_csv(io.StringIO(content.decode()))
        
        # Parse and analyze
        df = parse_sacct(df)
        insight = roofline_analysis(df, peak_flops=PEAK_FLOPS, peak_mem_bw=PEAK_MEM_BW)
        
        # Return result
        return {
            "status": "success",
            "job_id": df["JobID"].iloc[0],
            "elapsed_seconds": df["Elapsed_s"].iloc[0],
            "cpu_util_percent": round(df["CPU_util_percent"].iloc[0], 2),
            "memory_bandwidth_GB": round(df["Memory_bandwidth_GB"].iloc[0], 2),
            "insight": insight
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/docs")
async def get_docs():
    return FileResponse("./docs/swagger-ui.html")

# Optional: Serve static files (for frontend)
@app.get("/static/{file_name}")
async def serve_static(file_name: str):
    file_path = os.path.join("./frontend", file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

# Run with: uvicorn main:app --reload
# Then visit http://localhost:8000