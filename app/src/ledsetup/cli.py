"""CLI: desktop window, or menu / one-shot scan / gatt / on / off / color."""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from ledsetup import NAME_PREFIX_HINT, __version__
from ledsetup.ble import (
    DEFAULT_SCAN_TIMEOUT,
    BluetoothUnavailableError,
    DeviceHit,
    DeviceNotFoundError,
    GattSnapshot,
    WriteTargetError,
    enumerate_gatt,
    scan_devices,
    write_payload,
)
from ledsetup.capture import ScreenGrabber, grab_average, list_monitors, resolve_monitor
from ledsetup.color import parse_rgb_channel
from ledsetup.device import (
    DeviceNotSelectedError,
    SelectionError,
    format_scan_line,
    normalize_address,
    parse_choice_index,
    resolve_address,
    save_selected,
    select_hit,
    selected_from_hit,
)
from ledsetup.exceptions import LedSetupError
from ledsetup.gatt_text import format_gatt_lines
from ledsetup.protocol import (
    DEFAULT_COLOR_KIND,
    HYPOTHESIS_NOTE,
    RGB_OFF_NOTE,
    ColorFrameKind,
    build_color_frame,
    build_off_frame,
    build_on_frame,
    build_rgb_frame,
    frame_to_hex,
)
from ledsetup.session import BleSession
from ledsetup.settings import load_settings
from ledsetup.sync_loop import run_screen_sync
from ledsetup.throttle import ColorThrottle
from ledsetup.types import RGB, InputFn

CONNECT_TIMEOUT = 30.0


