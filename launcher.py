from __future__ import annotations

import socket
import threading
import time
import urllib.request

import uvicorn
import webview

from app.core.config import settings
from app.main import app


def _port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) != 0


def _wait_for_server(url: str, timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                return response.status == 200
        except Exception:
            time.sleep(0.3)
    return False


def _create_app_window(url: str) -> webview.Window:
    return webview.create_window(
        "autoWechat Console",
        url,
        width=1280,
        height=820,
        min_size=(980, 680),
    )


def main() -> None:
    host = settings.host
    port = settings.port
    url = f"http://{host}:{port}"

    if not _port_available(host, port):
        _create_app_window(url)
        webview.start()
        return

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=False,
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    if not _wait_for_server(f"{url}/api/health"):
        server.should_exit = True
        raise RuntimeError("autoWechat Console failed to start")

    try:
        _create_app_window(url)
        webview.start()
    finally:
        server.should_exit = True
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
