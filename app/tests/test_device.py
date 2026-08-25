"""Device store and scan selection — no BLE adapter."""

from pathlib import Path

import pytest

from ledsetup.ble import DeviceHit
from ledsetup.device import (
    DeviceNotSelectedError,
    SelectionError,
    clear_selected,
    format_scan_line,
    load_selected,
    normalize_address,
    parse_choice_index,
    resolve_address,
    save_selected,
    select_hit,
    selected_from_hit,
)

LEDNET = DeviceHit("LEDnetWFRenamed", "E4:98:BB:6B:1A:AC", -56, True)
OTHER = DeviceHit("Kitchen", "11:22:33:44:55:66", -70, False)
UNNAMED = DeviceHit("", "AA:BB:CC:DD:EE:FF", None, False)
HITS = [LEDNET, OTHER, UNNAMED]


def test_normalize_address_colon_and_hex() -> None:
    assert normalize_address("e4:98:bb:6b:1a:ac") == "E4:98:BB:6B:1A:AC"
    assert normalize_address("E4-98-BB-6B-1A-AC") == "E4:98:BB:6B:1A:AC"
    assert normalize_address("e498bb6b1aac") == "E4:98:BB:6B:1A:AC"


def test_normalize_address_rejects_garbage() -> None:
    with pytest.raises(ValueError, match="некорректный"):
        normalize_address("not-an-address")


def test_save_and_load_selected(tmp_path: Path) -> None:
    path = tmp_path / "selected-device.json"
    save_selected(selected_from_hit(LEDNET), path=path)
    loaded = load_selected(path)
    assert loaded is not None
    assert loaded.address == "E4:98:BB:6B:1A:AC"
    assert loaded.name == "LEDnetWFRenamed"


def test_clear_selected(tmp_path: Path) -> None:
    path = tmp_path / "selected-device.json"
    save_selected(selected_from_hit(LEDNET), path=path)
    clear_selected(path)
    assert load_selected(path) is None
    clear_selected(path)


def test_load_missing_is_none(tmp_path: Path) -> None:
    assert load_selected(tmp_path / "missing.json") is None


def test_resolve_address_prefers_cli(tmp_path: Path) -> None:
    path = tmp_path / "selected-device.json"
    save_selected(selected_from_hit(LEDNET), path=path)
    assert resolve_address(cli_address="11:22:33:44:55:66", path=path) == "11:22:33:44:55:66"
    assert resolve_address(path=path) == "E4:98:BB:6B:1A:AC"


def test_resolve_address_errors_when_empty(tmp_path: Path) -> None:
    with pytest.raises(DeviceNotSelectedError, match="scan"):
        resolve_address(path=tmp_path / "none.json")


def test_select_by_index() -> None:
    assert select_hit(HITS, index=2) is OTHER


def test_select_by_name_allows_non_lednetwf() -> None:
    hit = select_hit(HITS, name="Kitchen")
    assert hit.address == "11:22:33:44:55:66"


def test_select_by_address_not_in_scan() -> None:
    hit = select_hit([], address="E4:98:BB:6B:1A:AC")
    assert hit.address == "E4:98:BB:6B:1A:AC"
    assert hit.name == ""


def test_select_name_ambiguous() -> None:
    dup = [
        DeviceHit("Same", "11:11:11:11:11:11", None, False),
        DeviceHit("Same", "22:22:22:22:22:22", None, False),
    ]
    with pytest.raises(SelectionError, match="несколькими"):
        select_hit(dup, name="Same")


def test_select_index_out_of_range() -> None:
    with pytest.raises(SelectionError, match="вне диапазона"):
        select_hit(HITS, index=9)


def test_parse_choice_index() -> None:
    assert parse_choice_index("1", 3) == 0
    assert parse_choice_index(" 3 ", 3) == 2
    with pytest.raises(SelectionError, match="ничего не выбрано"):
        parse_choice_index("  ", 3)
    with pytest.raises(SelectionError, match="вне диапазона"):
        parse_choice_index("0", 3)


def test_format_scan_line_highlights_prefix() -> None:
    line = format_scan_line(1, LEDNET)
    assert "*" in line
    assert "E4:98:BB:6B:1A:AC" in line
    other = format_scan_line(2, OTHER)
    assert "*" not in other.split()[1]
    unnamed = format_scan_line(3, UNNAMED)
    assert "(без имени)" in unnamed
