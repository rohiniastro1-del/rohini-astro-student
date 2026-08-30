from __future__ import annotations

import ctypes
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import webview
from flask import jsonify, request
from werkzeug.serving import make_server

from app import CalculationError, app, load_jhd_path


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
INSTANCE_STATE_PATH = WEBVIEW_STORAGE.parent / ".desktop-instance.json"
_instance_mutex_handle = None


class WindowApi:
    def __init__(self, *, maximized: bool = False) -> None:
        self._window = None
        self._maximized = maximized
        self._restore_url = ""

    def set_window(self, window, *, restore_url: str = "") -> None:
        self._window = window
        self._restore_url = restore_url

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

    def show_loaded_chart(self) -> None:
        if self._window is None or not self._restore_url:
            return
        self._window.load_url(self._restore_url)
        try:
            self._window.show()
        except (AttributeError, OSError):
            pass


window_api = WindowApi(maximized=False)


def _show_loaded_chart_after_response() -> None:
    time.sleep(0.1)
    window_api.show_loaded_chart()


@app.post("/__rohini_window/open-jhd")
def native_open_jhd_file():
    payload = request.get_json(silent=True)
    path = str(payload.get("path", "")).strip() if isinstance(payload, dict) else ""
    if not path:
        return jsonify({"ok": False, "error": "Липсва път до .jhd файла."}), 400
    try:
        load_jhd_path(path)
    except (CalculationError, OSError, UnicodeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    threading.Thread(target=_show_loaded_chart_after_response, daemon=True).start()
    return jsonify({"ok": True})


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


def requested_jhd_path(arguments: list[str] | None = None) -> Path | None:
    values = list(sys.argv[1:] if arguments is None else arguments)
    if len(values) != 1:
        return None
    candidate = Path(values[0]).expanduser()
    return candidate if candidate.suffix.lower() == ".jhd" else None


def write_instance_state(port: int) -> None:
    INSTANCE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = INSTANCE_STATE_PATH.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps({"pid": os.getpid(), "port": port}),
        encoding="utf-8",
    )
    os.replace(temporary, INSTANCE_STATE_PATH)


def clear_instance_state() -> None:
    try:
        state = json.loads(INSTANCE_STATE_PATH.read_text(encoding="utf-8"))
        if int(state.get("pid", 0)) == os.getpid():
            INSTANCE_STATE_PATH.unlink(missing_ok=True)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        pass


def forward_jhd_to_running_instance(path: Path) -> bool:
    try:
        state = json.loads(INSTANCE_STATE_PATH.read_text(encoding="utf-8"))
        port = int(state["port"])
        if not 1 <= port <= 65535:
            return False
        body = json.dumps({"path": str(path)}, ensure_ascii=False).encode("utf-8")
        forwarded_request = urllib.request.Request(
            f"http://127.0.0.1:{port}/__rohini_window/open-jhd",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(forwarded_request, timeout=3.0) as response:
            result = json.loads(response.read().decode("utf-8"))
        return response.status == 200 and result.get("ok") is True
    except (
        KeyError,
        OSError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        urllib.error.URLError,
    ):
        return False


def show_file_open_error(message: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, message, APP_TITLE, 0x10)
    except (AttributeError, OSError):
        pass


def main() -> None:
    requested_file = requested_jhd_path()
    if not acquire_single_instance():
        if requested_file is not None and forward_jhd_to_running_instance(requested_file):
            return
        if requested_file is not None:
            show_file_open_error(
                "Rohini Astro Student вече работи, но файлът не можа да бъде "
                "предаден. Отвори го от бутона „Отвори“ в програмата."
            )
        else:
            show_already_running_message()
        return

    set_windows_app_identity()
    webview.settings["ALLOW_DOWNLOADS"] = True

    server = make_server("127.0.0.1", 0, app, threaded=True)
    port = server.server_port
    threading.Thread(target=server.serve_forever, daemon=True).start()
    write_instance_state(port)

    base_url = f"http://127.0.0.1:{port}/"
    initial_url = base_url
    if requested_file is not None:
        try:
            load_jhd_path(requested_file)
            initial_url = f"{base_url}?restore=1"
        except (CalculationError, OSError, UnicodeError, ValueError) as exc:
            show_file_open_error(f"Файлът не можа да бъде отворен.\n\n{exc}")

    window = webview.create_window(
        APP_TITLE,
        initial_url,
        width=1280,
        height=720,
        min_size=(900, 600),
        js_api=window_api,
        frameless=False,
        easy_drag=False,
        maximized=False,
        confirm_close=False,
    )
    window_api.set_window(window, restore_url=f"{base_url}?restore=1")
    window.events.shown += window_api.start_maximized
    try:
        webview.start(
            icon=str(WINDOWS_ICON) if WINDOWS_ICON.is_file() else None,
            private_mode=False,
            storage_path=str(WEBVIEW_STORAGE),
        )
    finally:
        clear_instance_state()
        server.shutdown()


if __name__ == "__main__":
    main()
