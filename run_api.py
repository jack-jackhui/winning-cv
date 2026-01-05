#!/usr/bin/env python3
"""
Run the WinningCV FastAPI server.

Usage:
    python run_api.py
    # or
    uvicorn api.main:app --reload --port 8000
"""
import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    reload = os.getenv("API_RELOAD", "true").lower() == "true"

    print(f"Starting WinningCV API on {host}:{port}")
    print(f"API docs: http://{host}:{port}/api/docs")

    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
