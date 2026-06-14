"""
Entry point for running the Virtual HR Platform backend server.

Usage:
    python run.py                   # development mode with auto-reload
    python run.py --host 0.0.0.0    # bind to all interfaces
    python run.py --port 8080       # custom port
"""
import argparse
import os
import sys

# Ensure the backend directory is in Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn


def parse_args():
    parser = argparse.ArgumentParser(description="Virtual HR Platform API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable auto-reload (use in production)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (production)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    print(f"Starting Virtual HR Platform API...")
    print(f"  Host:    {args.host}")
    print(f"  Port:    {args.port}")
    print(f"  Reload:  {not args.no_reload}")
    print(f"  Docs:    http://{args.host}:{args.port}/docs")
    print(f"  Health:  http://{args.host}:{args.port}/health")
    print()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=not args.no_reload,
        workers=args.workers if args.no_reload else 1,
        log_level="info",
    )
