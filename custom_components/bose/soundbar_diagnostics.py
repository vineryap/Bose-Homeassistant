"""Minimal, privacy-safe read-only Bose soundbar status sensors."""

from __future__ import annotations

import re
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory

from ._pybose import BoseSpeaker
from .const import _LOGGER
from .entity import BoseBaseEntity

_SAFE_TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,47}$")


def status_value(body: Any, mode: str) -> str:
    """Extract strictly bounded status labels, never arbitrary payloads/IDs."""
    if not isinstance(body, dict):
        return "unknown"
    if mode == "audio_mode":
        value = body.get("value")
        return value if isinstance(value, str) and _SAFE_TOKEN.fullmatch(value) else "unknown"
    if mode == "update":
        for key in ("status", "state", "phase", "updateState"):
            value = body.get(key)
            if isinstance(value, str) and _SAFE_TOKEN.fullmatch(value):
                return value
        for key in ("updateAvailable", "available"):
            value = body.get(key)
            if type(value) is bool:
                return "available" if value else "not_available"
        return "unknown"
    raise ValueError("Unsupported soundbar diagnostic mode")


class BoseSoundbarStatusSensor(BoseBaseEntity, SensorEntity):
    """Status-only diagnostics, no automatic control commands."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False

    def __init__(self, speaker: BoseSpeaker, mode: str) -> None:
        BoseBaseEntity.__init__(self, speaker)
        if mode not in ("audio_mode", "update"):
            raise ValueError("Invalid soundbar status kind")
        self._mode = mode
        self._attr_translation_key = f"soundbar_{mode}_diagnostic"
        self._attr_native_value = "unknown"
        self._attr_icon = "mdi:equalizer" if mode == "audio_mode" else "mdi:update"
        self.speaker.attach_receiver(self._receive)

    @property
    def _resource(self) -> str:
        return "/audio/mode" if self._mode == "audio_mode" else "/system/update/status"

    def _receive(self, data: Any) -> None:
        if not isinstance(data, dict):
            return
        header = data.get("header")
        if not isinstance(header, dict) or header.get("resource") != self._resource:
            return
        self._attr_native_value = status_value(data.get("body"), self._mode)
        self._attr_available = True
        if self.hass is not None and self.entity_id is not None:
            self.async_write_ha_state()

    async def async_update(self) -> None:
        """Read status during initial setup or an explicit user refresh."""
        try:
            response = (
                await self.speaker.get_audio_mode()
                if self._mode == "audio_mode"
                else await self.speaker.get_system_update_status()
            )
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Bose soundbar status GET failed", exc_info=True)
            self._attr_available = False
            return
        self._attr_native_value = status_value(response, self._mode)
        self._attr_available = True
