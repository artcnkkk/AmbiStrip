"""Human-readable GATT dump shared by CLI, terminal menu, and the desktop window."""

from __future__ import annotations

from ledsetup.ble import NOTIFY_UUID, SERVICE_UUID, WRITE_UUID, GattSnapshot, uuids_equal


def format_gatt_lines(snapshot: GattSnapshot, *, include_expected: bool = False) -> list[str]:
    lines = [f"GATT {snapshot.address} (UUID FFFF/FF01/FF02 сверены на этом ките):"]
    for svc_uuid, chars in snapshot.services:
        mark = "  << service FFFF" if uuids_equal(svc_uuid, SERVICE_UUID) else ""
        lines.append(f"  service {svc_uuid}{mark}")
        for char in chars:
            extra = ""
            if uuids_equal(char.uuid, WRITE_UUID):
                extra = "  << write FF01"
            elif uuids_equal(char.uuid, NOTIFY_UUID):
                extra = "  << notify FF02"
            props = ",".join(char.properties) or "-"
            handle = f" handle={char.handle}" if char.handle is not None else ""
            lines.append(f"    char {char.uuid} props={props}{handle}{extra}")
    lines.append(
        "совпадение UUID: "
        f"service={'да' if snapshot.service_matched else 'нет'}, "
        f"write={'да' if snapshot.write_matched else 'нет'}, "
        f"notify={'да' if snapshot.notify_matched else 'нет'}"
    )
    if include_expected:
        lines.append(f"ожидаемые: service {SERVICE_UUID}; write {WRITE_UUID}; notify {NOTIFY_UUID}")
    return lines
