#!/usr/bin/env python3
"""Run the Landing Page Builder Studio Web Application."""
from __future__ import annotations

import argparse
import socket
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


def get_lan_ip() -> str:
    """Detect local network IP address."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def open_browser(url: str, delay: float = 1.2) -> None:
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the Landing Page Builder Web Studio")
    parser.add_argument("--host", default=None, help="Host to bind (default: 127.0.0.1 or 0.0.0.0 if --lan is used)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--lan", action="store_true", help="Host on LAN (bind to 0.0.0.0 to allow access from other devices)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open the browser")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn auto-reload")
    args = parser.parse_args()

    # Determine host
    if args.host:
        host = args.host
    elif args.lan:
        host = "0.0.0.0"
    else:
        host = "127.0.0.1"

    app = create_app()
    lan_ip = get_lan_ip()

    print(f"\n========================================================")
    print(f"⚡ Landing Page Builder Studio (Multi-User Web App)")
    print(f"➜ Local:   http://localhost:{args.port}")
    if host in ("0.0.0.0", lan_ip):
        print(f"➜ Network: http://{lan_ip}:{args.port}  (Chia sẻ link này trong mạng LAN)")
    else:
        print(f"➜ Network: Chạy với cờ '--lan' để cho phép máy khác trong LAN truy cập")
    print(f"➜ Storage: {ROOT_DIR / 'output' / 'projects'}")
    print(f"========================================================\n")

    if not args.no_browser:
        threading.Thread(target=open_browser, args=(f"http://localhost:{args.port}",), daemon=True).start()

    uvicorn.run(app, host=host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
