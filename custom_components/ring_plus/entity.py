"""Base entities."""
from __future__ import annotations

from typing import Any

from aioring import RingAlarmConnection
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN


class RingAlarmEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, conn: RingAlarmConnection, zid: str, suffix: str | None = None) -> None:
        self._conn = conn
        self._zid = zid
        self._attr_unique_id = f"{conn.location_id}_{zid}" + (f"_{suffix}" if suffix else "")
        dev = self.device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{conn.location_id}_{zid}")},
            name=dev.get("name") or zid, manufacturer="Ring",
            model=dev.get("deviceType"), serial_number=dev.get("serialNumber"))

    @property
    def device(self) -> dict[str, Any]:
        return self._conn.devices.get(self._zid, {})

    @property
    def available(self) -> bool:
        return self._conn.connected and bool(self.device)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._conn.add_listener(self.schedule_update_ha_state))
