"""Safe schema diagnostics for Power Sync without exposing device identifiers."""

import pytest

from bose.power_sync import power_sync_field_status
from bose.soundbar_diagnostics import BoseSoundbarStatusSensor
from .conftest import FakeSpeaker


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (
            {"enabled": False, "powerOnDevice": "PRIVATE-DEVICE-ID", "powerOnTv": False},
            {
                "configuration": "complete",
                "enabled_field": "boolean",
                "power_on_device_field": "string",
                "power_on_tv_field": "boolean",
            },
        ),
        (
            {"enabled": False, "powerOnDevice": None, "powerOnTv": False},
            {
                "configuration": "incomplete",
                "enabled_field": "boolean",
                "power_on_device_field": "null",
                "power_on_tv_field": "boolean",
            },
        ),
        (
            {"enabled": False},
            {
                "configuration": "incomplete",
                "enabled_field": "boolean",
                "power_on_device_field": "missing",
                "power_on_tv_field": "missing",
            },
        ),
        (
            {"enabled": False, "powerOnDevice": 42, "powerOnTv": "false"},
            {
                "configuration": "incomplete",
                "enabled_field": "boolean",
                "power_on_device_field": "invalid",
                "power_on_tv_field": "invalid",
            },
        ),
        (
            None,
            {
                "configuration": "unknown",
                "enabled_field": "unknown",
                "power_on_device_field": "unknown",
                "power_on_tv_field": "unknown",
            },
        ),
    ],
)
def test_only_types_and_presence_are_exposed(body, expected):
    result = power_sync_field_status(body)
    assert result == expected
    assert "PRIVATE" not in str(result)
    assert "42" not in str(result)


@pytest.mark.asyncio
async def test_diagnostic_reports_null_field_from_actual_get_without_leaking_value():
    speaker = FakeSpeaker(capabilities=("/system/power/macro",))
    calls = []
    async def get():
        calls.append("GET")
        return {"enabled": False, "powerOnDevice": None, "powerOnTv": False, "id":"SECRET-IDENTIFIER"}
    speaker.get_power_sync_status = get
    entity = BoseSoundbarStatusSensor(speaker, "power_sync")
    await entity.async_update()
    assert entity.native_value == "disabled"
    assert entity.extra_state_attributes["configuration"] == "incomplete"
    assert entity.extra_state_attributes["power_on_device_field"] == "null"
    assert entity.extra_state_attributes["power_on_tv_field"] == "boolean"
    assert "SECRET" not in str(entity.extra_state_attributes)
    assert calls == ["GET"]
    assert speaker.requests == []


@pytest.mark.asyncio
async def test_partial_push_does_not_replace_last_complete_get_schema():
    speaker = FakeSpeaker(capabilities=("/system/power/macro",))
    async def get():
        return {"enabled": False, "powerOnDevice": "SENSITIVE", "powerOnTv": True}
    speaker.get_power_sync_status = get
    entity = BoseSoundbarStatusSensor(speaker, "power_sync")
    await entity.async_update()
    assert entity.extra_state_attributes["configuration"] == "complete"
    speaker.notify("/system/power/macro", {"enabled": True})
    assert entity.native_value == "enabled"
    assert entity.extra_state_attributes["configuration"] == "complete"
    speaker.notify("/system/power/macro", {"enabled": True, "powerOnDevice":None, "powerOnTv": True})
    assert entity.extra_state_attributes["configuration"] == "incomplete"
    assert entity.extra_state_attributes["power_on_device_field"] == "null"


def test_auto_standby_translation_explains_fixed_interval_without_changing_entity_key():
    import json
    from pathlib import Path
    from bose.switch import BoseStandbySettingSwitch
    from .conftest import FakeHass
    entity = BoseStandbySettingSwitch(
        FakeSpeaker(), {"productName": "Test"}, None, FakeHass()
    )
    assert entity._attr_translation_key == "auto_standby"
    root = Path(__file__).resolve().parents[1]/"custom_components/bose"
    for name in ("strings.json", "translations/en.json"):
        data = json.loads((root/name).read_text())
        assert data["entity"]["switch"]["auto_standby"]["name"] == "Standby Timer"