def rgb_byte(value: str) -> int:
    try:
        return parse_rgb_channel(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def ble_address(value: str) -> str:
    try:
        return normalize_address(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _add_timeout(parser: argparse.ArgumentParser, default: float, help_text: str) -> None:
    parser.add_argument("--timeout", type=float, default=default, help=help_text)


def _add_address_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--address",
        type=ble_address,
        help="BLE-адрес (стабильный ID). Иначе берётся устройство, выбранное в scan",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ledsetup",
        description=(
            "Управление одной аналоговой RGB-лентой по BLE. "
            "Без подкоманды — окно. "
            "Имя в рекламе нестабильно — цель задаётся адресом (scan или --address). "
            "Вся полоса — один цвет. "
            "sync — средний цвет выбранного монитора (не периметр)."
        ),
    )
    parser.add_argument("--version", action="version", version=f"ledsetup {__version__}")
    sub = parser.add_subparsers(dest="command", required=False)

    sub.add_parser("gui", help="окно управления (то же, что без подкоманды)")
    sub.add_parser("menu", help="терминальное меню")

    scan_p = sub.add_parser(
        "scan",
        help="список BLE-устройств рядом и выбор цели (адрес сохраняется)",
    )
    _add_timeout(
        scan_p,
        DEFAULT_SCAN_TIMEOUT,
        f"секунды сканирования (по умолчанию {DEFAULT_SCAN_TIMEOUT:g})",
    )
    select = scan_p.add_mutually_exclusive_group()
    select.add_argument(
        "--index",
        type=int,
        metavar="N",
        help="выбрать N-ю строку списка (с 1), без интерактивного промпта",
    )
    select.add_argument(
        "--address",
        type=ble_address,
        help="сохранить этот адрес (даже если в этом scan его не было)",
    )
    select.add_argument(
        "--name",
        help="выбрать по текущему рекламируемому имени из этого scan",
    )

    gatt_p = sub.add_parser("gatt", help="подключиться и перечислить GATT")
    _add_timeout(gatt_p, CONNECT_TIMEOUT, f"таймаут connect (по умолчанию {CONNECT_TIMEOUT:g})")
    _add_address_flag(gatt_p)

    on_p = sub.add_parser("on", help="кадр питания on (гипотеза, на ките не проверяли)")
    _add_timeout(on_p, CONNECT_TIMEOUT, f"таймаут connect (по умолчанию {CONNECT_TIMEOUT:g})")
    _add_address_flag(on_p)

    off_p = sub.add_parser("off", help="кадр питания off (визуально подтверждён)")
    _add_timeout(off_p, CONNECT_TIMEOUT, f"таймаут connect (по умолчанию {CONNECT_TIMEOUT:g})")
    _add_address_flag(off_p)

    color_p = sub.add_parser(
        "color",
        help="сплошной RGB всей ленты (0B 31 подтверждён; --hsv — гипотеза 0B 3B A1)",
    )
    color_p.add_argument("r", type=rgb_byte, help="красный 0–255")
    color_p.add_argument("g", type=rgb_byte, help="зелёный 0–255")
    color_p.add_argument("b", type=rgb_byte, help="синий 0–255")
    color_p.add_argument(
        "--hsv",
        action="store_true",
        help="слать HSV-кадр 0B 3B A1 вместо RGB 0B 31 (HSV — гипотеза)",
    )
    _add_timeout(color_p, CONNECT_TIMEOUT, f"таймаут connect (по умолчанию {CONNECT_TIMEOUT:g})")
    _add_address_flag(color_p)

    sync_p = sub.add_parser(
        "sync",
        help="средний цвет выбранного монитора → вся лента (пока Ctrl+C или --seconds)",
    )
    sync_p.add_argument(
        "--seconds",
        type=_positive_seconds,
        default=None,
        metavar="N",
        help="остановиться через N секунд (иначе только Ctrl+C)",
    )
    sync_p.add_argument(
        "--monitor",
        default=None,
        help="номер монитора с 1 или id (left,top,WxH). Иначе сохранённый / основной",
    )
    _add_timeout(sync_p, CONNECT_TIMEOUT, f"таймаут connect (по умолчанию {CONNECT_TIMEOUT:g})")
    _add_address_flag(sync_p)
    return parser


def _positive_seconds(value: str) -> float:
    try:
        number = float(value.replace(",", "."))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("ожидалось число секунд") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("--seconds должен быть > 0")
    return number


def _print(msg: str) -> None:
    print(msg)


def _print_gatt(snapshot: GattSnapshot) -> None:
    for line in format_gatt_lines(snapshot, include_expected=True):
        _print(line)


def _print_scan_hits(hits: Sequence[DeviceHit]) -> None:
    _print(f"* — префикс {NAME_PREFIX_HINT} (подсказка; имя не ID, цель — адрес)")
    for i, hit in enumerate(hits, start=1):
        _print(format_scan_line(i, hit))


async def _cmd_scan(
    timeout: float,
    *,
    index: int | None = None,
    address: str | None = None,
    name: str | None = None,
    store_path: Path | None = None,
    input_fn: InputFn | None = None,
    stdin_isatty: bool | None = None,
) -> int:
    hits = await scan_devices(timeout=timeout)
    if hits:
        _print_scan_hits(hits)
    else:
        _print(f"поблизости нет BLE-рекламы (таймаут {timeout:g} с). Bluetooth включён?")

    has_flag = index is not None or address is not None or name is not None
    if has_flag:
        try:
            hit = select_hit(hits, index=index, address=address, name=name)
        except (SelectionError, ValueError) as exc:
            _print(str(exc))
            return 1
        if (
            address is not None
            and not hit.name
            and not any(h.address.upper() == hit.address.upper() for h in hits)
        ):
            _print(f"в этом scan адреса {hit.address} не было — сохраняю как известный ID")
    elif not hits:
        return 1
    else:
        interactive = sys.stdin.isatty() if stdin_isatty is None else stdin_isatty
        if not interactive:
            _print(
                "scan без выбора: передайте --index / --address / --name "
                "или запустите в интерактивном терминале и укажите номер"
            )
            return 1
        prompt = input_fn or input
        try:
            raw = prompt("номер устройства: ")
        except EOFError:
            _print("выбор не получен (EOF). Передайте --index / --address / --name.")
            return 1
        try:
            chosen_i = parse_choice_index(raw, len(hits))
        except SelectionError as exc:
            _print(str(exc))
            return 1
        hit = hits[chosen_i]

    path = save_selected(selected_from_hit(hit), path=store_path)
    label = hit.name or "(нет)"
    _print(f"выбрано: {hit.address}  имя (справочно, не ID): {label}")
    _print(f"сохранено: {path}")
    return 0


async def _cmd_gatt(address: str, timeout: float) -> int:
    snapshot = await enumerate_gatt(address, timeout=timeout)
    _print_gatt(snapshot)
    return 0


def _frame_note(what: str) -> str:
    if what == "on" or (what.startswith("color") and "kind=hsv" in what):
        return HYPOTHESIS_NOTE
    return RGB_OFF_NOTE


async def _cmd_write(payload: bytes, address: str, timeout: float, what: str) -> int:
    _print(f"{what}: {_frame_note(what)}")
    _print(f"кадр ({len(payload)} байт): {frame_to_hex(payload)}")
    result = await write_payload(payload, address=address, timeout=timeout, log=_print)
    _print_gatt(result.snapshot)
    _print(
        f"write {'UUID FF01 совпал' if result.write_matched else 'UUID write не совпал с FF01'} "
        f"→ {result.write_uuid} method={result.write_method} "
        f"notify/CCCD={'да' if result.notify_enabled else 'нет'}"
    )
    _print("проверьте ленту глазами. Результат занесите в docs/protocol-notes.md.")
    return 0


def _color_kind(hsv: bool) -> ColorFrameKind:
    return "hsv" if hsv else DEFAULT_COLOR_KIND


def _target_address(args: argparse.Namespace) -> str:
    address = getattr(args, "address", None)
    return resolve_address(cli_address=address if isinstance(address, str) else None)


async def run_cli_sync(
    address: str,
    timeout: float,
    *,
    seconds: float | None,
    monitor_flag: str | None,
    grabber: ScreenGrabber | None = None,
    session: BleSession | None = None,
    settings_path: Path | None = None,
) -> int:
    settings = load_settings(settings_path)
    monitors = list_monitors(grabber)
    for item in monitors:
        _print(f"{item.index}. {item.label}  id={item.id}")
    monitor, note = resolve_monitor(
        monitors,
        saved_id=settings.monitor_id,
        flag=monitor_flag,
    )
    if note:
        _print(note)
    _print(f"захват: {monitor.label}")
    if seconds is None:
        _print("Ctrl+C — стоп; лента останется на последнем цвете")
    else:
        _print(f"{seconds:g} с или Ctrl+C — стоп; лента останется на последнем цвете")

    held = session or BleSession(timeout=timeout, log=_print)
    held.timeout = timeout
    own_session = session is None
    last: RGB | None = None

    async def send(rgb: RGB) -> None:
        await held.write(build_rgb_frame(*rgb))

    def sample() -> RGB:
        return grab_average(monitor, grabber)

    deadline = None if seconds is None else time.monotonic() + seconds
    try:
        await held.connect(address)
        last = await run_screen_sync(
            sample=sample,
            send=send,
            should_stop=lambda: False,
            throttle=ColorThrottle(),
            deadline=deadline,
        )
    finally:
        if own_session:
            await held.disconnect()
    if last is None:
        _print("sync остановлен")
        return 0
    _print(f"sync остановлен, последний цвет {last[0]} {last[1]} {last[2]}")
    return 0


async def _run(args: argparse.Namespace) -> int:
    if args.command == "scan":
        return await _cmd_scan(
            args.timeout,
            index=args.index,
            address=args.address,
            name=args.name,
        )
    address = _target_address(args)
    if args.command == "gatt":
        return await _cmd_gatt(address, args.timeout)
    if args.command == "on":
        return await _cmd_write(build_on_frame(), address, args.timeout, "on")
    if args.command == "off":
        return await _cmd_write(build_off_frame(), address, args.timeout, "off")
    if args.command == "color":
        kind = _color_kind(args.hsv)
        payload = build_color_frame(args.r, args.g, args.b, kind=kind)
        label = f"color {args.r},{args.g},{args.b} kind={kind}"
        return await _cmd_write(payload, address, args.timeout, label)
    if args.command == "sync":
        return await run_cli_sync(
            address,
            args.timeout,
            seconds=args.seconds,
            monitor_flag=args.monitor,
        )
    _print(f"неизвестная команда: {args.command}")
    return 2


def main(argv: Sequence[str] | None = None, *, stdin_isatty: bool | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command is None or args.command == "gui":
        from ledsetup.gui import run_gui

        return run_gui()
    if args.command == "menu":
        from ledsetup.menu import run_interactive

        return run_interactive(argv_tty=stdin_isatty)
    try:
        return asyncio.run(_run(args))
    except WriteTargetError as exc:
        if exc.snapshot is not None:
            _print_gatt(exc.snapshot)
        _print(str(exc))
        return 2
    except (DeviceNotSelectedError, DeviceNotFoundError, BluetoothUnavailableError) as exc:
        _print(str(exc))
        return 1
    except LedSetupError as exc:
        _print(str(exc))
        return 1
    except KeyboardInterrupt:
        _print("прервано")
        return 130


if __name__ == "__main__":
    sys.exit(main())
