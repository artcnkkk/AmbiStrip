"""Last-selected BLE peripheral. Address is the ID; advertised name is not stable."""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from ledsetup.ble import DeviceHit
from ledsetup.exceptions import DeviceNotSelectedError, SelectionError
from ledsetup.paths import default_app_dir

__all__ = [
    "DeviceNotSelectedError",
    "SelectedDevice",
    "SelectionError",
    "addresses_equal",
    "clear_selected",
    "default_store_path",
    "format_scan_line",
    "load_selected",
    "normalize_address",
    "parse_choice_index",
    "resolve_address",
    "save_selected",
    "select_hit",
    "selected_from_hit",
]


@dataclass(frozen=True)
class SelectedDevice:
    address: str
    name: str = ""


def default_store_path() -> Path:
    override = os.environ.get("LEDSETUP_DEVICE_FILE")
    if override:
        return Path(override)
    return default_app_dir() / "selected-device.json"


def normalize_address(value: str) -> str:
    cleaned = value.strip().upper().replace("-", ":")
    if ":" in cleaned:
        parts = [p for p in cleaned.split(":") if p]
        if len(parts) == 6 and all(
            len(p) == 2 and all(c in "0123456789ABCDEF" for c in p) for p in parts
        ):
            return ":".join(parts)
    hex_only = "".join(c for c in cleaned if c in "0123456789ABCDEF")
    if len(hex_only) == 12:
        return ":".join(hex_only[i : i + 2] for i in range(0, 12, 2))
    raise ValueError(f"некорректный BLE-адрес: {value!r}")


def addresses_equal(left: str, right: str) -> bool:
    try:
        return normalize_address(left) == normalize_address(right)
    except ValueError:
        return left.strip().upper() == right.strip().upper()


def load_selected(path: Path | None = None) -> SelectedDevice | None:
    store = path or default_store_path()
    try:
        raw = json.loads(store.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    address = raw.get("address")
    if not isinstance(address, str) or not address.strip():
        return None
    try:
        address = normalize_address(address)
    except ValueError:
        return None
    name = raw.get("name")
    name_str = name.strip() if isinstance(name, str) else ""
    return SelectedDevice(address=address, name=name_str)


def save_selected(device: SelectedDevice, path: Path | None = None) -> Path:
    store = path or default_store_path()
    store.parent.mkdir(parents=True, exist_ok=True)
    payload = {"address": normalize_address(device.address), "name": device.name}
    tmp = store.with_name(store.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(store)
    return store


def clear_selected(path: Path | None = None) -> None:
    store = path or default_store_path()
    try:
        store.unlink()
    except FileNotFoundError:
        return


def parse_choice_index(raw: str, count: int) -> int:
    """Parse a 1-based index from user input. Returns 0-based list index."""
    text = raw.strip()
    if not text:
        raise SelectionError("ничего не выбрано")
    try:
        number = int(text, 10)
    except ValueError as exc:
        raise SelectionError(f"ожидался номер 1–{count}, получено {raw!r}") from exc
    if number < 1 or number > count:
        raise SelectionError(f"номер {number} вне диапазона 1–{count}")
    return number - 1


def select_hit(
    hits: Sequence[DeviceHit],
    *,
    index: int | None = None,
    address: str | None = None,
    name: str | None = None,
) -> DeviceHit:
    flags = [v is not None for v in (index, address, name)]
    if sum(flags) != 1:
        raise SelectionError("укажите ровно один способ: --index, --address или --name")
    if address is not None:
        return _hit_for_address(hits, address)
    if not hits:
        raise SelectionError("список устройств пуст")
    if index is not None:
        if index < 1 or index > len(hits):
            raise SelectionError(f"номер {index} вне диапазона 1–{len(hits)}")
        return hits[index - 1]
    if name is None:
        raise SelectionError("укажите ровно один способ: --index, --address или --name")
    return _hit_for_name(hits, name)


def _hit_for_address(hits: Sequence[DeviceHit], address: str) -> DeviceHit:
    wanted = normalize_address(address)
    for hit in hits:
        if addresses_equal(hit.address, wanted):
            return hit
    return DeviceHit(
        name="",
        address=wanted,
        rssi=None,
        lednetwf=False,
    )


def _hit_for_name(hits: Sequence[DeviceHit], name: str) -> DeviceHit:
    wanted = name.strip()
    if not wanted:
        raise SelectionError("имя пустое")
    exact = [h for h in hits if h.name == wanted]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        addrs = ", ".join(h.address for h in exact)
        raise SelectionError(
            f"имя {wanted!r} совпало с несколькими устройствами ({addrs}); укажите --address"
        )
    folded = wanted.casefold()
    insensitive = [h for h in hits if h.name.casefold() == folded]
    if len(insensitive) == 1:
        return insensitive[0]
    if len(insensitive) > 1:
        addrs = ", ".join(h.address for h in insensitive)
        raise SelectionError(
            f"имя {wanted!r} совпало с несколькими устройствами ({addrs}); укажите --address"
        )
    raise SelectionError(f"в этом scan нет устройства с именем {wanted!r}")


def format_scan_line(index: int, hit: DeviceHit) -> str:
    marker = "*" if hit.lednetwf else " "
    label = hit.name or "(без имени)"
    rssi = f"  RSSI={hit.rssi}" if hit.rssi is not None else ""
    return f"{index:2d}  {marker}  {label}  {hit.address}{rssi}"


def selected_from_hit(hit: DeviceHit) -> SelectedDevice:
    return SelectedDevice(address=normalize_address(hit.address), name=hit.name)


def resolve_address(
    *,
    cli_address: str | None = None,
    path: Path | None = None,
) -> str:
    if cli_address:
        return normalize_address(cli_address)
    selected = load_selected(path)
    if selected is None:
        raise DeviceNotSelectedError()
    return selected.address
