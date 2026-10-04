"""Log in to Ring, list locations and dump Alarm devices (to verify the protocol).

Non-interactive. Credentials come from the environment or ./.env:
  RING_USERNAME, RING_PASSWORD, and (only when Ring asks for it) RING_OTP.
The token is cached in ./.ring_token.json (git-ignored), so 2FA is needed only once.

  1st run: Ring emails/texts a code and the script exits -> put it in RING_OTP, re-run.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

import aiohttp
from aioring import RingAlarmConnection, RingApi, RingAuth, Requires2FA, Token

ROOT = Path(__file__).resolve().parent.parent
TOKEN_FILE = ROOT / ".ring_token.json"


def load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


async def main() -> None:
    load_env()
    async with aiohttp.ClientSession() as session:
        def save(token: Token) -> None:
            TOKEN_FILE.write_text(json.dumps({"hardware_id": auth.hardware_id,
                                              **token.as_dict()}))
            TOKEN_FILE.chmod(0o600)

        auth = RingAuth(session, token_updater=save)
        if TOKEN_FILE.exists():
            t = json.loads(TOKEN_FILE.read_text())
            auth.hardware_id = t["hardware_id"]
            auth.token = Token(t["access_token"], t["refresh_token"], t["expires_at"])
        else:
            hw = ROOT / ".ring_hw"
            if hw.exists():
                auth.hardware_id = hw.read_text().strip()
            user, pw = os.environ.get("RING_USERNAME"), os.environ.get("RING_PASSWORD")
            if not (user and pw):
                sys.exit("Set RING_USERNAME and RING_PASSWORD (env or .env).")
            try:
                await auth.fetch_token(user, pw, os.environ.get("RING_OTP"))
            except Requires2FA:
                # hardware_id must stay the same between the two attempts
                Path(ROOT / ".ring_hw").write_text(auth.hardware_id)
                sys.exit("Ring requires a 2FA code. Set RING_OTP=<code> and re-run now.")
            save(auth.token)

        api = RingApi(session, auth)
        for loc in await api.get_locations():
            print("Location:", loc.get("name"), loc["location_id"])
            conn = RingAlarmConnection(session, api, loc["location_id"])
            try:
                await conn.start()
            except Exception as err:  # noqa: BLE001
                print("  no alarm:", err)
                continue
            print(json.dumps(conn.devices, indent=2))
            await conn.stop()
        print("Cameras:", json.dumps(await api.get_devices(), indent=2)[:3000])


asyncio.run(main())
