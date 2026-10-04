"""Camera / doorbell snapshot entities."""
from __future__ import annotations

from homeassistant.components.camera import Camera
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


def camera_device_info(dev: dict) -> DeviceInfo:
    return DeviceInfo(identifiers={(DOMAIN, str(dev["id"]))}, name=dev.get("description"),
                      manufacturer="Ring", model=dev.get("kind"),
                      sw_version=dev.get("firmware") or dev.get("firmware_version"))


async def async_setup_entry(hass, entry, async_add_entities):
    cams = entry.runtime_data.cameras
    if cams:
        async_add_entities(RingCamera(cams, entry.runtime_data.api, i) for i, d in cams.data.items()
                           if d["category"] in ("cameras", "doorbells"))


class RingCamera(CoordinatorEntity, Camera):
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator, api, dev_id):
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self._api = api
        self._dev_id = dev_id
        self._attr_unique_id = f"{dev_id}_camera"
        self._attr_device_info = camera_device_info(coordinator.data[dev_id])

    async def async_camera_image(self, width=None, height=None):
        try:
            return await self._api.get_snapshot(self._dev_id)
        except Exception:  # noqa: BLE001
            return None
