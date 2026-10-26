"""Opt-in Power Sync master switch for Bose devices advertising the feature.

The Bose Music request includes three distinct configuration fields. This
switch edits only enabled, and preserves powerOnDevice and powerOnTv
using a fresh device read immediately before every explicit operator action.
"""

from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory

from ._pybose.BoseSpeaker import BoseSpeaker
from .const import _LOGGER
from .entity import BoseBaseEntity

_RESOURCE = "/system/power/macro"


def read_power_sync(body: Any) -> tuple[bool, str, bool] | None:
    """Read fields required to safely change master switch, never expose ID."""
    if not isinstance(body, dict):
        return None
    enabled = body.get("enabled")
    device = body.get("powerOnDevice")
    tv = body.get("powerOnTv")
    if (
        type(enabled) is not bool
        or not isinstance(device, str)
        or len(device) > 1024
        or type(tv) is not bool
    ):
        return None
    return enabled, device, tv


def power_sync_field_status(body: Any) -> dict[str, str]:
    """Expose presence and types only, never raw identifiers or token data.

    This is diagnostic information, not a remote-pairing judgement. A missing
    field can mean model restrictions, unpaired hardware, or a partial reply.
    """
    if not isinstance(body, dict):
        return {
            "configuration": "unknown",
            "enabled_field": "unknown",
            "power_on_device_field": "unknown",
            "power_on_tv_field": "unknown",
        }

    def label(field: str, expected_type: type) -> str:
        if field not in body:
            return "missing"
        value = body[field]
        if value is None:
            return "null"
        if type(value) is not expected_type:
            return "invalid"
        if expected_type is str and len(value) > 1024:
            return "invalid"
        return "string" if expected_type is str else "boolean"

    enabled = label("enabled", bool)
    device = label("powerOnDevice", str)
    tv = label("powerOnTv", bool)
    return {
        "configuration": "complete" if read_power_sync(body) is not None else "incomplete",
        "enabled_field": enabled,
        "power_on_device_field": device,
        "power_on_tv_field": tv,
    }


def power_sync_control_reason(body: Any) -> str:
    """Short, value-free reason a Power Sync configuration cannot be changed."""
    if not isinstance(body, dict):
        return "unknown_response"
    status = power_sync_field_status(body)
    if status["configuration"] == "complete":
        return "ready"
    for name, field, expected in (
        ("enabled", "enabled_field", "boolean"),
        ("power_on_device", "power_on_device_field", "string"),
        ("power_on_tv", "power_on_tv_field", "boolean"),
    ):
        value = status[field]
        if value != expected:
            return f"{value}_{name}"
    return "unknown_response"


class BosePowerSyncSwitch(BoseBaseEntity, SwitchEntity):
    """Change only Power Sync enabled, not remote TV/device settings."""

    _attr_translation_key = "power_sync"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:power-settings"
    _attr_should_poll = False

    def __init__(self, speaker: BoseSpeaker) -> None:
        BoseBaseEntity.__init__(self, speaker)
        self._attr_available = False
        self._attr_is_on = None
        self._attr_extra_state_attributes = {"unavailable_reason": "unknown_response"}
        self._change_lock = asyncio.Lock()
        self.speaker.attach_receiver(self._receive)

    def _write(self) -> None:
        if self.hass is not None and self.entity_id is not None:
            self.async_write_ha_state()

    def _receive(self, message: Any) -> None:
        if not isinstance(message, dict):
            return
        header = message.get("header")
        if not isinstance(header, dict) or header.get("resource") != _RESOURCE:
            return
        full_state = read_power_sync(message.get("body"))
        if full_state is None:
            return
        self._attr_is_on = full_state[0]
        self._attr_available = True
        self._attr_extra_state_attributes = {}
        self._write()

    async def async_update(self) -> None:
        body = None
        reason = "unknown_response"
        try:
            body = await self.speaker.get_power_sync_status()
            state = read_power_sync(body)
            reason = power_sync_control_reason(body)
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Bose Power Sync status GET failed", exc_info=True)
            state = None
            reason = "read_failed"
        if state is None:
            self._attr_available = False
            self._attr_extra_state_attributes = {
                "unavailable_reason": reason
            }
            self._write()
            return
        self._attr_is_on = state[0]
        self._attr_available = True
        self._attr_extra_state_attributes = {}
        self._write()

    def _mark_unavailable(self, reason: str) -> None:
        self._attr_available = False
        self._attr_extra_state_attributes = {"unavailable_reason": reason}
        self._write()

    async def _change(self, enabled: bool) -> None:
        async with self._change_lock:
            if not self.speaker.has_capability(_RESOURCE):
                self._mark_unavailable("not_advertised")
                raise ValueError("Power Sync not advertised by Bose device")
            try:
                before_body = await self.speaker.get_power_sync_status()
                before = read_power_sync(before_body)
            except Exception as exc:
                self._mark_unavailable("read_failed")
                raise ValueError("Cannot read Power Sync configuration") from exc
            if before is None:
                self._mark_unavailable(power_sync_control_reason(before_body))
                raise ValueError("Incomplete Power Sync configuration; no changes made")
            if before[0] == enabled:
                self._attr_is_on = enabled
                self._attr_available = True
                self._attr_extra_state_attributes = {}
                self._write()
                return

            try:
                await self.speaker.set_power_sync(
                    enabled=enabled,
                    power_on_device=before[1],
                    power_on_tv=before[2],
                )
                after = read_power_sync(await self.speaker.get_power_sync_status())
            except Exception:
                # A failed acknowledgement might still have applied a change.
                # Never retry or claim the UI is synchronized.
                self._mark_unavailable("write_unconfirmed")
                raise
            if after != (enabled, before[1], before[2]):
                self._mark_unavailable("verification_failed")
                raise ValueError("Power Sync setting could not be verified")
            self._attr_is_on = enabled
            self._attr_available = True
            self._attr_extra_state_attributes = {}
            self._write()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._change(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._change(False)
