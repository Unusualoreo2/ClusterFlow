from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pathlib import Path
from analysis import analyze
from pydantic import BaseModel

# Constants
FRONTEND = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
EXAMPLE = Path(__file__).resolve().parent.parent / "data" / "example_sacct.txt"
MAX_BYTES = 10 * 1024 * 1024

# Create FastAPI app
app = FastAPI(title="ClusterFlow", version="0.2.0")

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/api/example")
async def example():
    return PlainTextResponse(EXAMPLE.read_text(encoding="utf-8"))

@app.get("/")
async def read_root():
    from fastapi.responses import FileResponse
    return FileResponse(FRONTEND, media_type="text/html")

async def _run(raw: bytes) -> dict:
    # Check file size
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "File is larger than 10 MB.")
    
    # Check for empty or whitespace-only files
    if not raw or not raw.strip():
        raise HTTPException(400, "The file is empty.")
    
    # Check for null bytes or invalid UTF-8
    if b"\x00" in raw:
        raise HTTPException(400, "This does not look like a text sacct export.")
    
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeError:
        raise HTTPException(400, "This does not look like a text sacct export.")
    
    # Call analysis
    try:
        result = analyze(text)
    except ValueError as error:
        raise HTTPException(400, str(error))
    
    return result

@app.post("/api/analyze")
async def analyze_file(file: UploadFile = File(...)):
    # Read at most MAX_BYTES + 1 bytes to check size
    content = await file.read(MAX_BYTES + 1)
    
    # Check if file is too large
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "File is larger than 10 MB.")
    
    return await _run(content)

class TextIn(BaseModel):
    text: str

@app.post("/api/analyze-text")
async def analyze_text(request: TextIn):
    return await _run(request.text.encode("utf-8"))