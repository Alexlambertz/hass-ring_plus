# Development

## Repository layout

```
aioring/                    async Ring client (own pyproject), importable as `aioring`
custom_components/ring_plus Home Assistant integration (domain: ring_plus)
scripts/                    build.sh, dump_alarm.py, make_icon.py
tests/                      pytest tests for the library
hacs.json                   HACS metadata
.github/workflows/          validate.yml (hassfest, HACS, tests), release.yml
```

## Why the build step exists

HACS (and Home Assistant) only look at `custom_components/ring_plus/`. The integration imports
the library from the separate `aioring/` folder, so for distribution `scripts/build.sh`
**bundles the library inside the integration** and rewrites the imports (`from aioring …` →
`from .aioring …`). The result is:

- `dist/ring_plus.zip`: release asset used by HACS (`zip_release` in `hacs.json`)
- `dist/ring_plus.tar.gz`: same content, convenient for `scp`

Never edit `dist/`; it is generated and git-ignored.

## Local setup

```sh
python3 -m venv .venv
.venv/bin/pip install -e "aioring[dev]"
.venv/bin/pytest -q tests
```

### Try the client against your account

`scripts/dump_alarm.py` is non-interactive. Put credentials in `.env` (git-ignored):

```
RING_USERNAME=you@example.com
RING_PASSWORD=...
```

```sh
.venv/bin/python scripts/dump_alarm.py                 # may stop and ask for 2FA
RING_OTP=123456 .venv/bin/python scripts/dump_alarm.py # then re-run with the code
```

The token is cached in `.ring_token.json`, so later runs need no password or code. The output
contains personal data (IPs, serials, coordinates); do not paste it publicly.

### Deploy to a test Home Assistant

```sh
./scripts/build.sh
scp dist/ring_plus.tar.gz root@<ha-host>:/tmp/
ssh root@<ha-host> 'mv /config/custom_components/ring_plus /root/ring_plus.bak 2>/dev/null;
  tar xzf /tmp/ring_plus.tar.gz -C /config/custom_components && rm /tmp/ring_plus.tar.gz'
```

Restart Home Assistant afterwards (Python modules are only reloaded on restart).

## Protocol notes

- **Login**: `POST https://oauth.ring.com/oauth/token` (password grant, then refresh token) with
  a stable `hardware_id` header; HTTP 412 means 2FA is required.
- **Alarm**: `GET https://app.ring.com/api/v1/clap/tickets?locationID=…` returns `host`, `ticket`
  and assets; connect a plain websocket to `wss://{host}/ws?authcode={ticket}&ack=false`.
  Frames are `{"channel": …, "msg": {…}}`. Request `DeviceInfoDocGetList`; updates arrive as
  `DataUpdate` with `datatype: DeviceInfoDocType`; commands are `DeviceInfoSet`
  (`security-panel.switch-mode`, `sound-siren`).
- **Cameras**: `clients_api/ring_devices` (includes `health` and `alerts`),
  `dings/active`, `doorbots/history`, `snapshots/image/{id}`.
- Reference implementations: [`ring-client-api`](https://github.com/dgreif/ring) and
  [`ring-mqtt`](https://github.com/tsightler/ring-mqtt).

## HACS: publishing and releasing

### One-time repository setup (needed for HACS validation)

1. **Description and topics.** On GitHub (repo → ⚙ next to *About*) add a description and topics such as
   `home-assistant`, `hacs`, `ring`, `ring-alarm`, `integration`.
2. **Issues enabled** (Settings → General → Features), because `manifest.json` links to the issue tracker.
3. Keep `hacs.json` and `custom_components/ring_plus/manifest.json` in the repository (they are).
4. For the automatic release workflow: Settings → Actions → General → *Workflow permissions* →
   **Read and write permissions**.

### Making a release

1. Bump `version` in `custom_components/ring_plus/manifest.json` (for example `0.1.1`).
2. Commit and push to `main`.
3. Tag and push the tag; the tag **must** be `v` + the manifest version:

   ```sh
   git tag v0.1.1 && git push origin v0.1.1
   ```

4. The **Release** workflow builds `ring_plus.zip` and attaches it to a new GitHub release.
   HACS then offers the update. The workflow fails on purpose when tag and manifest differ.

Without a release HACS has nothing to download, because `zip_release` is enabled.

### Adding the repository to HACS (end users)

See *Installation → Option A* in the [README](../README.md): HACS → ⋮ → Custom repositories →
repository URL, category *Integration*.

### Getting into the default HACS store (optional)

Custom-repository installs work without any approval. To be listed in HACS by default, the repo must
pass the **HACS** and **Hassfest** actions (both run in `validate.yml`), have a release, and be submitted
via a pull request to [`hacs/default`](https://github.com/hacs/default). Brand images for the default
store are also expected in [`home-assistant/brands`](https://github.com/home-assistant/brands) or the
integration's `brand/` folder (present here). Check the current requirements at
<https://hacs.xyz/docs/publish/integration/> before submitting.

## Status of the official Ring API

The Client ID / Secret / HMAC key from Ring's partner programme belong to the **official** API
(`oauth.ring.com/v2/authorize`, `api.amazonvision.com`). Its public documentation covers cameras,
doorbells, chimes and some sensors, with webhooks, but does not describe Alarm. Support for it
would be an additional, optional mode and is not implemented. **Never commit these credentials.**

## Known gaps

- Arming/disarming uses the command format of `ring-client-api`; changes to the panel state from
  Home Assistant are the least-tested part, so verify them while you are on site.
- The alarm "triggered" state mapping is an educated guess (`*-alarm` / `panic*` states).
- Controls for camera settings, lights and sirens are not implemented (write endpoints unverified).
