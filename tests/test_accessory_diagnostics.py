"""Read-only accessory diagnostics: no identity leaks and no pairing commands."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from bose import sensor
from bose.accessory_diagnostics import (
    BoseAccessoryDiagnosticSensor,
    summarize_accessory_links,
    summarize_pairing,
)

from .conftest import FakeHass, FakeSpeaker


ACCESSORIES = {
    "pairing": False,
    "enabled": {"subs": True, "rears": True},
    "subs": [
        {
            "type": "BOSE_BASS_MODULE_700",
            "serialnum": "PRIVATE_SERIAL_SUB",
            "available": True,
            "wireless": False,
        }
    ],
    "rears": [
        {"serialnum": "PRIVATE_SERIAL_REAR_A", "wireless": True, "available": True},
        {"serialnum": "PRIVATE_SERIAL_REAR_B", "wireless": True, "available": True},
    ],
    "account": "PRIVATE_ACCOUNT",
}


def test_report_actual_snapshot_without_ids():
    state, attributes = summarize_accessory_links(ACCESSORIES, "subs")
    assert state == "wired"
    assert attributes == {
        "available_count": 1,
        "wireless_count": 0,
        "wired_count": 1,
    }
    state, attributes = summarize_accessory_links(ACCESSORIES, "rears")
    assert state == "wireless"
    assert attributes["wireless_count"] == 2
    assert summarize_pairing(ACCESSORIES) == "inactive"
    assert summarize_pairing({"pairingMode": True}) == "active"


def test_unknown_bad_data_never_leaks():
    assert summarize_accessory_links({"subs": "SECRET"}, "subs") == ("unknown", {})
    assert summarize_accessory_links({}, "subs") == ("unknown", {})
    assert summarize_accessory_links({"subs": []}, "subs")[0] == "disconnected"
    assert summarize_accessory_links({"subs": [{"available": True}]}, "subs")[0] == "unknown"
    assert summarize_accessory_links(
        {"subs": [{"available": True, "wireless": True}, {"available": True, "wireless": False}]},
        "subs",
    )[0] == "mixed"
    assert summarize_pairing({"pairing": "SECRET", "pairingMode": False}) == "inactive"
    assert summarize_pairing({"pairing": 1}) == "unknown"


def test_sensor_never_exposes_serials_and_never_writes():
    speaker = FakeSpeaker(capabilities=("/accessories",))
    sub = BoseAccessoryDiagnosticSensor(speaker, "subs", ACCESSORIES)
    assert sub.native_value == "wired"
    assert sub.unique_id.endswith("accessories_subs_diagnostic")
    assert sub.should_poll is False
    assert not speaker.requests
    assert "PRIVATE_" not in json.dumps(sub.extra_state_attributes)
    # Pushes unrelated to accessories do nothing.
    speaker.notify("/audio/volume", {"value": 30})
    assert sub.native_value == "wired"
    # Pushes can change existing state without any writes.
    speaker.notify("/accessories", {"subs": [{"available": True, "wireless": True}]})
    assert sub.native_value == "wireless"
    assert speaker.requests == []


@pytest.mark.parametrize("mode", ["subs", "rears", "pairing"])
async def test_manual_refresh_get_only(mode):
    speaker = FakeSpeaker(
        capabilities=("/accessories",), values={"/accessories": ACCESSORIES}
    )
    speaker.get_accessories = lambda: speaker._request("/accessories", "GET")
    state = BoseAccessoryDiagnosticSensor(speaker, mode, {})
    await state.async_update()
    assert speaker.requests == [
        {"resource": "/accessories", "method": "GET", "body": None, "checkCapabilities": True}
    ]
    assert state.available is True


async def test_missing_resource_never_adds_diagnostics():
    speaker = FakeSpeaker()
    hass = FakeHass()
    hass.data = {"bose": {"e1": {"speaker": speaker, "coordinator": None, "accessories": ACCESSORIES}}}
    added = []
    await sensor.async_setup_entry(
        hass, SimpleNamespace(entry_id="e1", data={"ip": "fake"}),
        lambda entities, **kwargs: added.extend(entities)
    )
    assert added == []


async def test_setup_uses_only_previous_snapshot_no_requests():
    speaker = FakeSpeaker(capabilities=("/accessories",))
    hass = FakeHass()
    hass.data = {"bose": {"e1": {"speaker": speaker, "coordinator": None, "accessories": ACCESSORIES}}}
    added = []
    await sensor.async_setup_entry(
        hass, SimpleNamespace(entry_id="e1", data={"ip": "fake"}),
        lambda entities, **kwargs: added.extend(entities),
    )
    assert len(added) == 3
    assert {entity.native_value for entity in added} == {"wired", "wireless", "inactive"}
    assert speaker.requests == []
    for entity in added:
        assert not any(value.startswith("PRIVATE") for value in entity.extra_state_attributes.values() if isinstance(value, str))


def test_translation_keys_are_registered():
    root = Path(__file__).resolve().parents[1] / "custom_components/bose"
    for f in (root / "strings.json", root / "translations/en.json"):
        translations = json.loads(f.read_text())
        sensors = translations["entity"]["sensor"]
        assert all(
            f"accessories_{kind}_diagnostic" in sensors
            for kind in ("subs", "rears", "pairing")
        )
