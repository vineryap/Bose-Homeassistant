"""Minimal, privacy-safe read-only Bose soundbar status sensors."""

from __future__ import annotations

import re
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory

from ._pybose import BoseSpeaker
from .const import _LOGGER
from .entity import BoseBaseEntity
from .power_sync import power_sync_control_reason, power_sync_field_status

_SAFE_TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,47}$")


def status_value(body: Any, mode: str) -> str:
    """Extract strictly bounded status labels, never arbitrary payloads/IDs."""
    if not isinstance(body, dict):
        return "unknown"
    if mode == "audio_mode":
        value = body.get("value")
        return value if isinstance(value, str) and _SAFE_TOKEN.fullmatch(value) else "unknown"
    if mode == "power_sync":
        value = body.get("enabled")
        if type(value) is bool:
            return "enabled" if value else "disabled"
        return "unknown"
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
        if mode not in ("audio_mode", "update", "power_sync"):
            raise ValueError("Invalid soundbar status kind")
        self._mode = mode
        self._attr_translation_key = f"soundbar_{mode}_diagnostic"
        self._attr_native_value = "unknown"
        if mode == "power_sync":
            self._attr_extra_state_attributes = {
                **power_sync_field_status(None),
                "control_status": "unknown_response",
            }
        self._attr_icon = {
            "audio_mode": "mdi:equalizer",
            "update": "mdi:update",
            "power_sync": "mdi:power-settings",
        }[mode]
        self.speaker.attach_receiver(self._receive)

    @property
    def _resource(self) -> str:
        return {
            "audio_mode": "/audio/mode",
            "update": "/system/update/status",
            "power_sync": "/system/power/macro",
        }[self._mode]

    def _receive(self, data: Any) -> None:
        if not isinstance(data, dict):
            return
        header = data.get("header")
        if not isinstance(header, dict) or header.get("resource") != self._resource:
            return
        body = data.get("body")
        self._attr_native_value = status_value(body, self._mode)
        if (
            self._mode == "power_sync"
            and isinstance(body, dict)
            and ("powerOnDevice" in body or "powerOnTv" in body)
        ):
            # An enabled-only notification is a partial update. Retain the
            # schema from the last complete GET instead of misreporting it.
            self._attr_extra_state_attributes = {
                **power_sync_field_status(body),
                "control_status": power_sync_control_reason(body),
            }
        self._attr_available = True
        if self.hass is not None and self.entity_id is not None:
            self.async_write_ha_state()

    async def async_update(self) -> None:
        """Read status during initial setup or an explicit user refresh."""
        try:
            if self._mode == "audio_mode":
                response = await self.speaker.get_audio_mode()
            elif self._mode == "power_sync":
                response = await self.speaker.get_power_sync_status()
            else:
                response = await self.speaker.get_system_update_status()
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Bose soundbar status GET failed", exc_info=True)
            self._attr_available = False
            return
        self._attr_native_value = status_value(response, self._mode)
        if self._mode == "power_sync":
            self._attr_extra_state_attributes = {
                **power_sync_field_status(response),
                "control_status": power_sync_control_reason(response),
            }
        self._attr_available = True
