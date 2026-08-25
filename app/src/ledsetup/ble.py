"""BLE scan / GATT / write for one analog RGB LEDnetWF peripheral by address.

Advertised name is not a stable ID. GATT FFFF/FF01/FF02 were verified on this kit.
Write is never sent to an arbitrary first characteristic.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, cast

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

from ledsetup import has_lednetwf_prefix
from ledsetup.exceptions import (
    BluetoothUnavailableError,
    DeviceNotFoundError,
    WriteTargetError,
)
from ledsetup.types import BleClient, DisconnectFn, LogFn


def as_ble_client(client: object) -> BleClient:
    """BleakClient stubs do not structurally match BleClient; tests' FakeClient does."""
    return cast(BleClient, client)


# Verified by GATT enumeration on this analog kit (2026-08-25).
SERVICE_UUID = "0000ffff-0000-1000-8000-00805f9b34fb"
WRITE_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000ff02-0000-1000-8000-00805f9b34fb"

WRITE_PROPS = frozenset({"write", "write-without-response"})
DEFAULT_SCAN_TIMEOUT = 10.0

__all__ = [
    "DEFAULT_SCAN_TIMEOUT",
    "NOTIFY_UUID",
    "SERVICE_UUID",
    "WRITE_UUID",
    "BluetoothUnavailableError",
    "CharInfo",
    "DeviceHit",
    "DeviceNotFoundError",
    "GattSnapshot",
    "LogFn",
    "WriteResult",
    "WriteTargetError",
    "close_bleak_client",
    "enable_kit_notify",
    "enumerate_gatt",
    "normalize_uuid",
    "open_bleak_client",
    "scan_devices",
    "select_write_characteristic",
    "snapshot_from_client",
    "uuids_equal",
    "write_on_client",
    "write_payload",
]


@dataclass(frozen=True)
class DeviceHit:
    name: str
    address: str
    rssi: int | None
    lednetwf: bool = False


@dataclass(frozen=True)
class CharInfo:
    uuid: str
    properties: tuple[str, ...]
    handle: int | None = None
    service_uuid: str = ""


@dataclass
class GattSnapshot:
    address: str
    services: list[tuple[str, list[CharInfo]]] = field(default_factory=list)
    service_matched: bool = False
    write_matched: bool = False
    notify_matched: bool = False

    @property
    def all_chars(self) -> list[CharInfo]:
        chars: list[CharInfo] = []
        for _svc, items in self.services:
            chars.extend(items)
        return chars

    @property
    def writable(self) -> list[CharInfo]:
        return [c for c in self.all_chars if WRITE_PROPS.intersection(c.properties)]


@dataclass
class WriteResult:
    address: str
    write_uuid: str
    write_method: str
    write_matched: bool
    notify_enabled: bool
    payload_hex: str
    snapshot: GattSnapshot


def normalize_uuid(value: str) -> str:
    raw = value.lower().replace("-", "")
    if len(raw) == 4:
        raw = f"0000{raw}00001000800000805f9b34fb"
    if len(raw) != 32:
        return value.lower()
    return f"{raw[0:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:32]}"


def uuids_equal(left: str, right: str) -> bool:
    return normalize_uuid(left) == normalize_uuid(right)


def select_write_characteristic(writable: Sequence[CharInfo]) -> CharInfo:
    """Pick a write target without guessing the first of many unknowns.

    Prefer the kit write UUID. If it is absent, use the only
    characteristic that has write / write-without-response. Multiple
    unmatched writable characteristics → refuse.
    """
    if not writable:
        raise WriteTargetError(
            "нет characteristic с write / write-without-response; write не отправлен"
        )
    matched = [c for c in writable if uuids_equal(c.uuid, WRITE_UUID)]
    if matched:
        return matched[0]
    if len(writable) == 1:
        return writable[0]
    listed = ", ".join(f"{c.uuid} ({'/'.join(c.properties)})" for c in writable)
    raise WriteTargetError(
        "UUID write FF01 не совпал, и writable characteristics несколько "
        f"({listed}). Write не уходит в первый попавшийся. "
        "Зафиксируйте фактический UUID после `gatt`."
    )


