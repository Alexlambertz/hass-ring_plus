"""Device categories shared by the library and the Home Assistant integration."""
from __future__ import annotations

from typing import Any

# category -> Ring Alarm deviceType values
ALARM_CATEGORIES: dict[str, set[str]] = {
    "alarm_panel": {"security-panel"},
    "contact_sensors": {"sensor.contact", "sensor.tilt"},
    "motion_sensors": {"sensor.motion"},
    "other_sensors": {"sensor.glassbreak", "sensor.zone", "security-panic"},
    "smoke_co": {"alarm.smoke", "alarm.co", "listener.smoke-co"},
    "flood_freeze": {"sensor.flood-freeze", "sensor.freeze", "sensor.water"},
    "base_station": {"hub.redsky", "hub.kili"},
    "keypads_sirens": {"security-keypad", "siren", "range-extender.zwave"},
}
CAMERA_CATEGORIES = ("cameras", "doorbells", "chimes")
ALL_CATEGORIES = (*ALARM_CATEGORIES, *CAMERA_CATEGORIES)


def alarm_category(device_type: str | None) -> str | None:
    for category, types in ALARM_CATEGORIES.items():
        if device_type in types:
            return category
    return None


def flatten_doc(doc: dict[str, Any]) -> dict[str, Any]:
    """Flatten a DeviceInfoDocType document (general.v2 + device.v1) into one dict."""
    out: dict[str, Any] = {}
    out.update(doc.get("general", {}).get("v2", {}))
    out.update(doc.get("device", {}).get("v1", {}))
    zid = out.get("zid") or doc.get("zid") or doc.get("general", {}).get("v2", {}).get("zid")
    if zid:
        out["zid"] = zid
    return out
