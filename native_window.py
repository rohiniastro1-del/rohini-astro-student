from __future__ import annotations

import threading

import webview
from werkzeug.serving import make_server

from app import app


APP_TITLE = "Рохини Астро Студент"


class WindowApi:
    def __init__(self) -> None:
        self._window = None

    def set_window(self, window) -> None:
        self._window = window

    def minimize(self) -> None:
        if self._window is not None:
            self._window.minimize()

    def toggle_maximize(self) -> None:
        if self._window is None:
            return
        if self._window.maximized:
            self._window.restore()
        else:
            self._window.maximize()

    def close(self) -> None:
        if self._window is not None:
            self._window.destroy()


def main() -> None:
    server = make_server("127.0.0.1", 0, app, threaded=True)
    port = server.server_port
    threading.Thread(target=server.serve_forever, daemon=True).start()

    api = WindowApi()
    window = webview.create_window(
        APP_TITLE,
        f"http://127.0.0.1:{port}/",
        width=1440,
        height=900,
        min_size=(900, 600),
        js_api=api,
        confirm_close=False,
    )
    api.set_window(window)
    webview.start()


if __name__ == "__main__":
    main()
