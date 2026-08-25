"""Picker color mapping and write throttle — no BLE, no window."""

from ledsetup.color import hsv_to_rgb_bytes, rgb_to_hsv
from ledsetup.protocol import build_off_frame, build_on_frame, build_rgb_frame
from ledsetup.throttle import ColorThrottle


def test_hsv_red_becomes_rgb_frame_not_hsv_protocol() -> None:
    red, green, blue = hsv_to_rgb_bytes(0.0, 1.0, 1.0)
    frame = build_rgb_frame(red, green, blue)
    assert (red, green, blue) == (255, 0, 0)
    assert frame[8] == 0x31
    assert frame[9:12] == bytes([255, 0, 0])
    assert frame[7:10] != bytes.fromhex("0B 3B A1")


def test_off_and_on_frames() -> None:
    off = build_off_frame()
    on = build_on_frame()
    assert off[8] == 0x3B
    assert off[9] == 0x24
    assert on[8] == 0x3B
    assert on[9] == 0x23


def test_rgb_roundtrip_white() -> None:
    hue, sat, val = rgb_to_hsv(255, 255, 255)
    assert sat == 0
    assert hsv_to_rgb_bytes(hue, sat, val) == (255, 255, 255)


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_throttle_blocks_second_write() -> None:
    clock = _Clock()
    throttle = ColorThrottle(min_interval=0.1, clock=clock)
    first = (255, 0, 0)
    second = (0, 255, 0)
    assert throttle.allow(first) is True
    throttle.mark(first)
    clock.now += 0.05
    assert throttle.allow(second) is False
    clock.now += 0.06
    assert throttle.allow(second) is True
    throttle.mark(second)
    clock.now += 1.0
    assert throttle.allow(second) is False


def test_throttle_clear_after_off_resends_same_rgb() -> None:
    clock = _Clock()
    throttle = ColorThrottle(min_interval=0.1, clock=clock)
    rgb = (10, 20, 30)
    throttle.mark(rgb)
    clock.now += 1.0
    assert throttle.allow(rgb) is False
    throttle.clear_last()
    assert throttle.allow(rgb) is True