def snapshot_from_client(client: BleClient) -> GattSnapshot:
    services: list[tuple[str, list[CharInfo]]] = []
    service_hit = False
    write_hit = False
    notify_hit = False
    for service in client.services:
        svc_uuid = str(service.uuid)
        if uuids_equal(svc_uuid, SERVICE_UUID):
            service_hit = True
        chars: list[CharInfo] = []
        for char in service.characteristics:
            handle_raw = getattr(char, "handle", None)
            handle = handle_raw if isinstance(handle_raw, int) else None
            info = CharInfo(
                uuid=str(char.uuid),
                properties=tuple(char.properties),
                handle=handle,
                service_uuid=svc_uuid,
            )
            chars.append(info)
            if uuids_equal(info.uuid, WRITE_UUID):
                write_hit = True
            if uuids_equal(info.uuid, NOTIFY_UUID):
                notify_hit = True
        services.append((svc_uuid, chars))
    return GattSnapshot(
        address=client.address,
        services=services,
        service_matched=service_hit,
        write_matched=write_hit,
        notify_matched=notify_hit,
    )


def _device_name(device_name: str | None, local_name: str | None) -> str:
    return (device_name or local_name or "").strip()


def _scan_sort_key(hit: DeviceHit) -> tuple[bool, bool, str, str]:
    unnamed = not hit.name
    return (not hit.lednetwf, unnamed, hit.name.casefold(), hit.address.upper())


async def scan_devices(timeout: float = DEFAULT_SCAN_TIMEOUT) -> list[DeviceHit]:
    """Discover nearby BLE advertisements. LEDnetWF* is a highlight hint, not a filter."""
    try:
        found = await BleakScanner.discover(timeout=timeout, return_adv=True)
    except BleakError as exc:
        raise BluetoothUnavailableError(
            f"Bluetooth недоступен (адаптер выключен или backend Bleak не стартовал): {exc}"
        ) from exc
    except OSError as exc:
        raise BluetoothUnavailableError(f"Bluetooth недоступен: {exc}") from exc

    hits: list[DeviceHit] = []
    for address, (device, adv) in found.items():
        local_name_raw = getattr(adv, "local_name", None)
        local_name = local_name_raw if isinstance(local_name_raw, str) else None
        name = _device_name(device.name, local_name)
        rssi_raw = getattr(adv, "rssi", None)
        if rssi_raw is None:
            rssi_raw = getattr(device, "rssi", None)
        rssi = rssi_raw if isinstance(rssi_raw, int) else None
        hits.append(
            DeviceHit(
                name=name,
                address=address,
                rssi=rssi,
                lednetwf=has_lednetwf_prefix(name),
            )
        )
    hits.sort(key=_scan_sort_key)
    return hits


def _bleak_char_for(client: BleClient, info: CharInfo) -> object:
    char = client.services.get_characteristic(info.uuid)
    if char is None:
        raise WriteTargetError(f"characteristic {info.uuid} пропал после enumeration")
    return char


CONNECT_FAIL_HINT = "Закройте ZENGGE, если оно держит линк. PIN/bonding — TBD."


async def open_bleak_client(
    address: str,
    timeout: float = 30.0,
    on_disconnect: DisconnectFn | None = None,
) -> BleClient:
    """Connect and return a live client. Caller must disconnect."""
    if on_disconnect is None:
        client = BleakClient(address, timeout=timeout)
    else:
        # Bleak types the callback as BleakClient; we only need a disconnect signal.
        client = BleakClient(
            address,
            timeout=timeout,
            disconnected_callback=cast(Any, on_disconnect),
        )
    try:
        await client.connect()
    except (BleakError, OSError, TimeoutError) as exc:
        raise BluetoothUnavailableError(
            f"не удалось подключиться к {address}: {exc}. {CONNECT_FAIL_HINT}"
        ) from exc
    if not client.is_connected:
        raise BluetoothUnavailableError(f"не удалось подключиться к {address}. {CONNECT_FAIL_HINT}")
    return as_ble_client(client)


