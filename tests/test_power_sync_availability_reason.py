"""Friendly status diagnostics never leak Bose device identifiers."""

import json
from pathlib import Path

import pytest

from bose.power_sync import BosePowerSyncSwitch, power_sync_control_reason
from bose.soundbar_diagnostics import BoseSoundbarStatusSensor
from .conftest import FakeSpeaker


def test_status_and_control_have_distinct_display_names():
    root = Path(__file__).resolve().parents[1] / "custom_components/bose"
    for filename in ("strings.json", "translations/en.json"):
        data = json.loads((root / filename).read_text())
        assert data["entity"]["sensor"]["soundbar_power_sync_diagnostic"]["name"] == "Power Sync Status"
        assert data["entity"]["switch"]["power_sync"]["name"] == "Power Sync"


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        ({"enabled": False, "powerOnTv": False}, "missing_power_on_device"),
        ({"enabled": False, "powerOnDevice": None, "powerOnTv": False}, "null_power_on_device"),
        ({"enabled": False, "powerOnDevice": "", "powerOnTv": False}, "ready"),
        ({"enabled": False, "powerOnDevice": "SECRET-ID", "powerOnTv": False}, "ready"),
        ({"enabled": False, "powerOnDevice": "SECRET-ID"}, "missing_power_on_tv"),
        ({"enabled": "false", "powerOnDevice": "SECRET-ID", "powerOnTv": False}, "invalid_enabled"),
        (None, "unknown_response"),
    ]
)
def test_reason_only_mentions_field_status(body, reason):
    result = power_sync_control_reason(body)
    assert result == reason
    assert "SECRET" not in result


@pytest.mark.asyncio
async def test_status_diagnostic_exposes_blocker_from_read_only_response():
    speaker = FakeSpeaker(capabilities=("/system/power/macro",))
    async def get():
        return {"enabled": False, "powerOnTv": False, "private": "SECRET-ID"}
    speaker.get_power_sync_status = get
    sensor = BoseSoundbarStatusSensor(speaker, "power_sync")
    await sensor.async_update()
    attrs = sensor.extra_state_attributes
    assert attrs["control_status"] == "missing_power_on_device"
    assert attrs["configuration"] == "incomplete"
    assert attrs["power_on_device_field"] == "missing"
    assert "SECRET" not in str(attrs)
    assert not speaker.requests


@pytest.mark.asyncio
async def test_unavailable_switch_explains_reason_without_sending_write():
    speaker = FakeSpeaker(capabilities=("/system/power/macro",))
    async def get():
        return {"enabled": False, "powerOnTv": False, "private": "SECRET-ID"}
    speaker.get_power_sync_status = get
    switch = BosePowerSyncSwitch(speaker)
    await switch.async_update()
    assert switch.available is False
    assert switch.extra_state_attributes["unavailable_reason"] == "missing_power_on_device"
    assert "SECRET" not in str(switch.extra_state_attributes)
    assert not speaker.requests


@pytest.mark.asyncio
async def test_switch_removes_blocker_after_complete_status():
    speaker = FakeSpeaker(capabilities=("/system/power/macro",))
    current = {"enabled": False, "powerOnTv": False}
    async def get():
        return current.copy()
    speaker.get_power_sync_status = get
    switch = BosePowerSyncSwitch(speaker)
    await switch.async_update()
    assert switch.extra_state_attributes["unavailable_reason"] == "missing_power_on_device"
    current["powerOnDevice"] = ""
    await switch.async_update()
    assert switch.available is True
    assert switch.extra_state_attributes.get("unavailable_reason") is None


@pytest.mark.asyncio
async def test_failed_get_sets_safe_unavailable_reason():
    speaker = FakeSpeaker(capabilities=("/system/power/macro",))
    async def get():
        raise TimeoutError("synthetic")
    speaker.get_power_sync_status = get
    entity = BosePowerSyncSwitch(speaker)
    await entity.async_update()
    assert entity.available is False
    assert entity.extra_state_attributes["unavailable_reason"] == "read_failed"


@pytest.mark.asyncio
async def test_failing_explicit_change_explains_ambiguous_write():
    speaker = FakeSpeaker(capabilities=("/system/power/macro",))
    async def get():
        return {"enabled": False, "powerOnDevice": "", "powerOnTv": False}
    async def write(**kwargs):
        raise TimeoutError("synthetic command timeout")
    speaker.get_power_sync_status = get
    speaker.set_power_sync = write
    entity = BosePowerSyncSwitch(speaker)
    with pytest.raises(TimeoutError):
        await entity.async_turn_on()
    assert entity.available is False
    assert entity.extra_state_attributes["unavailable_reason"] == "write_unconfirmed"
