"""Read-only, identifier-free Bose wireless accessory diagnostics.

This module never sends a pairing or enable/disable request.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory

from ._pybose import BoseSpeaker
from .const import _LOGGER
from .entity import BoseBaseEntity


def summarize_accessory_links(body: Any, kind: str) -> tuple[str, dict[str, int]]:
    """Summarize reported links without retaining any sensitive accessory fields.

    A wired or wireless connection only describes the *current* transport,
    and cannot prove whether wireless hardware is installed or supported.
    """
    if not isinstance(body, dict) or kind not in ("subs", "rears"):
        return "unknown", {}
    entries = body.get(kind)
    if not isinstance(entries, list):
        return "unknown", {}

    available_count = 0
    wireless_count = 0
    wired_count = 0

    for entry in entries:
        if not isinstance(entry, dict) or entry.get("available") is not True:
            continue
        available_count += 1
        wireless = entry.get("wireless")
        if wireless is True:
            wireless_count += 1
        elif wireless is False:
            wired_count += 1

    attributes = {
        "available_count": available_count,
        "wireless_count": wireless_count,
        "wired_count": wired_count,
    }
    if not available_count:
        return "disconnected", attributes
    if wireless_count and wired_count:
        return "mixed", attributes
    if wireless_count == available_count:
        return "wireless", attributes
    if wired_count == available_count:
        return "wired", attributes
    return "unknown", attributes


def summarize_pairing(body: Any) -> str:
    """Decode firmware's two observed pairing-state field spellings."""
    if not isinstance(body, dict):
        return "unknown"
    for field in ("pairing", "pairingMode"):
        value = body.get(field)
        if type(value) is bool:
            return "active" if value else "inactive"
    return "unknown"


class BoseAccessoryDiagnosticSensor(BoseBaseEntity, SensorEntity):
    """Show an accessory connection or pairing state without exposing serials."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:speaker-wireless"

    def __init__(self, speaker: BoseSpeaker, mode: str, snapshot: dict[str, Any]) -> None:
        BoseBaseEntity.__init__(self, speaker)
        if mode not in ("subs", "rears", "pairing"):
            raise ValueError("Unknown accessory diagnostic mode")
        self._mode = mode
        self._cf_unique_id = f"accessories_{mode}_diagnostic"
        self._attr_translation_key = f"accessories_{mode}_diagnostic"
        self._attr_extra_state_attributes: dict[str, int] = {}
        self._apply_status(snapshot)
        self.speaker.attach_receiver(self._receive)

    def _apply_status(self, body: Any) -> None:
        if self._mode == "pairing":
            self._attr_native_value = summarize_pairing(body)
            self._attr_extra_state_attributes = {}
        else:
            self._attr_native_value, self._attr_extra_state_attributes = (
                summarize_accessory_links(body, self._mode)
            )

    def _receive(self, data: Any) -> None:
        if not isinstance(data, dict):
            return
        header = data.get("header")
        if not isinstance(header, dict) or header.get("resource") != "/accessories":
            return
        body = data.get("body")
        if not isinstance(body, dict):
            return
        self._apply_status(body)
        # An attached HA entity must not emit before the platform adds it.
        if self.hass is not None and self.entity_id is not None:
            self.async_write_ha_state()

    async def async_update(self) -> None:
        """Explicit refresh only (automatic polling is disabled)."""
        try:
            body = await self.speaker.get_accessories()
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Could not read accessory diagnostic status", exc_info=True)
            self._attr_available = False
            return
        self._attr_available = True
        self._apply_status(body)
