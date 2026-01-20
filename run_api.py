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

    # Production: disable reload and use multiple workers
    # Development: enable reload (which disables workers)
    is_production = os.getenv("RUNNING_IN_DOCKER", "false").lower() == "true"
    workers = int(os.getenv("API_WORKERS", "4" if is_production else "1"))

    # Reload mode is incompatible with multiple workers
    if reload and workers > 1:
        reload = False

    print(f"Starting WinningCV API on {host}:{port}")
    print(f"API docs: http://{host}:{port}/api/docs")
    print(f"Mode: {'Production' if is_production else 'Development'} (workers={workers}, reload={reload})")

    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers if not reload else 1,
        log_level="info",
        timeout_keep_alive=30,
    )
