"""Binary sensors: alarm sensors, tamper, connectivity, camera events and status."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .camera import camera_device_info
from .entity import RingAlarmEntity

# deviceType -> device class for the `faulted` state
FAULT_CLASS = {
    "sensor.contact": BinarySensorDeviceClass.OPENING,
    "sensor.motion": BinarySensorDeviceClass.MOTION,
    "sensor.tilt": BinarySensorDeviceClass.GARAGE_DOOR,
    "sensor.glassbreak": BinarySensorDeviceClass.SAFETY,
    "sensor.zone": BinarySensorDeviceClass.SAFETY,
    "sensor.freeze": BinarySensorDeviceClass.COLD,
    "sensor.water": BinarySensorDeviceClass.MOISTURE,
    "sensor.flood-freeze": BinarySensorDeviceClass.MOISTURE,
    "alarm.smoke": BinarySensorDeviceClass.SMOKE,
    "alarm.co": BinarySensorDeviceClass.CO,
    "listener.smoke-co": BinarySensorDeviceClass.SMOKE,
}


async def async_setup_entry(hass, entry, async_add_entities):
    data = entry.runtime_data
    entities = []
    for conn, dev in data.alarm_devices():
        zid = dev["zid"]
        if dev.get("deviceType") in FAULT_CLASS:
            entities.append(RingFaultSensor(conn, zid))
        if "tamperStatus" in dev:
            entities.append(RingTamperSensor(conn, zid))
        if "commStatus" in dev:
            entities.append(RingAlarmFlag(conn, zid, "comm", "Connectivity", lambda d: d.get("commStatus") == "ok",
                                          BinarySensorDeviceClass.CONNECTIVITY))
        if "acStatus" in dev:
            entities.append(RingAlarmFlag(conn, zid, "ac", "AC power", lambda d: d.get("acStatus") == "ok",
                                          BinarySensorDeviceClass.PLUG))
        if "batteryLevel" in dev:
            entities.append(RingAlarmFlag(conn, zid, "low_battery", "Low battery",
                                          lambda d: d.get("batteryStatus") == "low",
                                          BinarySensorDeviceClass.BATTERY))
        if dev.get("deviceType") == "security-panel":
            entities.append(RingAlarmFlag(conn, zid, "siren", "Siren",
                                          lambda d: (d.get("siren") or {}).get("state") == "on",
                                          BinarySensorDeviceClass.SOUND, diagnostic=False))
    if data.cameras:
        for dev_id, dev in data.cameras.data.items():
            c = data.cameras
            entities.append(RingCameraFlag(c, dev_id, "online", "Connectivity", BinarySensorDeviceClass.CONNECTIVITY))
            if dev["category"] != "chimes":
                entities.append(RingCameraEvent(c, dev_id, "motion"))
            if dev["category"] == "doorbells":
                entities.append(RingCameraEvent(c, dev_id, "ding"))
            if dev.get("external_power") is not None and dev["category"] != "chimes":
                entities.append(RingCameraFlag(c, dev_id, "external_power", "External power",
                                               BinarySensorDeviceClass.PLUG))
            if dev.get("light") is not None:
                entities.append(RingCameraFlag(c, dev_id, "light", "Light", BinarySensorDeviceClass.LIGHT,
                                               diagnostic=False))
    async_add_entities(entities)


class RingFaultSensor(RingAlarmEntity, BinarySensorEntity):
    _attr_name = None

    def __init__(self, conn, zid):
        super().__init__(conn, zid)
        self._attr_device_class = FAULT_CLASS[self.device["deviceType"]]
        if self.device["deviceType"] == "sensor.contact" and self.device.get("subCategoryId") == 2:
            self._attr_device_class = BinarySensorDeviceClass.WINDOW

    @property
    def is_on(self):
        return bool(self.device.get("faulted"))


class RingTamperSensor(RingAlarmEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.TAMPER
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Tamper"

    def __init__(self, conn, zid):
        super().__init__(conn, zid, "tamper")

    @property
    def is_on(self):
        return self.device.get("tamperStatus") == "tamper"


class RingAlarmFlag(RingAlarmEntity, BinarySensorEntity):
    """Generic boolean derived from a device document."""

    def __init__(self, conn, zid, key, name, fn, device_class, diagnostic=True):
        super().__init__(conn, zid, key)
        self._fn = fn
        self._attr_name = name
        self._attr_device_class = device_class
        if diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self):
        return bool(self._fn(self.device))


class RingCameraEvent(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, dev_id, kind):
        super().__init__(coordinator)
        self._dev_id = dev_id
        self._kind = kind
        self._attr_unique_id = f"{dev_id}_{kind}"
        self._attr_name = "Motion" if kind == "motion" else "Ding"
        self._attr_device_class = (BinarySensorDeviceClass.MOTION if kind == "motion"
                                   else BinarySensorDeviceClass.OCCUPANCY)
        self._attr_device_info = camera_device_info(coordinator.data[dev_id])

    @property
    def is_on(self):
        return bool((self.coordinator.data.get(self._dev_id) or {}).get(self._kind))


class RingCameraFlag(CoordinatorEntity, BinarySensorEntity):
    """Boolean field from the coordinator's per-device dict."""
    _attr_has_entity_name = True

    def __init__(self, coordinator, dev_id, key, name, device_class, diagnostic=True):
        super().__init__(coordinator)
        self._dev_id = dev_id
        self._key = key
        self._attr_unique_id = f"{dev_id}_{key}"
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_device_info = camera_device_info(coordinator.data[dev_id])
        if diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self):
        value = (self.coordinator.data.get(self._dev_id) or {}).get(self._key)
        return None if value is None else bool(value)
