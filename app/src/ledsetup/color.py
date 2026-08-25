"""RGB helpers. Widget/picker may use HSV; the wire uses RGB frames."""

from __future__ import annotations

import colorsys

from ledsetup.types import RGB


def check_rgb(red: int, green: int, blue: int) -> None:
    for name, value in (("r", red), ("g", green), ("b", blue)):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > 255:
            raise ValueError(f"{name} must be an int 0–255, got {value!r}")


def coerce_rgb_byte(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"канал RGB должен быть 0–255, получено {value!r}")
    number = int(value)
    if number < 0 or number > 255:
        raise ValueError(f"канал RGB должен быть 0–255, получено {number}")
    return number


def parse_rgb_channel(value: str) -> int:
    text = value.strip()
    try:
        number = int(text, 10)
    except ValueError as exc:
        raise ValueError(f"ожидалось целое 0–255, получено {value!r}") from exc
    if number < 0 or number > 255:
        raise ValueError(f"канал RGB должен быть 0–255, получено {number}")
    return number


def parse_rgb_triple(raw: str) -> RGB:
    parts = raw.strip().split()
    if len(parts) != 3:
        raise ValueError("ожидалось три числа 0–255, например 255 0 0")
    return (
        parse_rgb_channel(parts[0]),
        parse_rgb_channel(parts[1]),
        parse_rgb_channel(parts[2]),
    )


def hsv_to_rgb_bytes(hue: float, sat: float, val: float) -> RGB:
    red, green, blue = colorsys.hsv_to_rgb(hue, sat, val)
    return (
        round(red * 255),
        round(green * 255),
        round(blue * 255),
    )


def rgb_to_hsv(red: int, green: int, blue: int) -> tuple[float, float, float]:
    return colorsys.rgb_to_hsv(red / 255.0, green / 255.0, blue / 255.0)


def rgb_to_hex(red: int, green: int, blue: int) -> str:
    return f"#{red:02x}{green:02x}{blue:02x}"


def boost_max_value(rgb: RGB) -> RGB:
    """Keep hue/saturation, set value to 1. Black stays black."""
    red, green, blue = rgb
    check_rgb(red, green, blue)
    if red == 0 and green == 0 and blue == 0:
        return (0, 0, 0)
    hue, sat, _val = rgb_to_hsv(red, green, blue)
    return hsv_to_rgb_bytes(hue, sat, 1.0)
