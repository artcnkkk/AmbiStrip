"""Held BLE session — mock client, no adapter."""

import asyncio

from fake_ble import FakeOpener
from ledsetup.protocol import build_rgb_frame
from ledsetup.session import BleSession, NotConnectedError


def test_two_writes_one_connect() -> None:
    opener = FakeOpener()
    session = BleSession(opener=opener.open, closer=opener.close)

    async def _run() -> None:
        await session.connect("e4:98:bb:6b:1a:ac")
        await session.write(build_rgb_frame(255, 0, 0))
        await session.write(build_rgb_frame(0, 255, 0))
        await session.disconnect()

    asyncio.run(_run())
    assert opener.open_calls == 1
    assert session.connect_calls == 1
    assert opener.client.write_calls == 2
    assert opener.client.connect_calls == 1
    red, green = opener.client.written
    assert red[8] == 0x31
    assert red[9:12] == bytes([255, 0, 0])
    assert green[9:12] == bytes([0, 255, 0])
    assert 0xA1 not in red


def test_second_connect_same_address_reuses_client() -> None:
    opener = FakeOpener()
    session = BleSession(opener=opener.open, closer=opener.close)

    async def _run() -> None:
        await session.connect("E4:98:BB:6B:1A:AC")
        await session.connect("E4:98:BB:6B:1A:AC")
        await session.disconnect()

    asyncio.run(_run())
    assert opener.open_calls == 1
    assert session.connect_calls == 1


def test_write_without_connect_raises() -> None:
    opener = FakeOpener()
    session = BleSession(opener=opener.open, closer=opener.close)

    async def _run() -> None:
        try:
            await session.write(build_rgb_frame(1, 2, 3))
        except NotConnectedError:
            return
        raise AssertionError("expected NotConnectedError")

    asyncio.run(_run())
    assert opener.open_calls == 0
