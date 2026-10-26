"""Tests for the Bose select platform."""

from bose.select import BoseAudioSelect

from .conftest import FakeHass, FakeSpeaker


def _audio_select(speaker):
    entity = BoseAudioSelect(speaker, {"productName": "Test"}, None, FakeHass())
    entity.async_write_ha_state = lambda: None
    return entity


async def test_failed_update_goes_unavailable_instead_of_raising():
    """A speaker that does not answer must not break the poll (issue #82)."""
    speaker = FakeSpeaker()

    async def no_answer():
        raise TimeoutError("no response from the speaker within 10 seconds")

    speaker.get_audio_mode = no_answer
    entity = _audio_select(speaker)

    await entity.async_update()

    assert not entity.available


async def test_update_recovers_when_the_speaker_answers_again():
    """Availability comes back with the first successful read."""
    speaker = FakeSpeaker()

    async def answers():
        return {
            "value": "NORMAL",
            "properties": {"supportedValues": ["NORMAL", "DIALOG"]},
        }

    speaker.get_audio_mode = answers
    entity = _audio_select(speaker)
    entity._attr_available = False  # noqa: SLF001

    await entity.async_update()

    assert entity.available
    assert entity.current_option == "normal"


async def test_push_restores_availability():
    """A notification proves the speaker is alive again."""
    speaker = FakeSpeaker()
    entity = _audio_select(speaker)
    entity._attr_available = False  # noqa: SLF001

    speaker.notify(
        "/audio/mode",
        {"value": "DIALOG", "properties": {"supportedValues": ["DIALOG"]}},
    )

    assert entity.available
    assert entity.current_option == "dialog"


async def test_audio_mode_preserves_supported_options_across_partial_push():
    """Notifications often carry just value; they must not empty the selector."""
    speaker = FakeSpeaker()
    entity = _audio_select(speaker)
    entity._parse_audio_mode(
        {
            "value": "NORMAL",
            "properties": {"supportedValues": ["NORMAL", "DIALOG", "DYNAMIC_DIALOG"]},
        },
        None,
    )
    assert entity.options == ["normal", "dialog", "dynamic_dialog"]
    speaker.notify("/audio/mode", {"value": "DIALOG"})
    assert entity.current_option == "dialog"
    assert entity.options == ["normal", "dialog", "dynamic_dialog"]


async def test_audio_mode_does_not_lose_state_on_invalid_push():
    speaker = FakeSpeaker()
    entity = _audio_select(speaker)
    entity._parse_audio_mode(
        {"value": "NORMAL", "properties": {"supportedValues": ["NORMAL", "DIALOG"]}},
        None,
    )
    speaker.notify("/audio/mode", {"properties": {"supportedValues": []}})
    assert entity.current_option == "normal"
    assert entity.options == ["normal", "dialog"]


async def test_audio_mode_rejects_unadvertised_selection_without_write():
    import pytest

    speaker = FakeSpeaker()
    entity = _audio_select(speaker)
    entity._parse_audio_mode(
        {"value": "NORMAL", "properties": {"supportedValues": ["NORMAL", "DIALOG"]}},
        None,
    )
    calls = []
    async def fake_set(value):
        calls.append(value)
        return True
    speaker.set_audio_mode = fake_set
    with pytest.raises(ValueError, match="unavailable or unsupported"):
        await entity.async_select_option("dynamic_dialog")
    assert calls == []


async def test_audio_mode_select_maps_dialogue_to_bose_enum():
    speaker = FakeSpeaker()
    entity = _audio_select(speaker)
    entity._parse_audio_mode(
        {"value": "NORMAL", "properties": {"supportedValues": ["NORMAL", "DIALOG"]}},
        None,
    )
    calls = []
    async def fake_set(value):
        calls.append(value)
        return True
    speaker.set_audio_mode = fake_set
    await entity.async_select_option("dialog")
    assert calls == ["DIALOG"]
    assert entity.current_option == "dialog"
    await entity.async_select_option("dialog")
    assert calls == ["DIALOG"]  # idempotent


async def test_audio_mode_rejected_write_preserves_current_option():
    import pytest

    speaker = FakeSpeaker()
    entity = _audio_select(speaker)
    entity._parse_audio_mode(
        {"value": "NORMAL", "properties": {"supportedValues": ["NORMAL", "DIALOG"]}},
        None,
    )
    async def fake_set(_):
        return False
    speaker.set_audio_mode = fake_set
    with pytest.raises(ValueError, match="rejected"):
        await entity.async_select_option("dialog")
    assert entity.current_option == "normal"


async def test_audio_mode_push_with_no_supported_options_does_not_allow_writes():
    import pytest
    speaker = FakeSpeaker()
    entity = _audio_select(speaker)
    entity._parse_audio_mode({"value": "NORMAL", "properties": {"supportedValues": []}}, None)
    assert entity.options == []
    with pytest.raises(ValueError, match="unavailable or unsupported"):
        await entity.async_select_option("dialog")


def test_audio_mode_and_cec_labels_present_for_known_values():
    import json
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]/"custom_components/bose"
    for filename in ("strings.json", "translations/en.json"):
        data=json.loads((root/filename).read_text())
        states=data["entity"]["select"]["audio_mode"]["state"]
        assert states["normal"] == "Normal"
        assert states["dialog"] == "Dialogue"
        assert states["dynamic_dialog"] == "Dynamic Dialogue"
        assert data["entity"]["select"]["cec_settings"]["state"]["option7"] == "Option 7 (TV power-on and power-off issues)"
