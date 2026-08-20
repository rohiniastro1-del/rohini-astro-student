from __future__ import annotations

import ctypes
import json
import os
import socket
import subprocess
import sys
import time
import traceback
import urllib.request
from pathlib import Path

APP_TITLE = "Rohini Astro"
MUTEX_NAME = r"Local\RohiniAstroDesktopBoard"
ERROR_ALREADY_EXISTS = 183
APP_ROOT = Path(__file__).resolve().parent
CRASH_LOG = APP_ROOT / ".rohini-desktop.crash.log"
STATE_PATH = APP_ROOT / ".rohini-desktop.state.json"
SERVER_SCRIPT = APP_ROOT / "rohini_local_server.py"


def show_message(message: str, *, error: bool = False) -> None:
    icon = 0x10 if error else 0x40
    ctypes.windll.user32.MessageBoxW(None, message, APP_TITLE, icon)


def acquire_single_instance() -> object | None:
    ctypes.windll.kernel32.CreateMutexW.restype = ctypes.c_void_p
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        ctypes.windll.kernel32.CloseHandle(mutex)
        return None
    return mutex


def write_runtime_state(port: int, server_pid: int) -> None:
    temporary_path = STATE_PATH.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "server_pid": server_pid,
                "port": port,
                "app_root": str(APP_ROOT),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    os.replace(temporary_path, STATE_PATH)


def clear_runtime_state() -> None:
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if int(state.get("pid", 0)) == os.getpid():
            STATE_PATH.unlink(missing_ok=True)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass


def reserve_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def wait_for_server(port: int, server_process: subprocess.Popen[bytes]) -> None:
    health_url = f"http://127.0.0.1:{port}/__rohini_health"
    for _attempt in range(80):
        if server_process.poll() is not None:
            raise RuntimeError("Локалният сървър спря при стартиране.")
        try:
            with urllib.request.urlopen(health_url, timeout=0.5) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("Локалният сървър не отговори навреме.")


def main() -> int:
    mutex = acquire_single_instance()
    if mutex is None:
        return 0

    server_process: subprocess.Popen[bytes] | None = None
    try:
        port = reserve_local_port()
        server_process = subprocess.Popen(
            [sys.executable, str(SERVER_SCRIPT), str(port)],
            cwd=str(APP_ROOT),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            close_fds=True,
        )
        wait_for_server(port, server_process)
        write_runtime_state(port, server_process.pid)
        while server_process.poll() is None:
            time.sleep(1)
        raise RuntimeError("Локалният сървър спря неочаквано.")
    finally:
        clear_runtime_state()
        if server_process is not None and server_process.poll() is None:
            server_process.terminate()
            try:
                server_process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                server_process.kill()
        ctypes.windll.kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        CRASH_LOG.write_text(traceback.format_exc(), encoding="utf-8")
        show_message(
            "Рохини Астро не успя да се отвори. Записах подробности в "
            "'.rohini-desktop.crash.log'.",
            error=True,
        )
        sys.exit(1)
