#!/usr/bin/env python3
"""Run the Landing Page Builder Studio Web Application."""
from __future__ import annotations

import argparse
import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

from web.server import create_app

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")


def open_browser(url: str, delay: float = 1.2) -> None:
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the Landing Page Builder Web Studio")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open the browser")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn auto-reload")
    args = parser.parse_args()

    app = create_app()
    url = f"http://{args.host}:{args.port}"

    print(f"\n========================================================")
    print(f"⚡ Landing Page Builder Studio (Multi-User Web App)")
    print(f"URL: {url}")
    print(f"Isolated Storage: {ROOT_DIR / 'output' / 'projects'}")
    print(f"========================================================\n")

    if not args.no_browser and (args.host == "127.0.0.1" or args.host == "localhost"):
        threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
