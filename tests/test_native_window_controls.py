import unittest
from pathlib import Path

import native_window
from native_window import WindowApi, app, window_api


class FakeWindow:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def minimize(self) -> None:
        self.calls.append("minimize")

    def maximize(self) -> None:
        self.calls.append("maximize")

    def restore(self) -> None:
        self.calls.append("restore")

    def destroy(self) -> None:
        self.calls.append("destroy")


class NativeWindowControlTests(unittest.TestCase):
    def test_startup_maximizes_after_normal_bounds_exist(self) -> None:
        fake = FakeWindow()
        api = WindowApi(maximized=False)
        api.set_window(fake)

        api.start_maximized()

        self.assertTrue(api.state())
        self.assertEqual(fake.calls, ["maximize"])

    def test_window_api_tracks_restore_and_maximize(self) -> None:
        fake = FakeWindow()
        api = WindowApi(maximized=True)
        api.set_window(fake)

        self.assertFalse(api.toggle_maximize())
        self.assertTrue(api.toggle_maximize())
        self.assertTrue(api.minimize())
        api.close()

        self.assertEqual(fake.calls, ["restore", "maximize", "minimize", "destroy"])

    def test_desktop_uses_the_native_windows_frame(self) -> None:
        source = Path(native_window.__file__).read_text(encoding="utf-8")
        template = (Path(native_window.__file__).parent / "templates" / "index.html").read_text(
            encoding="utf-8"
        )
        styles = (Path(native_window.__file__).parent / "static" / "styles.css").read_text(
            encoding="utf-8"
        )
        self.assertIn("frameless=False", source)
        self.assertIn("private_mode=False", source)
        self.assertIn("storage_path=str(WEBVIEW_STORAGE)", source)
        self.assertNotIn('data-window-action="minimize"', template)
        self.assertNotIn('data-window-action="maximize"', template)
        self.assertNotIn('data-window-action="close"', template)
        self.assertNotIn('class="desktop-menubar__badge"', template)
        self.assertIn("flex: 0 0 190px", styles)
        self.assertIn("max-width: 190px", styles)

    def test_http_controls_reach_the_native_window(self) -> None:
        fake = FakeWindow()
        old_window = window_api._window
        old_maximized = window_api._maximized
        try:
            window_api.set_window(fake)
            window_api._maximized = True
            client = app.test_client()

            state = client.post("/__rohini_window/state")
            restored = client.post("/__rohini_window/maximize")
            minimized = client.post("/__rohini_window/minimize")

            self.assertEqual(state.get_json(), {"ok": True, "maximized": True})
            self.assertEqual(restored.get_json(), {"ok": True, "maximized": False})
            self.assertEqual(minimized.get_json(), {"ok": True, "maximized": False})
            self.assertEqual(fake.calls, ["restore", "minimize"])
        finally:
            window_api._window = old_window
            window_api._maximized = old_maximized

    def test_unknown_window_action_is_rejected(self) -> None:
        response = app.test_client().post("/__rohini_window/not-a-command")
        self.assertEqual(response.status_code, 404)

    def test_single_instance_accepts_the_first_process(self) -> None:
        class Kernel32:
            def SetLastError(self, _value):
                pass

            def CreateMutexW(self, _security, _owner, name):
                self.name = name
                return 123

            def GetLastError(self):
                return 0

        kernel32 = Kernel32()
        old_platform = native_window.sys.platform
        old_windll = native_window.ctypes.windll
        old_handle = native_window._instance_mutex_handle
        try:
            native_window.sys.platform = "win32"
            native_window.ctypes.windll = type("WinDll", (), {"kernel32": kernel32})()
            native_window._instance_mutex_handle = None
            self.assertTrue(native_window.acquire_single_instance())
            self.assertEqual(kernel32.name, native_window.WINDOWS_INSTANCE_MUTEX)
            self.assertEqual(native_window._instance_mutex_handle, 123)
        finally:
            native_window.sys.platform = old_platform
            native_window.ctypes.windll = old_windll
            native_window._instance_mutex_handle = old_handle

    def test_single_instance_rejects_a_second_process(self) -> None:
        class Kernel32:
            def __init__(self):
                self.closed = []

            def SetLastError(self, _value):
                pass

            def CreateMutexW(self, _security, _owner, _name):
                return 456

            def GetLastError(self):
                return 183

            def CloseHandle(self, handle):
                self.closed.append(handle)

        kernel32 = Kernel32()
        old_platform = native_window.sys.platform
        old_windll = native_window.ctypes.windll
        old_handle = native_window._instance_mutex_handle
        try:
            native_window.sys.platform = "win32"
            native_window.ctypes.windll = type("WinDll", (), {"kernel32": kernel32})()
            native_window._instance_mutex_handle = None
            self.assertFalse(native_window.acquire_single_instance())
            self.assertEqual(kernel32.closed, [456])
            self.assertIsNone(native_window._instance_mutex_handle)
        finally:
            native_window.sys.platform = old_platform
            native_window.ctypes.windll = old_windll
            native_window._instance_mutex_handle = old_handle


if __name__ == "__main__":
    unittest.main()
