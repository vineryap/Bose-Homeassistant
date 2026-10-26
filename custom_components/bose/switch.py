"""Support for Bose power switch."""

from typing import Any

from ._pybose.BoseResponse import Accessories, SystemInfo, SystemTimeout
from ._pybose.BoseSpeaker import BoseSpeaker

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .optical_auto_wake import BoseOpticalAutoWakeSwitch
from .const import _LOGGER, DOMAIN
from .entity import BoseBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Bose switch."""
    speaker: BoseSpeaker = hass.data[DOMAIN][config_entry.entry_id]["speaker"]

    # Fetch system info
    system_info = hass.data[DOMAIN][config_entry.entry_id]["system_info"]
    accessories = hass.data[DOMAIN][config_entry.entry_id]["accessories"]

    entities: list[SwitchEntity] = []
    if speaker.has_capability("/system/power/mode/opticalAutoWake"):
        async_add_entities(
            [BoseOpticalAutoWakeSwitch(speaker)],
            update_before_add=True,
        )
    if speaker.has_capability("/system/power/timeouts"):
        entities.append(
            BoseStandbySettingSwitch(speaker, system_info, config_entry, hass)
        )
    else:
        _LOGGER.debug("Speaker does not support system timeouts")

    if accessories:
        if accessories.get("controllable", {}).get("subs", False):
            entities.append(
                BoseSubwooferSwitch(speaker, system_info, accessories, config_entry)
            )
        if accessories.get("controllable", {}).get("rears", False):
            entities.append(
                BoseRearSpeakerSwitch(speaker, system_info, accessories, config_entry)
            )

    # Add switch entity with device info
    async_add_entities(
        entities,
        update_before_add=False,
    )


class BoseAccessorySwitch(BoseBaseEntity, SwitchEntity):
    """Generic accessory switch for Bose speakers."""

    def __init__(
        self,
        speaker: BoseSpeaker,
        speaker_info: SystemInfo,
        accessories: Accessories,
        config_entry,
        name: str,
        attribute: str,
    ) -> None:
        """Initialize the switch."""
        BoseBaseEntity.__init__(self, speaker)
        self.speaker = speaker
        self._attribute = attribute
        self._attr_is_on = (
            accessories.get("enabled", {}).get(attribute) if accessories else False
        )
        self.speaker_info = speaker_info
        self.config_entry = config_entry
        self._attr_translation_key = attribute
        self.icon = "mdi:speaker"

        self.speaker.attach_receiver(self._parse_message)

    async def _change_accessory(self, enabled: bool) -> None:
        """Write one setting and update the UI only after acknowledgement."""
        result = await self.speaker.put_accessories(
            **{f"{self._attribute}_enabled": enabled}
        )
        if result is False:
            raise ValueError("Bose refused accessory enablement change")
        self._attr_is_on = enabled
        self._attr_available = True
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the selected accessory without changing the other one."""
        await self._change_accessory(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the selected accessory without changing the other one."""
        await self._change_accessory(False)

    def _parse_message(self, data):
        """Ignore partial or malformed accessory event bodies."""
        if not isinstance(data, dict):
            return
        header = data.get("header")
        if isinstance(header, dict) and header.get("resource") == "/accessories":
            self._parse_accessories(data.get("body"))

    def _parse_accessories(self, data: Accessories):
        """Only update our own explicitly present boolean state."""
        if not isinstance(data, dict):
            return
        enabled = data.get("enabled")
        if not isinstance(enabled, dict):
            return
        state = enabled.get(self._attribute)
        if type(state) is not bool:
            return
        self._attr_is_on = state
        self._attr_available = True
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the switch state."""
        try:
            accessories = await self.speaker.get_accessories()
        except Exception:  # noqa: BLE001
            _LOGGER.debug(
                "Cannot read the accessory state from the speaker", exc_info=True
            )
            if self._attr_available:
                self._attr_available = False
                self.async_write_ha_state()
            return
        self._parse_accessories(accessories)


class BoseSubwooferSwitch(BoseAccessorySwitch):
    """Switch to turn on/off subwoofers."""

    def __init__(
        self,
        speaker: BoseSpeaker,
        speaker_info: SystemInfo,
        accessories: Accessories,
        config_entry,
    ) -> None:
        """Initialize the switch."""
        super().__init__(
            speaker, speaker_info, accessories, config_entry, "Subwoofers", "subs"
        )


class BoseRearSpeakerSwitch(BoseAccessorySwitch):
    """Switch to turn on/off rear speakers."""

    def __init__(
        self,
        speaker: BoseSpeaker,
        speaker_info: SystemInfo,
        accessories: Accessories,
        config_entry,
    ) -> None:
        """Initialize the switch."""
        super().__init__(
            speaker, speaker_info, accessories, config_entry, "Rear Speakers", "rears"
        )


class BoseStandbySettingSwitch(BoseBaseEntity, SwitchEntity):
    """Switch to turn on/off standby setting."""

    def __init__(
        self,
        speaker: BoseSpeaker,
        speaker_info: SystemInfo,
        config_entry,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the switch."""
        BoseBaseEntity.__init__(self, speaker)
        self.speaker = speaker
        self._attr_is_on = None
        self.speaker_info = speaker_info
        self.config_entry = config_entry
        self.icon = "mdi:power-standby"
        self._attr_translation_key = "auto_standby"

        self._attr_entity_category = EntityCategory.CONFIG

        self.speaker.attach_receiver(self._parse_message)
        hass.async_create_task(self.async_update())

    def _parse_message(self, data):
        """Ignore partial timeout updates without an explicit boolean state."""
        if not isinstance(data, dict):
            return
        header = data.get("header")
        if not isinstance(header, dict) or header.get("resource") != "/system/power/timeouts":
            return
        result = data.get("body")
        if not isinstance(result, dict) or type(result.get("noAudio")) is not bool:
            return
        self._attr_is_on = result["noAudio"]
        self._attr_available = True
        self.async_write_ha_state()

    async def _change(self, enabled: bool) -> None:
        """Read both timeout values, then change only the selected setting.

        The underlying endpoint requires both fields, so hard-coding
        noVideo=False could overwrite an unrelated existing configuration.
        """
        timeouts = await self.speaker.get_system_timeout()
        if not isinstance(timeouts, dict) or any(
            type(timeouts.get(key)) is not bool for key in ("noAudio", "noVideo")
        ):
            raise ValueError("Bose timeout state is unknown; change refused")
        if timeouts["noAudio"] == enabled:
            self._attr_is_on = enabled
            self._attr_available = True
            self.async_write_ha_state()
            return
        result = await self.speaker.set_system_timeout(
            enabled, timeouts["noVideo"]
        )
        if isinstance(result, dict) and type(result.get("noAudio")) is bool:
            if result["noAudio"] != enabled:
                raise ValueError("Bose did not confirm standby timeout change")
        self._attr_is_on = enabled
        self._attr_available = True
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable standby on no audio, preserving video timeout."""
        await self._change(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable standby on no audio, preserving video timeout."""
        await self._change(False)

    async def async_update(self) -> None:
        """Update the switch state."""
        try:
            timeouts = await self.speaker.get_system_timeout()
        except Exception:  # noqa: BLE001
            _LOGGER.debug(
                "Cannot read the standby setting from the speaker", exc_info=True
            )
            if self._attr_available:
                self._attr_available = False
                self.async_write_ha_state()
            return
        if not isinstance(timeouts, dict) or type(timeouts.get("noAudio")) is not bool:
            self._attr_available = False
            self.async_write_ha_state()
            return
        self._attr_is_on = timeouts["noAudio"]
        self._attr_available = True
        self.async_write_ha_state()
