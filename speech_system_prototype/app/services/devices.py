from __future__ import annotations

from typing import Dict, Optional

from app.domain.models import Device, DeviceType
from app.services.utils import clamp


class DeviceManager:
    def __init__(self, devices: Dict[str, Device]) -> None:
        self.devices = devices

    def list_devices(self) -> list[Device]:
        return list(self.devices.values())

    def get(self, device_id: str) -> Optional[Device]:
        return self.devices.get(device_id)

    def toggle(self, device_id: str, is_on: bool) -> Device:
        d = self._must(device_id)
        d.is_on = bool(is_on)
        return d

    def set_value(self, device_id: str, value: float) -> Device:
        d = self._must(device_id)
        # For demo: clamp temperature-like values
        if d.type in (DeviceType.AC, DeviceType.THERMOSTAT):
            d.value = clamp(float(value), 10.0, 30.0)
        else:
            d.value = float(value)
        return d

    def add_device(self, device: Device) -> Device:
        self.devices[device.id] = device
        return device

    def remove_device(self, device_id: str) -> None:
        if device_id in self.devices:
            del self.devices[device_id]

    def _must(self, device_id: str) -> Device:
        d = self.devices.get(device_id)
        if not d:
            raise KeyError(f"Device not found: {device_id}")
        return d
