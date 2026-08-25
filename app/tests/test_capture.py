"""Monitor list / resolve — no live capture."""

import pytest

from fake_screen import SolidGrabber
from ledsetup.capture import MonitorInfo, grab_average, monitors_from_mss_dicts, resolve_monitor
from ledsetup.exceptions import CaptureError


def _primary() -> MonitorInfo:
    return MonitorInfo(
        id="0,0,1920x1080",
        index=1,
        left=0,
        top=0,
        width=1920,
        height=1080,
        is_primary=True,
        label="Монитор 1 · 1920×1080 (основной)",
    )


def _second() -> MonitorInfo:
    return MonitorInfo(
        id="1920,0,1280x720",
        index=2,
        left=1920,
        top=0,
        width=1280,
        height=720,
        is_primary=False,
        label="Монитор 2 · 1280×720",
    )


def test_mss_dicts_skip_virtual_desktop() -> None:
    raw = [
        {"left": 0, "top": 0, "width": 3200, "height": 1080},
        {"left": 0, "top": 0, "width": 1920, "height": 1080},
        {"left": 1920, "top": 0, "width": 1280, "height": 720},
    ]
    found = monitors_from_mss_dicts(raw)
    assert len(found) == 2
    assert found[0].is_primary is True
    assert found[0].id == "0,0,1920x1080"
    assert found[1].index == 2
    assert "основной" in found[0].label
    assert "основной" not in found[1].label


def test_mss_dicts_use_is_primary_flag() -> None:
    raw = [
        {"left": 0, "top": 0, "width": 3200, "height": 1200},
        {
            "left": 0,
            "top": 0,
            "width": 1920,
            "height": 1200,
            "is_primary": True,
            "name": "BOE PnP Monitor",
        },
    ]
    found = monitors_from_mss_dicts(raw)
    assert found[0].is_primary is True
    assert found[0].width == 1920


def test_resolve_saved_and_missing() -> None:
    monitors = [_primary(), _second()]
    chosen, note = resolve_monitor(monitors, saved_id=_second().id)
    assert chosen.id == _second().id
    assert note == ""
    fallback, note = resolve_monitor(monitors, saved_id="missing")
    assert fallback.is_primary is True
    assert "основной" in note


def test_resolve_flag_index_and_id() -> None:
    monitors = [_primary(), _second()]
    by_index, _note = resolve_monitor(monitors, flag="2")
    assert by_index.id == _second().id
    by_id, _note = resolve_monitor(monitors, flag=_second().id)
    assert by_id.id == _second().id
    with pytest.raises(CaptureError):
        resolve_monitor(monitors, flag="9")


def test_grab_average_solid_red() -> None:
    assert grab_average(SolidGrabber().monitors()[0], SolidGrabber()) == (255, 0, 0)


def test_grab_average_boosts_dim_red() -> None:
    grabber = SolidGrabber((40, 0, 0))
    assert grab_average(grabber.monitors()[0], grabber) == (255, 0, 0)


def test_grab_average_black_stays_off() -> None:
    grabber = SolidGrabber((0, 0, 0))
    assert grab_average(grabber.monitors()[0], grabber) == (0, 0, 0)
