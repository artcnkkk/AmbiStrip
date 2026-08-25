"""Web UI assets ship with the package."""

from ledsetup.ble import DeviceHit
from ledsetup.gui import WEB_INDEX, WINDOW_HEIGHT, WINDOW_WIDTH, AsyncBridge, JsApi
from ledsetup.session import BleSession
from ledsetup.settings import AppSettings


async def _noop_scan(timeout: float = 10.0) -> list[DeviceHit]:
    return []


def test_window_is_wider_than_picker_slice() -> None:
    assert 720 <= WINDOW_WIDTH <= 840
    assert WINDOW_HEIGHT >= 700


def test_web_index_exists() -> None:
    folder = WEB_INDEX.parent
    assert WEB_INDEX.is_file()
    assert (folder / "app.css").is_file()
    assert (folder / "app.js").is_file()


def test_sync_controls_only_on_color_view() -> None:
    html = WEB_INDEX.read_text(encoding="utf-8")
    device, _sep, color = html.partition('id="view-color"')
    assert "btn-sync" not in device
    assert "monitor-select" not in device
    assert "btn-sync" in color
    assert "monitor-select" in color


def test_js_api_exposes_only_callables() -> None:
    bridge = AsyncBridge()
    try:
        api = JsApi(
            BleSession(timeout=1.0),
            bridge,
            device_path=None,
            settings_path=None,
            scan_fn=_noop_scan,
            settings=AppSettings(),
        )
        public = [name for name in dir(api) if not name.startswith("_")]
        assert "window" not in public
        for name in public:
            assert callable(getattr(api, name)), name
        api._syncing = True
        assert api.set_color(9, 8, 7) == {"ok": True}
        assert api._pending is None
    finally:
        bridge.stop()