async def close_bleak_client(client: BleClient | None) -> None:
    if client is None:
        return
    try:
        if client.is_connected:
            await client.disconnect()
    except (BleakError, OSError):
        return


async def enumerate_gatt(address: str, timeout: float = 30.0) -> GattSnapshot:
    try:
        async with BleakClient(address, timeout=timeout) as client:
            return snapshot_from_client(as_ble_client(client))
    except BleakError as exc:
        raise BluetoothUnavailableError(
            f"не удалось подключиться к {address}: {exc}. {CONNECT_FAIL_HINT}"
        ) from exc


def _discard_log(_msg: str) -> None:
    return


async def enable_kit_notify(
    client: BleClient,
    snapshot: GattSnapshot,
    log: LogFn,
) -> bool:
    """Enable CCCD only on the verified notify UUID, if it exists."""
    if not snapshot.notify_matched:
        log(
            "notify UUID FF02 не найден — CCCD не включаем "
            "(чужие notify characteristics не трогаем)"
        )
        return False

    async def _on_notify(_sender: object, data: bytearray) -> None:
        hex_data = " ".join(f"{b:02X}" for b in data)
        log(f"notify (FF02): {hex_data}")

    try:
        await client.start_notify(NOTIFY_UUID, _on_notify)
    except BleakError as exc:
        log(f"не удалось включить notify/CCCD на FF02: {exc}; пишем без него")
        return False
    log("CCCD включён на FF02 (обязателен ли для write — TBD)")
    return True


async def write_on_client(
    client: BleClient,
    payload: bytes,
    log: LogFn,
    *,
    notify_enabled: bool | None = None,
    settle: float = 0.4,
) -> WriteResult:
    """Enumerate GATT on an already connected client, then write safely."""
    snapshot = snapshot_from_client(client)
    try:
        chosen = select_write_characteristic(snapshot.writable)
    except WriteTargetError as exc:
        raise WriteTargetError(str(exc), snapshot=snapshot) from exc
    log(
        f"write target: {chosen.uuid} props={','.join(chosen.properties)} "
        f"(FF01 {'совпал' if uuids_equal(chosen.uuid, WRITE_UUID) else 'не совпал'})"
    )
    if notify_enabled is None:
        notify_on = await enable_kit_notify(client, snapshot, log)
    else:
        notify_on = notify_enabled
    char = _bleak_char_for(client, chosen)
    props = set(getattr(char, "properties", ()))
    try:
        # FF01 has both. Write-with-response at sync rate (~10 Hz) makes WinRT
        # mark handle 0x0016 Unreachable after a while; command writes last.
        if "write-without-response" in props:
            method = "write-without-response"
            await client.write_gatt_char(char, payload, response=False)
        elif "write" in props:
            method = "write"
            await client.write_gatt_char(char, payload, response=True)
        else:
            raise WriteTargetError(
                f"{chosen.uuid} не имеет write / write-without-response",
                snapshot=snapshot,
            )
    except BleakError as exc:
        raise BluetoothUnavailableError(f"ошибка BLE при write на {client.address}: {exc}") from exc
    if settle > 0:
        await asyncio.sleep(settle)
    return WriteResult(
        address=client.address,
        write_uuid=str(getattr(char, "uuid", chosen.uuid)),
        write_method=method,
        write_matched=uuids_equal(str(getattr(char, "uuid", chosen.uuid)), WRITE_UUID),
        notify_enabled=notify_on,
        payload_hex=" ".join(f"{b:02X}" for b in payload),
        snapshot=snapshot,
    )


async def write_payload(
    payload: bytes,
    address: str,
    timeout: float = 30.0,
    log: LogFn | None = None,
) -> WriteResult:
    """Enumerate GATT first, then write only to a safely selected characteristic."""
    sink = log if log is not None else _discard_log
    try:
        async with BleakClient(address, timeout=timeout) as client:
            return await write_on_client(as_ble_client(client), payload, sink)
    except WriteTargetError:
        raise
    except BleakError as exc:
        raise BluetoothUnavailableError(f"ошибка BLE при write на {address}: {exc}") from exc
