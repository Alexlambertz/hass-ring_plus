"""Data handling: alarm websocket per location + polled cameras/doorbells."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from aioring import RingAlarmConnection, RingApi, RingError
from aioring.devices import ALARM_CATEGORIES, alarm_category
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CAMERA_POLL_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

CAMERA_KEYS = {  # clients_api key -> category
    "doorbots": "doorbells", "authorized_doorbots": "doorbells",
    "stickup_cams": "cameras", "chimes": "chimes",
}


class RingCameraCoordinator(DataUpdateCoordinator[dict[int, dict[str, Any]]]):
    """Polls devices and active dings. data: id -> {**device, category, motion, ding}."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: RingApi,
                 categories: set[str]) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=f"{DOMAIN} cameras",
                         update_interval=timedelta(seconds=CAMERA_POLL_INTERVAL))
        self.api = api
        self.categories = categories
        self._events: dict[int, dict[str, dict[str, Any]]] = {}

    async def _fetch_events(self) -> dict[int, dict[str, dict[str, Any]]]:
        """Latest motion / ding per device from the shared history feed."""
        try:
            history = await self.api.get_history(50)
        except Exception as err:  # noqa: BLE001 - keep last known events
            _LOGGER.debug("History fetch failed: %s", err)
            return self._events
        events: dict[int, dict[str, dict[str, Any]]] = {}
        for item in history:  # newest first
            kind = item.get("kind")
            if kind not in ("motion", "ding"):
                continue
            at = dt_util.parse_datetime(item.get("created_at") or "")
            dev_id = (item.get("doorbot") or {}).get("id")
            if at is None or dev_id is None or kind in events.get(dev_id, {}):
                continue
            cv = item.get("cv_properties") or {}
            events.setdefault(dev_id, {})[kind] = {
                "at": at, "person": bool(cv.get("person_detected")),
                "detection_type": cv.get("detection_type")}
        self._events = events
        return events

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        try:
            devices = await self.api.get_devices()
            dings = await self.api.get_active_dings()
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(str(err)) from err
        active = {d.get("doorbot_id"): d.get("kind") for d in dings}
        events = await self._fetch_events()
        out: dict[int, dict[str, Any]] = {}
        for key, category in CAMERA_KEYS.items():
            if category is None or category not in self.categories:
                continue
            for dev in devices.get(key, []):
                kind = active.get(dev["id"])
                health = dev.get("health") or {}
                alerts = dev.get("alerts") or {}
                battery = health.get("battery_percentage", dev.get("battery_life"))
                try:
                    battery = int(battery)
                except (TypeError, ValueError):
                    battery = None
                out[dev["id"]] = {**dev, "category": category, "battery": battery,
                                  "online": (alerts.get("connection") == "online"
                                             if "connection" in alerts else health.get("connected")),
                                  "rssi": health.get("rssi"),
                                  "uptime": health.get("uptime_sec"),
                                  "firmware": health.get("firmware_version"),
                                  "external_power": dev.get("external_connection"),
                                  "light": (dev.get("led_status") == "on"
                                            if dev.get("led_status") is not None
                                            else (health.get("floodlight_on") if "floodlight" in dev["kind"] else None)),
                                  "events": events.get(dev["id"], {}),
                                  "motion": kind == "motion", "ding": kind == "ding"}
        return out


@dataclass
class RingData:
    api: RingApi
    categories: set[str]
    alarms: dict[str, RingAlarmConnection] = field(default_factory=dict)
    locations: dict[str, str] = field(default_factory=dict)
    cameras: RingCameraCoordinator | None = None

    def alarm_devices(self) -> list[tuple[RingAlarmConnection, dict[str, Any]]]:
        """All alarm devices whose category was selected."""
        return [(conn, dev) for conn in self.alarms.values() for dev in conn.devices.values()
                if alarm_category(dev.get("deviceType")) in self.categories]

    async def async_shutdown(self) -> None:
        for conn in self.alarms.values():
            await conn.stop()


async def async_setup_data(hass: HomeAssistant, entry: ConfigEntry, api: RingApi,
                           categories: set[str]) -> RingData:
    data = RingData(api, categories)
    if categories & set(ALARM_CATEGORIES):
        for loc in await api.get_locations():
            conn = RingAlarmConnection(async_get_clientsession(hass), api, loc["location_id"])
            try:
                await conn.start()
            except RingError as err:
                _LOGGER.debug("No alarm at %s: %s", loc.get("name"), err)
                continue
            data.alarms[loc["location_id"]] = conn
            data.locations[loc["location_id"]] = loc.get("name", loc["location_id"])
    if categories & {"cameras", "doorbells"}:
        data.cameras = RingCameraCoordinator(hass, entry, api, categories)
        await data.cameras.async_config_entry_first_refresh()
    return data
