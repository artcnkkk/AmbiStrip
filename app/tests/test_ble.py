"""Write-target selection without a BLE adapter."""

import pytest

from ledsetup.ble import (
    WRITE_UUID,
    CharInfo,
    WriteTargetError,
    normalize_uuid,
    select_write_characteristic,
    uuids_equal,
)


def test_normalize_short_uuid() -> None:
    assert normalize_uuid("FF01") == WRITE_UUID
    assert uuids_equal("ff01", WRITE_UUID)
    assert uuids_equal("0000FF01-0000-1000-8000-00805F9B34FB", WRITE_UUID)


def test_prefers_kit_write_uuid() -> None:
    other = CharInfo("0000aaaa-0000-1000-8000-00805f9b34fb", ("write",))
    kit = CharInfo(WRITE_UUID, ("write-without-response",))
    chosen = select_write_characteristic([other, kit])
    assert chosen.uuid == WRITE_UUID


def test_short_uuid_counts_as_kit_write() -> None:
    chosen = select_write_characteristic([CharInfo("ff01", ("write",))])
    assert uuids_equal(chosen.uuid, WRITE_UUID)


def test_single_unmatched_writable_is_used() -> None:
    only = CharInfo("00001111-0000-1000-8000-00805f9b34fb", ("write",))
    chosen = select_write_characteristic([only])
    assert chosen is only


def test_refuses_first_of_many_unmatched() -> None:
    a = CharInfo("00001111-0000-1000-8000-00805f9b34fb", ("write",))
    b = CharInfo("00002222-0000-1000-8000-00805f9b34fb", ("write-without-response",))
    with pytest.raises(WriteTargetError, match="несколько"):
        select_write_characteristic([a, b])


def test_refuses_when_none_writable() -> None:
    with pytest.raises(WriteTargetError, match="нет characteristic"):
        select_write_characteristic([])


def test_lednetwf_prefix_is_hint_not_lock() -> None:
    from ledsetup import (
        LAST_SEEN_ADDRESS,
        LAST_SEEN_NAME,
        OUTDATED_HYPOTHESIS_NAME,
        has_lednetwf_prefix,
    )

    assert LAST_SEEN_NAME == "LEDnetWF0200086B1AAC"
    assert LAST_SEEN_ADDRESS == "E4:98:BB:6B:1A:AC"
    assert has_lednetwf_prefix("LEDnetWF0200086B1AAC")
    assert has_lednetwf_prefix("LEDnetWFABCDEF")
    assert not has_lednetwf_prefix("Kitchen")
    assert not has_lednetwf_prefix("")
    assert not has_lednetwf_prefix(None)
    assert OUTDATED_HYPOTHESIS_NAME == "LEDnetWF0200006B1AAC"
