"""Config flow for IP Ban Manager."""

from __future__ import annotations

from homeassistant import config_entries

from . import DOMAIN


class IPBanManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        if user_input is not None:
            return self.async_create_entry(title="IP Ban Manager", data={})
        return self.async_show_form(step_id="user")
