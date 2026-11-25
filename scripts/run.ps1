Set-Location (Join-Path $PSScriptRoot "..\backend")
Write-Host "HPCFlow running at http://127.0.0.1:8000 (Ctrl+C to stop)"
& "..\.venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000