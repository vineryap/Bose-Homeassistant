"""Mock-only tests for new soundbar statuses and optical auto-wake."""

from types import SimpleNamespace

import pytest

from bose import sensor, switch
from bose.optical_auto_wake import BoseOpticalAutoWakeSwitch
from bose.soundbar_diagnostics import BoseSoundbarStatusSensor, status_value
from .conftest import FakeHass, FakeSpeaker


def test_status_values_drop_unknown_fields_and_secret_strings():
    assert status_value({"value": "DIALOGUE", "token": "SECRET"}, "audio_mode") == "DIALOGUE"
    assert status_value({"value": "TV HDMI: SECRET"}, "audio_mode") == "unknown"
    assert status_value({"value": "a" * 500}, "audio_mode") == "unknown"
    assert status_value({"status": "IDLE", "personId": "SECRET"}, "update") == "IDLE"
    assert status_value({"available": True, "url": "secret"}, "update") == "available"
    assert status_value({"updateAvailable": False}, "update") == "not_available"
    assert status_value({"state": ["secret"]}, "update") == "unknown"
    assert status_value(None, "update") == "unknown"
    with pytest.raises(ValueError):
        status_value({"value": "UNKNOWN"}, "unsupported")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "resource", "expected"),
    [
        ("audio_mode", "/audio/mode", "STANDARD"),
        ("update", "/system/update/status", "READY"),
    ],
)
async def test_diagnostic_getter_only_and_update(mode, resource, expected):
    speaker = FakeSpeaker(capabilities=(resource,))
    calls = []

    async def audio():
        calls.append("get_audio_mode")
        return {"value": "STANDARD", "serialnum": "SECRET"}

    async def update():
        calls.append("get_system_update_status")
        return {"state": "READY", "downloadUri": "SECRET"}

    speaker.get_audio_mode = audio
    speaker.get_system_update_status = update

    entity = BoseSoundbarStatusSensor(speaker, mode)
    assert entity.should_poll is False
    assert entity.native_value == "unknown"
    await entity.async_update()
    assert entity.native_value == expected
    assert entity.available
    assert calls == ["get_audio_mode" if mode == "audio_mode" else "get_system_update_status"]
    assert not speaker.requests
    speaker.notify(resource, {"value": "MUSIC", "state": "CHECKING", "secret": "hidden"})
    assert entity.native_value == ("MUSIC" if mode == "audio_mode" else "CHECKING")


@pytest.mark.asyncio
async def test_status_get_failure_fails_closed():
    speaker = FakeSpeaker()

    async def raises():
        raise OSError("fake disconnect")

    speaker.get_audio_mode = raises
    entity = BoseSoundbarStatusSensor(speaker, "audio_mode")
    await entity.async_update()
    assert entity.available is False


@pytest.mark.asyncio
async def test_capability_gated_status_sensor_setup():
    speaker = FakeSpeaker(capabilities=("/audio/mode", "/system/update/status"))
    hass = FakeHass()
    hass.data = {"bose": {"e1": {
        "speaker": speaker,
        "coordinator": None,
        "accessories": {},
    }}}
    added = []
    await sensor.async_setup_entry(
        hass,
        SimpleNamespace(entry_id="e1", data={"ip": "fake", "guid": "fake"}),
        lambda entities, **kw: added.extend(entities),
    )
    assert [e._mode for e in added] == ["audio_mode", "update"]
    assert not speaker.requests


@pytest.mark.asyncio
async def test_optical_requires_successful_read_before_write():
    speaker = FakeSpeaker(capabilities=("/system/power/mode/opticalAutoWake",))
    writes = []

    async def get():
        return {"enabled": False}

    async def set_state(state):
        writes.append(state)
        return {"enabled": state}

    speaker.get_optical_auto_wake = get
    speaker.set_optical_auto_wake = set_state
    entity = BoseOpticalAutoWakeSwitch(speaker)

    with pytest.raises(ValueError, match="unknown"):
        await entity.async_turn_on()
    assert writes == []
    await entity.async_update()
    assert entity.available
    assert entity.is_on is False
    await entity.async_turn_on()
    assert writes == [True]
    assert entity.is_on is True
    await entity.async_turn_off()
    assert writes == [True, False]
    assert entity.is_on is False


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", [{"enabled": "on"}, {}, ["other"], None])
async def test_optical_invalid_read_refuses_to_write(invalid):
    speaker = FakeSpeaker(capabilities=("/system/power/mode/opticalAutoWake",))
    async def get():
        return invalid
    async def bad_set(_):
        raise AssertionError("write must not happen")
    speaker.get_optical_auto_wake = get
    speaker.set_optical_auto_wake = bad_set
    entity = BoseOpticalAutoWakeSwitch(speaker)
    await entity.async_update()
    assert not entity.available
    with pytest.raises(ValueError, match="unknown"):
        await entity.async_turn_on()


@pytest.mark.asyncio
async def test_optical_read_error_and_response_mismatch():
    speaker = FakeSpeaker(capabilities=("/system/power/mode/opticalAutoWake",))
    async def get():
        return {"enabled": True}
    async def mismatched(_):
        return {"enabled": True}
    speaker.get_optical_auto_wake = get
    speaker.set_optical_auto_wake = mismatched
    entity = BoseOpticalAutoWakeSwitch(speaker)
    await entity.async_update()
    with pytest.raises(ValueError, match="did not confirm"):
        await entity.async_turn_off()
    assert entity.is_on is True


@pytest.mark.asyncio
async def test_optical_switch_is_gated_when_setup():
    speaker = FakeSpeaker(capabilities=("/system/power/mode/opticalAutoWake",))
    hass = FakeHass()
    hass.data = {"bose": {"e1": {
        "speaker": speaker, "system_info": {}, "accessories": {},
    }}}
    added = []
    await switch.async_setup_entry(
        hass, SimpleNamespace(entry_id="e1", data={}),
        lambda entities, **kwargs: added.extend(entities)
    )
    assert [type(e).__name__ for e in added] == ["BoseOpticalAutoWakeSwitch"]
    assert speaker.requests == []
