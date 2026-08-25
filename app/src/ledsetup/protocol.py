"""LEDnetWF power/RGB frames from open reverse engineering.

RGB 0B 31 and off 0B 3B 24 were visually confirmed on this analog kit.
Do not send chip-type, LED-count, smear, or other config frames from
addressable firmware dumps. HSV / on / seq / checksum remain TBD.
"""

from __future__ import annotations

import colorsys
from typing import Literal

from ledsetup.color import check_rgb

# RGB/off: visually confirmed 2026-08-25. HSV and on: reverse only.
RGB_OFF_VISUALLY_CONFIRMED = True
HSV_FRAME_IS_HYPOTHESIS = True
ON_FRAME_IS_HYPOTHESIS = True
HYPOTHESIS_NOTE = (
    "hypothesis from open Zengge/LEDnetWF reverse; not verified on this kit "
    "(HSV / on / seq / checksum TBD)"
)
RGB_OFF_NOTE = (
    "RGB 0B 31 and off 0B 3B 24 visually confirmed on this analog kit "
    "(seq/checksum and extra bytes TBD)"
)

ColorFrameKind = Literal["rgb", "hsv"]

# Analog RGB kit uses raw RGB after 0B 31 (confirmed visually). HSV after 0B 3B A1
# is the ring-light variant and was not tried on this kit.
DEFAULT_COLOR_KIND: ColorFrameKind = "rgb"

# Unknown padding/flag bytes copied from reverse, not invented. TBD on device.
_RGB_TRAILER = bytes.fromhex("00 00 0F")  # TBD
_POWER_TAIL = bytes.fromhex("00 00 00 00 00 00 00 32 00 00")  # TBD (0x32 unknown)


def _checksum_after_0b(body_including_0b: bytes) -> int:
    """Sum of bytes after the 0x0B marker, excluding checksum. Often ignored by devices."""
    if not body_including_0b or body_including_0b[0] != 0x0B:
        raise ValueError("body must start with 0x0B")
    return sum(body_including_0b[1:]) & 0xFF


def wrap_frame(body_including_0b: bytes, seq: int = 1) -> bytes:
    """Build a single-fragment LEDnetWF frame (header + lengths + body + checksum)."""
    if not body_including_0b or body_including_0b[0] != 0x0B:
        raise ValueError("payload body must start with 0x0B (hypothesis)")
    seq_byte = seq & 0xFF
    n = len(body_including_0b)
    header = bytes([0x00, seq_byte, 0x80, 0x00, 0x00, n, n + 1])
    return header + body_including_0b + bytes([_checksum_after_0b(body_including_0b)])


def build_on_frame(seq: int = 1) -> bytes:
    """Power on: 0B 3B 23 (hypothesis; not sent in the confirmed visual run)."""
    body = bytes([0x0B, 0x3B, 0x23]) + _POWER_TAIL
    return wrap_frame(body, seq=seq)


def build_off_frame(seq: int = 1) -> bytes:
    """Power off: 0B 3B 24 (visually confirmed: strip went dark)."""
    body = bytes([0x0B, 0x3B, 0x24]) + _POWER_TAIL
    return wrap_frame(body, seq=seq)


def build_rgb_frame(red: int, green: int, blue: int, seq: int = 1) -> bytes:
    """Solid RGB after 0B 31 (visually confirmed). Entire strip, one color."""
    check_rgb(red, green, blue)
    body = bytes([0x0B, 0x31, red, green, blue]) + _RGB_TRAILER
    return wrap_frame(body, seq=seq)


def rgb_to_lednetwf_hsv(red: int, green: int, blue: int) -> tuple[int, int, int]:
    """Hue/2, saturation 0–100, value 0–100 — ring-light reverse (hypothesis)."""
    check_rgb(red, green, blue)
    hue, sat, val = colorsys.rgb_to_hsv(red / 255.0, green / 255.0, blue / 255.0)
    h_byte = int(hue * 360) // 2
    s_byte = int(sat * 100)
    v_byte = int(val * 100)
    return h_byte, s_byte, v_byte


def build_hsv_frame(red: int, green: int, blue: int, seq: int = 1) -> bytes:
    """Solid color as HSV after 0B 3B A1 (hypothesis, ring-light reverse)."""
    h_byte, s_byte, v_byte = rgb_to_lednetwf_hsv(red, green, blue)
    body = bytes(
        [0x0B, 0x3B, 0xA1, h_byte, s_byte, v_byte, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
    )
    return wrap_frame(body, seq=seq)


def build_color_frame(
    red: int,
    green: int,
    blue: int,
    kind: ColorFrameKind = DEFAULT_COLOR_KIND,
    seq: int = 1,
) -> bytes:
    if kind == "hsv":
        return build_hsv_frame(red, green, blue, seq=seq)
    if kind == "rgb":
        return build_rgb_frame(red, green, blue, seq=seq)
    raise ValueError(f"unknown color frame kind: {kind!r}")


def frame_to_hex(frame: bytes) -> str:
    return " ".join(f"{b:02X}" for b in frame)
