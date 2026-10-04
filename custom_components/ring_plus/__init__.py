"""Ring Plus: Ring Alarm, cameras and doorbells."""
from __future__ import annotations

from aioring import AuthError, RingApi, RingAuth, Token
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_DEVICE_TYPES, CONF_HARDWARE_ID, CONF_TOKEN, DOMAIN, PLATFORMS
from .coordinator import RingData, async_setup_data

type RingConfigEntry = ConfigEntry[RingData]


async def async_setup_entry(hass: HomeAssistant, entry: RingConfigEntry) -> bool:
    session = async_get_clientsession(hass)

    def _save_token(token: Token) -> None:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_TOKEN: token.as_dict()})

    t = entry.data[CONF_TOKEN]
    auth = RingAuth(session, entry.data[CONF_HARDWARE_ID],
                    Token(t["access_token"], t["refresh_token"], t["expires_at"]), _save_token)
    api = RingApi(session, auth)
    try:
        await auth.access_token()
        entry.runtime_data = await async_setup_data(
            hass, entry, api, set(entry.options.get(CONF_DEVICE_TYPES, [])))
    except AuthError as err:
        raise ConfigEntryAuthFailed from err
    except ConfigEntryNotReady:
        raise
    except Exception as err:  # noqa: BLE001
        raise ConfigEntryNotReady(str(err)) from err

    async def _on_stop(_: Event) -> None:
        await entry.runtime_data.async_shutdown()

    # Stop websockets before HA closes the shared HTTP session.
    entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _on_stop))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def _reload(hass: HomeAssistant, entry: RingConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: RingConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        await entry.runtime_data.async_shutdown()
    return ok
