"""Ring Alarm siren: sound or silence the siren through the security panel."""
from __future__ import annotations

from typing import Any

from aioring import RingError
from homeassistant.components.siren import SirenEntity, SirenEntityFeature
from homeassistant.exceptions import HomeAssistantError

from .entity import RingAlarmEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        RingAlarmSiren(conn, dev["zid"]) for conn, dev in entry.runtime_data.alarm_devices()
        if dev.get("deviceType") == "security-panel")


class RingAlarmSiren(RingAlarmEntity, SirenEntity):
    _attr_name = "Siren"
    _attr_supported_features = SirenEntityFeature.TURN_ON | SirenEntityFeature.TURN_OFF

    def __init__(self, conn, zid: str) -> None:
        super().__init__(conn, zid, "siren")

    @property
    def is_on(self) -> bool | None:
        state = (self.device.get("siren") or {}).get("state")
        return None if state is None else state == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        try:
            await self._conn.sound_siren(self._zid)
        except RingError as err:
            raise HomeAssistantError(f"Could not sound Ring siren: {err}") from err

    async def async_turn_off(self, **kwargs: Any) -> None:
        try:
            await self._conn.silence_siren(self._zid)
        except RingError as err:
            raise HomeAssistantError(f"Could not silence Ring siren: {err}") from err
