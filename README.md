# hass-ring

Home Assistant custom integration `ring_plus` (Ring Alarm first, then cameras/doorbells)
plus the `aioring` async client in `aioring/`.

## Roadmap
1. aioring: auth (done), REST, alarm websocket (ticket -> wss://{host}/ws?authcode=...), device model
2. HA: config flow (user/pass + 2FA, token persistence), coordinator
3. alarm_control_panel, binary_sensor, sensor (battery/tamper), siren
4. camera/doorbell events, snapshots
