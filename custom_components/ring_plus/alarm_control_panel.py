"""Ring Alarm panel."""
from __future__ import annotations

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity, AlarmControlPanelEntityFeature, AlarmControlPanelState)

from .entity import RingAlarmEntity

MODE_STATE = {"none": AlarmControlPanelState.DISARMED, "some": AlarmControlPanelState.ARMED_HOME,
              "all": AlarmControlPanelState.ARMED_AWAY}


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        RingAlarmPanel(conn, dev["zid"]) for conn, dev in entry.runtime_data.alarm_devices()
        if dev.get("deviceType") == "security-panel")


class RingAlarmPanel(RingAlarmEntity, AlarmControlPanelEntity):
    _attr_name = None
    _attr_code_arm_required = False
    _attr_supported_features = (AlarmControlPanelEntityFeature.ARM_HOME
                                | AlarmControlPanelEntityFeature.ARM_AWAY)

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        dev = self.device
        alarm = (dev.get("alarmInfo") or {}).get("state") or ""
        if alarm == "entry-delay":
            return AlarmControlPanelState.PENDING
        if alarm.endswith("-alarm") or alarm.startswith("panic"):
            return AlarmControlPanelState.TRIGGERED
        if dev.get("transitionDelayEndTimestamp"):
            return (AlarmControlPanelState.PENDING if dev.get("mode") == "none"
                    else AlarmControlPanelState.ARMING)
        return MODE_STATE.get(dev.get("mode"))

    @property
    def extra_state_attributes(self):
        dev = self.device
        modes = dev.get("modes") or {}
        return {
            "siren": (dev.get("siren") or {}).get("state"),
            "bypassed_devices": len(dev.get("bypasses") or []),
            "entry_delay_home": (modes.get("some") or {}).get("entryDelay"),
            "entry_delay_away": (modes.get("all") or {}).get("entryDelay"),
            "exit_delay_home": (modes.get("some") or {}).get("transitionDelay"),
            "exit_delay_away": (modes.get("all") or {}).get("transitionDelay"),
        }

    async def async_alarm_disarm(self, code=None):
        await self._conn.set_mode(self._zid, "none")

    async def async_alarm_arm_home(self, code=None):
        await self._conn.set_mode(self._zid, "some")

    async def async_alarm_arm_away(self, code=None):
        await self._conn.set_mode(self._zid, "all")
