"""Config flow: login (+2FA), then choose which device types to import."""
from __future__ import annotations

import uuid
from typing import Any

import voluptuous as vol
from aioring import AuthError, RingAuth, Requires2FA
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector, SelectSelectorConfig, SelectSelectorMode)

from .const import (CONF_DEVICE_TYPES, CONF_HARDWARE_ID, CONF_TOKEN, DEFAULT_DEVICE_TYPES,
                    DOMAIN)

CONF_OTP = "otp"


def _types_schema(default: list[str]) -> vol.Schema:
    return vol.Schema({vol.Required(CONF_DEVICE_TYPES, default=default): SelectSelector(
        SelectSelectorConfig(options=DEFAULT_DEVICE_TYPES, multiple=True,
                             mode=SelectSelectorMode.LIST, translation_key="device_types"))})


class RingPlusConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._user: dict[str, str] = {}
        self._hardware_id = str(uuid.uuid4())
        self._token: dict[str, Any] | None = None
        self._reauth_entry = None

    async def _login(self, otp: str | None) -> RingAuth:
        auth = RingAuth(async_get_clientsession(self.hass), self._hardware_id)
        await auth.fetch_token(self._user[CONF_USERNAME], self._user[CONF_PASSWORD], otp)
        self._token = auth.token.as_dict()
        return auth

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        errors = {}
        if user_input:
            self._user = user_input
            try:
                await self._login(None)
            except Requires2FA:
                return await self.async_step_2fa()
            except AuthError:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                return await self._after_login()
        return self.async_show_form(step_id="user", errors=errors, data_schema=vol.Schema({
            vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}))

    async def async_step_2fa(self, user_input=None) -> ConfigFlowResult:
        errors = {}
        if user_input:
            try:
                await self._login(user_input[CONF_OTP])
            except AuthError:
                errors["base"] = "invalid_2fa"
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                return await self._after_login()
        return self.async_show_form(step_id="2fa", errors=errors,
                                    data_schema=vol.Schema({vol.Required(CONF_OTP): str}))

    async def _after_login(self) -> ConfigFlowResult:
        if self._reauth_entry:
            return self.async_update_reload_and_abort(
                self._reauth_entry, data={**self._reauth_entry.data, CONF_TOKEN: self._token,
                                          CONF_HARDWARE_ID: self._hardware_id})
        await self.async_set_unique_id(self._user[CONF_USERNAME].lower())
        self._abort_if_unique_id_configured()
        return await self.async_step_devices()

    async def async_step_devices(self, user_input=None) -> ConfigFlowResult:
        if user_input:
            return self.async_create_entry(
                title=self._user[CONF_USERNAME],
                data={CONF_USERNAME: self._user[CONF_USERNAME], CONF_TOKEN: self._token,
                      CONF_HARDWARE_ID: self._hardware_id},
                options={CONF_DEVICE_TYPES: user_input[CONF_DEVICE_TYPES]})
        return self.async_show_form(step_id="devices", data_schema=_types_schema(DEFAULT_DEVICE_TYPES))

    async def async_step_reauth(self, entry_data) -> ConfigFlowResult:
        self._reauth_entry = self._get_reauth_entry()
        self._hardware_id = self._reauth_entry.data[CONF_HARDWARE_ID]
        return await self.async_step_user()

    @staticmethod
    def async_get_options_flow(config_entry):
        return RingPlusOptionsFlow()


class RingPlusOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        if user_input:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_DEVICE_TYPES, DEFAULT_DEVICE_TYPES)
        return self.async_show_form(step_id="init", data_schema=_types_schema(current))
