"""OAuth against oauth.ring.com (password grant + refresh token)."""
from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass

import aiohttp

from .exceptions import AuthError, Requires2FA

OAUTH_URL = "https://oauth.ring.com/oauth/token"
CLIENT_ID = "ring_official_android"


@dataclass
class Token:
    access_token: str
    refresh_token: str
    expires_at: float

    @property
    def expired(self) -> bool:
        return time.time() >= self.expires_at - 60

    def as_dict(self) -> dict:
        return {"access_token": self.access_token, "refresh_token": self.refresh_token,
                "expires_at": self.expires_at}


def _token(data: dict) -> Token:
    return Token(data["access_token"], data["refresh_token"],
                 time.time() + int(data.get("expires_in", 3600)))


class RingAuth:
    def __init__(self, session: aiohttp.ClientSession, hardware_id: str | None = None,
                 token: Token | None = None,
                 token_updater: Callable[[Token], None] | None = None) -> None:
        self._session = session
        self._token_updater = token_updater
        self.hardware_id = hardware_id or str(uuid.uuid4())
        self.token = token

    @property
    def _headers(self) -> dict:
        return {"hardware_id": self.hardware_id, "2fa-support": "true",
                "User-Agent": "android:com.ringapp"}

    async def fetch_token(self, username: str, password: str, otp: str | None = None) -> Token:
        headers = dict(self._headers)
        if otp:
            headers["2fa-code"] = otp
        body = {"client_id": CLIENT_ID, "grant_type": "password", "scope": "client",
                "username": username, "password": password}
        async with self._session.post(OAUTH_URL, json=body, headers=headers) as resp:
            if resp.status == 412:
                raise Requires2FA("2FA code required")
            if resp.status in (400, 401):
                raise AuthError(await resp.text())
            resp.raise_for_status()
            self._set_token(_token(await resp.json()))
        return self.token

    def _set_token(self, token: Token) -> None:
        self.token = token
        if self._token_updater:
            self._token_updater(token)

    async def refresh(self) -> Token:
        if not self.token:
            raise AuthError("no token")
        body = {"client_id": CLIENT_ID, "grant_type": "refresh_token",
                "scope": "client", "refresh_token": self.token.refresh_token}
        async with self._session.post(OAUTH_URL, json=body, headers=self._headers) as resp:
            if resp.status in (400, 401):
                raise AuthError(await resp.text())
            resp.raise_for_status()
            self._set_token(_token(await resp.json()))
        return self.token

    async def access_token(self) -> str:
        if not self.token:
            raise AuthError("not authenticated")
        if self.token.expired:
            await self.refresh()
        return self.token.access_token
