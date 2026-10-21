"""Bose optical auto-wake setting: explicit, reversible user control."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory

from ._pybose import BoseSpeaker
from .const import _LOGGER
from .entity import BoseBaseEntity

_RESOURCE = "/system/power/mode/opticalAutoWake"


class BoseOpticalAutoWakeSwitch(BoseBaseEntity, SwitchEntity):
    """Never change settings on startup; get only when requested."""

    _attr_translation_key = "optical_auto_wake"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:power-socket"
    _attr_should_poll = False

    def __init__(self, speaker: BoseSpeaker) -> None:
        BoseBaseEntity.__init__(self, speaker)
        self._attr_is_on = None
        self._attr_available = False
        self.speaker.attach_receiver(self._receive)

    def _receive(self, message: Any) -> None:
        if not isinstance(message, dict):
            return
        header = message.get("header")
        if not isinstance(header, dict) or header.get("resource") != _RESOURCE:
            return
        body = message.get("body")
        if isinstance(body, dict) and type(body.get("enabled")) is bool:
            self._attr_is_on = body["enabled"]
            self._attr_available = True
            if self.hass is not None and self.entity_id is not None:
                self.async_write_ha_state()

    async def async_update(self) -> None:
        try:
            body = await self.speaker.get_optical_auto_wake()
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Bose optical auto-wake GET failed", exc_info=True)
            self._attr_available = False
            return
        if not isinstance(body, dict) or type(body.get("enabled")) is not bool:
            self._attr_available = False
            return
        self._attr_is_on = body["enabled"]
        self._attr_available = True

    async def _change(self, enabled: bool) -> None:
        # The setting cannot be changed blindly when GET is unsupported or
        # returns an unexpected schema. Explicit UI action only.
        if not self.speaker.has_capability(_RESOURCE):
            raise ValueError("Optical auto-wake is not advertised")
        if type(self._attr_is_on) is not bool or not self.available:
            raise ValueError("Optical auto-wake state is unknown; refresh first")
        body = await self.speaker.set_optical_auto_wake(enabled)
        if isinstance(body, dict) and type(body.get("enabled")) is bool:
            if body["enabled"] != enabled:
                raise ValueError("Bose did not confirm the requested optical setting")
        self._attr_is_on = enabled
        if self.hass is not None and self.entity_id is not None:
            self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._change(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._change(False)
