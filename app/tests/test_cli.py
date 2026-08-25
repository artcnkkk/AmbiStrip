"""CLI argument parsing and scan select — no BLE adapter."""

import argparse
import asyncio
from pathlib import Path

import pytest

from ledsetup.ble import DeviceHit
from ledsetup.cli import _cmd_scan, build_parser, rgb_byte
from ledsetup.device import load_selected


def test_rgb_byte_accepts_edges() -> None:
    assert rgb_byte("0") == 0
    assert rgb_byte("255") == 255


def test_rgb_byte_rejects_range() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        rgb_byte("256")
    with pytest.raises(argparse.ArgumentTypeError):
        rgb_byte("-1")
    with pytest.raises(argparse.ArgumentTypeError):
        rgb_byte("red")


def test_scan_default_timeout() -> None:
    args = build_parser().parse_args(["scan"])
    assert args.command == "scan"
    assert args.timeout == 10.0
    assert args.index is None
    assert args.address is None
    assert args.name is None


def test_scan_select_flags() -> None:
    parser = build_parser()
    by_index = parser.parse_args(["scan", "--index", "2"])
    assert by_index.index == 2
    by_addr = parser.parse_args(["scan", "--address", "e4:98:bb:6b:1a:ac"])
    assert by_addr.address == "E4:98:BB:6B:1A:AC"
    by_name = parser.parse_args(["scan", "--name", "Kitchen"])
    assert by_name.name == "Kitchen"


def test_scan_select_flags_mutually_exclusive(capsys: pytest.CaptureFixture[str]) -> None:
    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["scan", "--index", "1", "--name", "x"])
    assert exc.value.code == 2
    err = capsys.readouterr().err.lower()
    assert "not allowed" in err or "exclusive" in err or "не допускается" in err


def test_gatt_requires_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("LEDSETUP_DEVICE_FILE", str(tmp_path / "none.json"))
    from ledsetup.cli import main

    code = main(["gatt"])
    assert code == 1
    out = capsys.readouterr().out
    assert "scan" in out
    assert "--address" in out


def test_gatt_accepts_address() -> None:
    args = build_parser().parse_args(["gatt", "--address", "11:22:33:44:55:66"])
    assert args.command == "gatt"
    assert args.address == "11:22:33:44:55:66"


def test_color_requires_three_channels() -> None:
    parser = build_parser()
    args = parser.parse_args(["color", "255", "0", "0"])
    assert args.command == "color"
    assert (args.r, args.g, args.b) == (255, 0, 0)
    assert args.hsv is False
    assert args.address is None


def test_color_hsv_flag() -> None:
    args = build_parser().parse_args(["color", "0", "255", "0", "--hsv"])
    assert args.hsv is True


def test_color_rejects_256(capsys: pytest.CaptureFixture[str]) -> None:
    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["color", "256", "0", "0"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "0–255" in err or "0-255" in err


def test_color_rejects_missing_channel(capsys: pytest.CaptureFixture[str]) -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["color", "1", "2"])
    err = capsys.readouterr().err.lower()
    assert "r" in err or "required" in err or "arguments" in err


def test_subcommands_exist() -> None:
    parser = build_parser()
    for name in ("scan", "gatt", "on", "off", "gui", "menu"):
        args = parser.parse_args([name])
        assert args.command == name


def _hits() -> list[DeviceHit]:
    return [
        DeviceHit("LEDnetWFRenamed", "E4:98:BB:6B:1A:AC", -56, True),
        DeviceHit("Kitchen", "11:22:33:44:55:66", -70, False),
    ]


def test_scan_index_persists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_scan(timeout: float = 10.0) -> list[DeviceHit]:
        return _hits()

    monkeypatch.setattr("ledsetup.cli.scan_devices", fake_scan)
    store = tmp_path / "selected-device.json"
    code = asyncio.run(_cmd_scan(1.0, index=2, store_path=store))
    assert code == 0
    selected = load_selected(store)
    assert selected is not None
    assert selected.address == "11:22:33:44:55:66"
    assert selected.name == "Kitchen"


def test_scan_interactive_number(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_scan(timeout: float = 10.0) -> list[DeviceHit]:
        return _hits()

    monkeypatch.setattr("ledsetup.cli.scan_devices", fake_scan)
    store = tmp_path / "selected-device.json"
    code = asyncio.run(_cmd_scan(1.0, store_path=store, input_fn=lambda _: "1", stdin_isatty=True))
    assert code == 0
    selected = load_selected(store)
    assert selected is not None
    assert selected.address == "E4:98:BB:6B:1A:AC"


def test_scan_non_tty_requires_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_scan(timeout: float = 10.0) -> list[DeviceHit]:
        return _hits()

    monkeypatch.setattr("ledsetup.cli.scan_devices", fake_scan)
    store = tmp_path / "selected-device.json"
    code = asyncio.run(_cmd_scan(1.0, store_path=store, stdin_isatty=False))
    assert code == 1
    assert load_selected(store) is None


def test_scan_address_without_hits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_scan(timeout: float = 10.0) -> list[DeviceHit]:
        return []

    monkeypatch.setattr("ledsetup.cli.scan_devices", fake_scan)
    store = tmp_path / "selected-device.json"
    code = asyncio.run(_cmd_scan(1.0, address="E4:98:BB:6B:1A:AC", store_path=store))
    assert code == 0
    selected = load_selected(store)
    assert selected is not None
    assert selected.address == "E4:98:BB:6B:1A:AC"
