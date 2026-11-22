"""The IP Ban Manager integration."""

from __future__ import annotations

from datetime import datetime, timezone
from ipaddress import ip_address
from pathlib import Path
from typing import Any

import voluptuous as vol
from aiohttp import web
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.components import websocket_api
from homeassistant.helpers.http import HomeAssistantView

DOMAIN = "ip_ban_manager"
DATA_BANS = "bans"

ADD_SERVICE_SCHEMA = vol.Schema({vol.Required("ip"): cv.string})
REMOVE_SERVICE_SCHEMA = vol.Schema({vol.Required("ip"): cv.string})


def _ban_file(hass: HomeAssistant) -> Path:
    return Path(hass.config.path("ip_bans.yaml"))


def _load_bans(hass: HomeAssistant) -> list[dict[str, str]]:
    bans: list[dict[str, str]] = []
    if not _ban_file(hass).exists():
        return bans

    from homeassistant.config import load_yaml_config_file

    data = load_yaml_config_file(str(_ban_file(hass))) or {}
    if not isinstance(data, dict):
        return bans

    for ip, details in data.items():
        if not isinstance(details, dict):
            details = {}
        bans.append({
            "ip": str(ip),
            "banned_at": str(details.get("banned_at", "")),
        })
    return bans


def _write_bans(hass: HomeAssistant, bans: list[dict[str, str]]) -> None:
    import yaml

    rows: dict[str, dict[str, str]] = {}
    for ban in bans:
        row = {}
        if ban.get("banned_at"):
            row["banned_at"] = ban["banned_at"]
        rows[ban["ip"]] = row
    _ban_file(hass).write_text(
        yaml.safe_dump(rows, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


class IPBanManagerFrontendView(HomeAssistantView):
    """Serve the management panel module."""

    url = "/api/ip_ban_manager/frontend.js"
    name = "api:ip_ban_manager:frontend"
    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request):
        """Return the frontend JavaScript."""
        frontend = Path(__file__).with_name("frontend.js")
        content = await self.hass.async_add_executor_job(
            frontend.read_text, "utf-8"
        )
        return web.Response(text=content, content_type="application/javascript")


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][DATA_BANS] = await hass.async_add_executor_job(_load_bans, hass)
    await _async_register_services(hass)
    await _async_register_websocket(hass)
    hass.http.register_view(IPBanManagerFrontendView(hass))

    from homeassistant.components import panel_custom

    await panel_custom.async_register_panel(
        hass,
        front_url_path="ip-ban-manager",
        webcomponent_name="ip-ban-manager-panel",
        sidebar_title="IP Ban Manager",
        sidebar_icon="mdi:shield-lock",
        module_url="/api/ip_ban_manager/frontend.js",
        require_admin=True,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    return await async_setup(hass, {})


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    return True


async def _async_register_services(hass: HomeAssistant) -> None:
    async def add_ban(call: ServiceCall) -> None:
        ip = str(call.data["ip"]).strip()
        ip_obj = ip_address(ip)
        bans = await hass.async_add_executor_job(_load_bans, hass)
        if not any(ban["ip"] == ip for ban in bans):
            from homeassistant.components.http.ban import KEY_BAN_MANAGER

            manager = hass.http.app.get(KEY_BAN_MANAGER)
            if manager is not None:
                await manager.async_add_ban(ip_obj)
                bans = await hass.async_add_executor_job(_load_bans, hass)
            else:
                bans.append({
                    "ip": ip,
                    "banned_at": datetime.now(timezone.utc).isoformat(),
                })
                await hass.async_add_executor_job(_write_bans, hass, bans)
        hass.data[DOMAIN][DATA_BANS] = bans

    async def remove_ban(call: ServiceCall) -> None:
        ip = str(call.data["ip"]).strip()
        ip_address(ip)
        bans = await hass.async_add_executor_job(_load_bans, hass)
        bans = [ban for ban in bans if ban["ip"] != ip]
        await hass.async_add_executor_job(_write_bans, hass, bans)
        from homeassistant.components.http.ban import KEY_BAN_MANAGER

        manager = hass.http.app.get(KEY_BAN_MANAGER)
        if manager is not None:
            manager.ip_bans_lookup.pop(ip_address(ip), None)
        hass.data[DOMAIN][DATA_BANS] = bans

    async def refresh(call: ServiceCall) -> None:
        hass.data[DOMAIN][DATA_BANS] = await hass.async_add_executor_job(
            _load_bans, hass
        )

    hass.services.async_register(DOMAIN, "add_ban", add_ban, ADD_SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, "remove_ban", remove_ban, REMOVE_SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, "refresh", refresh)


async def _async_register_websocket(hass: HomeAssistant) -> None:
    @websocket_api.websocket_command({"type": f"{DOMAIN}/list"})
    @websocket_api.async_response
    async def list_bans(hass: HomeAssistant, connection, msg):
        bans = await hass.async_add_executor_job(_load_bans, hass)
        connection.send_result(msg["id"], {"bans": bans})

    @websocket_api.websocket_command({
        "type": f"{DOMAIN}/add",
        "ip": str,
    })
    @websocket_api.async_response
    async def add_ban(hass: HomeAssistant, connection, msg):
        ip = msg["ip"].strip()
        ip_address(ip)
        await hass.services.async_call(
            DOMAIN,
            "add_ban",
            {"ip": ip},
            blocking=True,
        )
        connection.send_result(msg["id"], {"ok": True})

    @websocket_api.websocket_command({"type": f"{DOMAIN}/remove", "ip": str})
    @websocket_api.async_response
    async def remove_ban(hass: HomeAssistant, connection, msg):
        await hass.services.async_call(
            DOMAIN,
            "remove_ban",
            {"ip": msg["ip"].strip()},
            blocking=True,
        )
        connection.send_result(msg["id"], {"ok": True})

    websocket_api.async_register_command(hass, list_bans)
    websocket_api.async_register_command(hass, add_ban)
    websocket_api.async_register_command(hass, remove_ban)
