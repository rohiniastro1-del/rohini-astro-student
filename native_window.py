from __future__ import annotations

import ctypes
import os
import sys
import threading
from pathlib import Path

import webview
from flask import jsonify
from werkzeug.serving import make_server

from app import app


APP_TITLE = "Рохини Астро Студент"
APP_ROOT = Path(__file__).resolve().parent
WINDOWS_ICON = APP_ROOT / "assets" / "windows" / "rohini-astro-student-windows.ico"
WINDOWS_APP_ID = "bg.rohiniastro.student.desktop.v1.2026"
WINDOWS_INSTANCE_MUTEX = "Local\\RohiniAstroStudentDesktop_v1"
WEBVIEW_STORAGE = (
    Path(os.environ.get("LOCALAPPDATA", Path.home()))
    / "Rohini Astro Student"
    / "WebView2"
)
_instance_mutex_handle = None


class WindowApi:
    def __init__(self, *, maximized: bool = False) -> None:
        self._window = None
        self._maximized = maximized

    def set_window(self, window) -> None:
        self._window = window

    def minimize(self) -> bool:
        if self._window is not None:
            self._window.minimize()
        return self._maximized

    def start_maximized(self) -> None:
        """Let Windows maximize after it has recorded normal restore bounds."""
        if self._window is not None:
            self._window.maximize()
            self._maximized = True

    def toggle_maximize(self) -> bool:
        if self._window is None:
            return self._maximized
        if self._maximized:
            self._window.restore()
            self._maximized = False
        else:
            self._window.maximize()
            self._maximized = True
        return self._maximized

    def close(self) -> None:
        if self._window is not None:
            self._window.destroy()

    def state(self) -> bool:
        return self._maximized


window_api = WindowApi(maximized=False)


@app.post("/__rohini_window/<action>")
def native_window_action(action: str):
    if action == "minimize":
        maximized = window_api.minimize()
    elif action == "maximize":
        maximized = window_api.toggle_maximize()
    elif action == "close":
        window_api.close()
        maximized = window_api.state()
    elif action == "state":
        maximized = window_api.state()
    else:
        return jsonify({"ok": False, "error": "unknown action"}), 404
    return jsonify({"ok": True, "maximized": maximized})


def set_windows_app_identity() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


def acquire_single_instance() -> bool:
    """Keep one desktop instance and expose a reliable installer check."""
    global _instance_mutex_handle
    if sys.platform != "win32":
        return True

    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.SetLastError(0)
        handle = kernel32.CreateMutexW(None, False, WINDOWS_INSTANCE_MUTEX)
        if not handle:
            return True
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            kernel32.CloseHandle(handle)
            return False
        _instance_mutex_handle = handle
    except (AttributeError, OSError):
        return True
    return True


def show_already_running_message() -> None:
    try:
        ctypes.windll.user32.MessageBoxW(
            None,
            "Rohini Astro Student вече е стартирана.",
            APP_TITLE,
            0x40,
        )
    except (AttributeError, OSError):
        pass


def main() -> None:
    if not acquire_single_instance():
        show_already_running_message()
        return

    set_windows_app_identity()
    webview.settings["ALLOW_DOWNLOADS"] = True

    server = make_server("127.0.0.1", 0, app, threaded=True)
    port = server.server_port
    threading.Thread(target=server.serve_forever, daemon=True).start()

    window = webview.create_window(
        APP_TITLE,
        f"http://127.0.0.1:{port}/",
        width=1280,
        height=720,
        min_size=(900, 600),
        js_api=window_api,
        frameless=False,
        easy_drag=False,
        maximized=False,
        confirm_close=False,
    )
    window_api.set_window(window)
    window.events.shown += window_api.start_maximized
    webview.start(
        icon=str(WINDOWS_ICON) if WINDOWS_ICON.is_file() else None,
        private_mode=False,
        storage_path=str(WEBVIEW_STORAGE),
    )


if __name__ == "__main__":
    main()
