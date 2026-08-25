"""Web UI assets ship with the package."""

from ledsetup.ble import DeviceHit
from ledsetup.gui import WEB_INDEX, AsyncBridge, JsApi
from ledsetup.session import BleSession
from ledsetup.settings import AppSettings


async def _noop_scan(timeout: float = 10.0) -> list[DeviceHit]:
    return []


def test_web_index_exists() -> None:
    folder = WEB_INDEX.parent
    assert WEB_INDEX.is_file()
    assert (folder / "app.css").is_file()
    assert (folder / "app.js").is_file()


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
    finally:
        bridge.stop()
