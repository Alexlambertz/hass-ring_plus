"""REST helpers: devices, locations, alarm websocket tickets."""
from __future__ import annotations

from typing import Any

import aiohttp

from .auth import RingAuth

CLIENTS_API = "https://api.ring.com/clients_api"
DEVICES_API = "https://api.ring.com/devices/v1"
APP_API = "https://app.ring.com/api/v1"


class RingApi:
    def __init__(self, session: aiohttp.ClientSession, auth: RingAuth) -> None:
        self._session = session
        self._auth = auth

    async def _request(self, method: str, url: str, **kw: Any) -> Any:
        headers = {"Authorization": f"Bearer {await self._auth.access_token()}",
                   "hardware_id": self._auth.hardware_id, **kw.pop("headers", {})}
        async with self._session.request(method, url, headers=headers, **kw) as resp:
            resp.raise_for_status()
            return await resp.json() if resp.content_length != 0 else None

    async def get_devices(self) -> dict:
        """Cameras, doorbells, chimes, lights (legacy clients_api)."""
        return await self._request("GET", f"{CLIENTS_API}/ring_devices")

    async def get_locations(self) -> list[dict]:
        """Returns [{location_id, name, ...}] (devices/v1 endpoint, as in ring_doorbell)."""
        data = await self._request("GET", f"{DEVICES_API}/locations")
        return data.get("user_locations", [])

    async def get_active_dings(self) -> list[dict]:
        return await self._request("GET", f"{CLIENTS_API}/dings/active") or []

    async def get_history(self, limit: int = 50) -> list[dict]:
        """Latest events (motion/ding/...) across all devices, newest first."""
        return await self._request("GET", f"{CLIENTS_API}/doorbots/history",
                                   params={"limit": str(limit)}) or []

    async def get_snapshot(self, device_id: int | str) -> bytes:
        headers = {"Authorization": f"Bearer {await self._auth.access_token()}",
                   "hardware_id": self._auth.hardware_id}
        async with self._session.get(f"{CLIENTS_API}/snapshots/image/{device_id}",
                                     headers=headers) as resp:
            resp.raise_for_status()
            return await resp.read()

    async def refresh_snapshots(self, device_ids: list[int]) -> None:
        await self._request("PUT", f"{CLIENTS_API}/snapshots/update_all",
                            json={"doorbot_ids": device_ids, "timeout": 15, "refresh": True})

    async def get_ws_ticket(self, location_id: str) -> dict:
        """Returns {host, ticket, assets:[{uuid, kind,...}]} for the alarm websocket."""
        return await self._request(
            "GET", f"{APP_API}/clap/tickets",
            params={"locationID": location_id, "enableExtendedEmergencyCellUsage": "true",
                    "requestedTransport": "ws"})
