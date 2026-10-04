"""Sensors: battery, signal, uptime, last events, hub/network diagnostics."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass)
from homeassistant.const import (
    PERCENTAGE, SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory, UnitOfTime)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .camera import camera_device_info
from .entity import RingAlarmEntity


def _ms_to_dt(ms):
    return dt_util.utc_from_timestamp(ms / 1000) if ms else None


def _net(dev, iface, field):
    return ((dev.get("networks") or {}).get(iface) or {}).get(field)


@dataclass(frozen=True, kw_only=True)
class AlarmSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]
    exists_fn: Callable[[dict[str, Any]], bool]


DIAG = EntityCategory.DIAGNOSTIC
ALARM_SENSORS = (
    AlarmSensorDescription(
        key="last_comm", name="Last communication", device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=DIAG, entity_registry_enabled_default=False,
        value_fn=lambda d: _ms_to_dt(d.get("lastCommTime")),
        exists_fn=lambda d: bool(d.get("lastCommTime"))),
    AlarmSensorDescription(
        key="link_quality", name="Link quality", entity_category=DIAG,
        value_fn=lambda d: d.get("linkQuality"), exists_fn=lambda d: "linkQuality" in d),
    AlarmSensorDescription(
        key="firmware", name="Firmware", entity_category=DIAG,
        value_fn=lambda d: (d.get("version") or {}).get("softwareVersion"),
        exists_fn=lambda d: "softwareVersion" in (d.get("version") or {})),
    AlarmSensorDescription(
        key="power_source", name="Power source", entity_category=DIAG,
        value_fn=lambda d: d.get("powerSource"), exists_fn=lambda d: "powerSource" in d),
    AlarmSensorDescription(
        key="battery_backup", name="Battery backup", entity_category=DIAG,
        value_fn=lambda d: d.get("batteryBackup"), exists_fn=lambda d: "batteryBackup" in d),
    AlarmSensorDescription(
        key="connection", name="Network connection", entity_category=DIAG,
        value_fn=lambda d: d.get("networkConnection"), exists_fn=lambda d: "networkConnection" in d),
    AlarmSensorDescription(
        key="wifi_signal", name="Wi-Fi signal", device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT, entity_category=DIAG,
        value_fn=lambda d: _net(d, "wlan0", "rssi"), exists_fn=lambda d: _net(d, "wlan0", "rssi") is not None),
    AlarmSensorDescription(
        key="cell_signal", name="Cellular signal", device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT, entity_category=DIAG,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _net(d, "ppp0", "rssi"), exists_fn=lambda d: _net(d, "ppp0", "rssi") is not None),
)


async def async_setup_entry(hass, entry, async_add_entities):
    data = entry.runtime_data
    entities: list[SensorEntity] = []
    for conn, dev in data.alarm_devices():
        if "batteryLevel" in dev:
            entities.append(RingAlarmBattery(conn, dev["zid"]))
        entities += [RingAlarmSensor(conn, dev["zid"], desc) for desc in ALARM_SENSORS
                     if desc.exists_fn(dev)]
    if data.cameras:
        c = data.cameras
        for dev_id, dev in c.data.items():
            if dev.get("battery") is not None:
                entities.append(RingCameraBattery(c, dev_id))
            if dev.get("rssi") is not None:
                entities.append(RingCameraValue(
                    c, dev_id, "rssi", "Wi-Fi signal", SensorDeviceClass.SIGNAL_STRENGTH,
                    SIGNAL_STRENGTH_DECIBELS_MILLIWATT, state_class=SensorStateClass.MEASUREMENT))
            if dev.get("uptime") is not None:
                entities.append(RingCameraValue(
                    c, dev_id, "uptime", "Uptime", SensorDeviceClass.DURATION,
                    UnitOfTime.SECONDS, enabled=False))
            if dev["category"] == "doorbells":
                entities.append(RingLastEvent(c, dev_id, "ding", "Last ding"))
            if dev["category"] != "chimes":
                entities.append(RingLastEvent(c, dev_id, "motion", "Last motion"))
    async_add_entities(entities)


class RingAlarmBattery(RingAlarmEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Battery"

    def __init__(self, conn, zid):
        super().__init__(conn, zid, "battery")

    @property
    def native_value(self):
        return self.device.get("batteryLevel")


class RingAlarmSensor(RingAlarmEntity, SensorEntity):
    entity_description: AlarmSensorDescription

    def __init__(self, conn, zid, description: AlarmSensorDescription):
        self.entity_description = description
        super().__init__(conn, zid, description.key)

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.device)


class _CameraBase(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, dev_id, key):
        super().__init__(coordinator)
        self._dev_id = dev_id
        self._attr_unique_id = f"{dev_id}_{key}"
        self._attr_device_info = camera_device_info(coordinator.data[dev_id])

    @property
    def _dev(self) -> dict:
        return self.coordinator.data.get(self._dev_id) or {}


class RingCameraBattery(_CameraBase):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Battery"

    def __init__(self, coordinator, dev_id):
        super().__init__(coordinator, dev_id, "battery")

    @property
    def native_value(self):
        return self._dev.get("battery")


class RingCameraValue(_CameraBase):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, dev_id, key, name, device_class, unit,
                 state_class=None, enabled=True):
        super().__init__(coordinator, dev_id, key)
        self._key = key
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = state_class
        self._attr_entity_registry_enabled_default = enabled

    @property
    def native_value(self):
        return self._dev.get(self._key)


class RingLastEvent(_CameraBase):
    """Timestamp of the latest motion/ding; attributes describe the detection."""
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, dev_id, kind, name):
        super().__init__(coordinator, dev_id, f"last_{kind}")
        self._kind = kind
        self._attr_name = name

    @property
    def _event(self) -> dict:
        return (self._dev.get("events") or {}).get(self._kind) or {}

    @property
    def native_value(self):
        return self._event.get("at")

    @property
    def extra_state_attributes(self):
        if self._kind != "motion" or not self._event:
            return None
        return {"person_detected": self._event.get("person"),
                "detection_type": self._event.get("detection_type")}
