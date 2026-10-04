<p align="center"><img src="https://raw.githubusercontent.com/Alexlambertz/hass-ring_plus/main/custom_components/ring_plus/brand/icon%402x.png" width="128" alt="Ring Plus"></p>

# Ring Plus for Home Assistant

A Home Assistant custom integration for **Ring Alarm**, plus Ring cameras, doorbells and chimes.
You choose which device types are imported.

> **Unofficial.** Not affiliated with or endorsed by Ring or Amazon. It uses the same private
> API as the Ring mobile app (the approach used by `ring-client-api` / `ring-mqtt`), which Ring can
> change at any time. Use at your own risk.

## Features

| Area | What you get |
|------|--------------|
| **Alarm panel** | Arm home / arm away / disarm; states disarmed, armed home/away, arming, pending (entry delay), triggered. Attributes: entry/exit delays, siren state, bypassed devices |
| **Alarm sensors** | Contact (door/window), motion, tilt, glass break, smoke/CO, flood/freeze, with tamper and battery |
| **Alarm hardware** | Base station (AC power, battery backup, firmware, Wi-Fi/cellular signal, active network), keypads, sirens, range extenders |
| **Diagnostics** | Connectivity, low battery, AC power, Z-Wave link quality, last communication |
| **Cameras / doorbells** | Snapshot camera, motion and ding sensors, last motion / last ding (with person detection), connectivity, Wi-Fi signal, battery, external power, light state, uptime |
| **Chimes** | Connectivity and Wi-Fi signal |

Alarm data is **pushed** over Ring's websocket (near real-time). Cameras and doorbells are
**polled every 15 seconds**.

Not supported yet: live video, camera settings/lights/sirens as controls, Z-Wave locks/switches/lights,
panic buttons, bypassing open sensors when arming.

## Requirements

- Home Assistant **2025.11** or newer
- A Ring account (2FA supported). For Alarm: a Ring Alarm base station
- [HACS](https://hacs.xyz) for the recommended install

## Installation

### Option A: HACS (recommended)

This repository is not in the default HACS store, so add it as a **custom repository**:

1. In Home Assistant open **HACS**.
2. Open the **⋮** menu (top right) → **Custom repositories**.
3. Repository: `https://github.com/Alexlambertz/hass-ring_plus`, Type/Category: **Integration** → **Add**.
4. Search for **Ring Plus** in HACS, open it and click **Download**. Choose the latest release.
5. **Restart Home Assistant** (Settings → System → Restart).

HACS installs the *release asset* `ring_plus.zip`, which already contains the bundled `aioring`
library. For that reason a **GitHub release must exist**; installing from the bare branch does not work.
Updates then appear in HACS like any other integration.

### Option B: Manual

1. Download `ring_plus.zip` from the [latest release](https://github.com/Alexlambertz/hass-ring_plus/releases/latest).
2. Unzip it into `<config>/custom_components/ring_plus/` (so `manifest.json` sits directly in that folder).
3. Restart Home Assistant.

## Setup

1. **Settings → Devices & services → Add integration → Ring Plus.**
2. Enter your Ring email and password.
3. If Ring asks for it, enter the **2FA code** (sent by SMS/email/authenticator app).
4. Select the **device types** to import and finish.

Change the selection later under **Settings → Devices & services → Ring Plus → Configure**.
The integration reloads and adds or removes entities accordingly.

| Device type | Imports |
|-------------|---------|
| Alarm panel | the alarm control panel |
| Contact sensors | door/window/tilt sensors |
| Motion sensors | Alarm motion detectors |
| Other sensors | glass break, zone, panic |
| Smoke & CO detectors | smoke/CO alarms and listeners |
| Flood & freeze sensors | water and freeze sensors |
| Base station | base-station diagnostics |
| Keypads, sirens & extenders | their diagnostics |
| Cameras / Doorbells / Chimes | cameras, doorbells, chimes with their sensors |

All types are selected by default for new installs. Existing installs do not automatically get
newly added types (for example *Chimes*); enable them under **Configure**.

### Authentication and tokens

Your password is used once to obtain a token and is **not stored**. Home Assistant keeps the
refresh token in the config entry (`.storage/core.config_entries`) and updates it whenever Ring
rotates it, so you normally stay signed in. If Ring rejects the token, Home Assistant shows a
**re-authentication** prompt. Keep your `.storage` folder private and out of public backups.

> Ring's *official* partner API (OAuth client ID/secret, webhooks) is not used yet. It does not
> document Alarm support. See `docs/DEVELOPMENT.md` for the status.

## Entities

Entity names follow the device name from your Ring app. Diagnostic entities are in the device's
*Diagnostic* section; some are disabled by default (uptime, last communication, cellular signal).

- `alarm_control_panel`: one per base station
- `binary_sensor`: opening/motion/smoke/… per sensor, *Tamper*, *Connectivity*, *Low battery*,
  *AC power*, *Siren*, camera *Motion* / *Ding* / *Light* / *External power*
- `sensor`: *Battery*, *Wi-Fi signal*, *Last motion*, *Last ding*, hub *Firmware* / *Power source* / …
- `camera`: snapshot image (not a live stream)

## Troubleshooting

**Integration not listed after install**: restart Home Assistant; check **Settings → System → Logs**
for `custom_components.ring_plus`. A warning that the integration "has not been tested by Home
Assistant" is normal for custom integrations.

**Duplicate or unexpected Ring errors in the log**: Home Assistant's built-in *Ring* integration
can run alongside this one. Messages from `ring_doorbell` (such as `Unknown kind: …`) come from the
built-in one, not from Ring Plus.

**No Alarm entities**: make sure an Alarm device type is selected under *Configure* and that your
account owns or is a full user of a location with a base station.

**Enable debug logging**:

```yaml
logger:
  logs:
    custom_components.ring_plus: debug
```

**Sign-in fails** with valid credentials: Ring may require a fresh 2FA code; try again, then
re-authenticate from the integration page.

## Support and development

- Bugs / ideas: [GitHub issues](https://github.com/Alexlambertz/hass-ring_plus/issues). Please include
  Home Assistant version, log excerpt and **redact** serial numbers, IPs, Wi-Fi names and tokens.
- Contributing, local testing, building and releasing: see [`docs/DEVELOPMENT.md`](https://github.com/Alexlambertz/hass-ring_plus/blob/main/docs/DEVELOPMENT.md).

## License

[MIT](https://github.com/Alexlambertz/hass-ring_plus/blob/main/LICENSE). Not affiliated with Ring or Amazon.
