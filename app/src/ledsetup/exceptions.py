"""User-visible errors. Catch `LedSetupError` at UI boundaries."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ledsetup.ble import GattSnapshot


class LedSetupError(Exception):
    """Recoverable application error shown to the user."""


class BluetoothUnavailableError(LedSetupError):
    """Adapter down, backend failed, or the link dropped."""


class DeviceNotFoundError(LedSetupError):
    """Scan/connect could not see the requested peripheral."""


class WriteTargetError(LedSetupError):
    """No safe GATT write characteristic; payload was not sent."""

    def __init__(self, message: str, snapshot: GattSnapshot | None = None) -> None:
        super().__init__(message)
        self.snapshot = snapshot


class DeviceNotSelectedError(LedSetupError):
    def __init__(self) -> None:
        super().__init__(
            "устройство не выбрано. Запустите `ledsetup scan` и укажите номер, "
            "либо передайте --address."
        )


class SelectionError(LedSetupError):
    """Invalid scan/menu choice."""


class SettingsError(LedSetupError, ValueError):
    """Invalid timeout or settings payload."""


class NotConnectedError(LedSetupError):
    def __init__(self) -> None:
        super().__init__("нет BLE-соединения. Подключитесь из меню или выберите устройство.")


class CaptureError(LedSetupError):
    """Screen grab failed or no usable monitor."""
