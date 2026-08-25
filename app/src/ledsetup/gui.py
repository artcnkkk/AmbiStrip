"""Desktop window via WebView2. Two steps: pick the strip, then set color."""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path

import webview

from ledsetup.ble import scan_devices
from ledsetup.gui_api import JsApi
from ledsetup.gui_bridge import AsyncBridge
from ledsetup.session import BleSession
from ledsetup.settings import load_settings
from ledsetup.types import ScanFn

WEB_INDEX = Path(__file__).resolve().parent / "web" / "index.html"

__all__ = ["WEB_INDEX", "AsyncBridge", "JsApi", "run_gui"]


def run_gui(
    *,
    session: BleSession | None = None,
    device_path: Path | None = None,
    settings_path: Path | None = None,
    scan_fn: ScanFn | None = None,
    auto_connect: bool = True,
) -> int:
    settings = load_settings(settings_path)
    bridge = AsyncBridge()
    held = session or BleSession(timeout=settings.connect_timeout)
    held.timeout = settings.connect_timeout
    api = JsApi(
        held,
        bridge,
        device_path=device_path,
        settings_path=settings_path,
        scan_fn=scan_fn or scan_devices,
        settings=settings,
    )
    if not WEB_INDEX.is_file():
        print(f"нет UI-файла: {WEB_INDEX}")
        bridge.stop()
        return 1

    window = webview.create_window(
        "LEDSetup",
        url=str(WEB_INDEX),
        js_api=api,
        width=480,
        height=760,
        background_color="#0b0c10",
        fullscreen=False,
        maximized=False,
        resizable=False,
    )
    if window is None:
        print("не удалось создать окно WebView")
        bridge.stop()
        return 1
    api._ui = window

    def _closed() -> None:
        # Native window teardown can race the BLE disconnect.
        with suppress(Exception):
            bridge.submit(held.disconnect()).result(timeout=2)
        bridge.stop()

    window.events.closed += _closed
    _ = auto_connect
    try:
        webview.start(gui="edgechromium")
    except Exception:
        # Fallback if WebView2/edgechromium is missing; pywebview picks another backend.
        webview.start()
    return 0
