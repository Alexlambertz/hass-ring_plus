"""Ring Alarm websocket connection (plain WebSocket, as in ring-client-api).

GET clap/tickets -> wss://{host}/ws?authcode={ticket}&ack=false. Frames are JSON
envelopes {"channel": ..., "msg": {...}}; we send channel "message".
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import aiohttp

from .api import RingApi
from .devices import flatten_doc
from .exceptions import RingError

_LOGGER = logging.getLogger(__name__)

UpdateCallback = Callable[[], None]


class RingAlarmConnection:
    def __init__(self, session: aiohttp.ClientSession, api: RingApi, location_id: str) -> None:
        self._session = session
        self._api = api
        self.location_id = location_id
        self.devices: dict[str, dict[str, Any]] = {}  # zid -> flattened state
        self.asset_id: str | None = None
        self.connected = False
        self._listeners: list[UpdateCallback] = []
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._task: asyncio.Task | None = None
        self._seq = 1
        self._ready = asyncio.Event()

    def add_listener(self, cb: UpdateCallback) -> Callable[[], None]:
        self._listeners.append(cb)
        return lambda: self._listeners.remove(cb)

    def _notify(self) -> None:
        for cb in list(self._listeners):
            cb()

    async def start(self, timeout: float = 20) -> None:
        """Connect and wait for the first device list."""
        self._task = asyncio.create_task(self._run())
        try:
            await asyncio.wait_for(self._ready.wait(), timeout)
        except TimeoutError as err:
            await self.stop()
            raise RingError("Timed out waiting for Ring Alarm device list") from err

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None
        if self._ws and not self._ws.closed:
            await self._ws.close()

    async def _run(self) -> None:
        delay = 1
        while True:
            try:
                await self._connect_once()
                delay = 1
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Ring alarm connection failed: %s", err)
            self.connected = False
            self._notify()
            await asyncio.sleep(delay)
            delay = min(delay * 2, 300)

    async def _connect_once(self) -> None:
        ticket = await self._api.get_ws_ticket(self.location_id)
        assets = [a for a in ticket.get("assets", []) if a.get("kind") == "base_station_v1"]
        if not assets:
            raise RingError("No Ring Alarm base station at this location")
        self.asset_id = assets[0]["uuid"]
        url = f"wss://{ticket['host']}/ws?authcode={ticket['ticket']}&ack=false"
        async with self._session.ws_connect(url, heartbeat=30) as ws:
            self._ws = ws
            self.connected = True
            await self._send({"msg": "DeviceInfoDocGetList", "dst": self.asset_id})
            async for frame in ws:
                if frame.type != aiohttp.WSMsgType.TEXT:
                    continue
                try:
                    envelope = json.loads(frame.data)
                except ValueError:
                    continue
                if self._handle(envelope.get("channel"), envelope.get("msg")):
                    break  # hub disconnected; reconnect

    def _handle(self, channel: str | None, msg: Any) -> bool:
        """Process a message. Returns True if we should reconnect."""
        if not isinstance(msg, dict):
            return False
        if msg.get("datatype") == "HubDisconnectionEventType":
            return True
        if msg.get("msg") == "DeviceInfoDocGetList" or (
                channel == "DataUpdate" and msg.get("datatype") == "DeviceInfoDocType"):
            for doc in msg.get("body") or []:
                state = flatten_doc(doc)
                if zid := state.get("zid"):
                    self.devices.setdefault(zid, {}).update(state)
            self._ready.set()
            self._notify()
        return False

    async def _send(self, message: dict[str, Any]) -> None:
        if not self._ws or self._ws.closed:
            raise RingError("Ring Alarm websocket not connected")
        message["seq"] = self._seq
        self._seq += 1
        await self._ws.send_str(json.dumps({"channel": "message", "msg": message}))

    async def _command(self, zid: str, command_type: str, data: dict | None = None) -> None:
        body: dict[str, Any] = {"commandType": command_type}
        if data is not None:
            body["data"] = data
        await self._send({
            "msg": "DeviceInfoSet", "datatype": "DeviceInfoSetType", "dst": self.asset_id,
            "body": [{"zid": zid, "command": {"v1": [body]}}],
        })

    async def set_mode(self, panel_zid: str, mode: str, bypass: list[str] | None = None) -> None:
        """mode: 'none' (disarm), 'some' (home), 'all' (away)."""
        await self._command(panel_zid, "security-panel.switch-mode",
                            {"mode": mode, "bypass": bypass or []})

    async def sound_siren(self, panel_zid: str) -> None:
        await self._command(panel_zid, "security-panel.sound-siren")

    async def silence_siren(self, panel_zid: str) -> None:
        await self._command(panel_zid, "security-panel.silence-siren")
