"""Safety checks for the deliberately opt-in Bose accessory pairing services."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from bose import setup
from bose.accessory_pairing import (
    PAIRING_CONFIRMATION,
    change_accessory_pairing,
    pairing_state,
)


class FakeAccessorySpeaker:
    """Only simulated calls; no socket or Bose account exists."""

    def __init__(self, state=False, advertised=True):
        self.state = state
        self.advertised = advertised
        self.calls = []

    def has_capability(self, resource):
        self.calls.append(("capability", resource))
        return self.advertised and resource == "/accessories"

    async def get_accessories(self):
        self.calls.append(("GET", "/accessories"))
        return {"pairing": self.state, "rears": [
            {"available": True, "wireless": True, "serialnum": "SECRET_A"},
            {"available": True, "wireless": True, "serialnum": "SECRET_B"},
        ]}

    async def start_accessory_pairing(self):
        self.calls.append(("PUT", "/accessories", {"pairing": True}))

    async def stop_accessory_pairing(self):
        self.calls.append(("PUT", "/accessories", {"pairing": False}))


def test_pairing_state_accepts_original_and_live_field_names():
    assert pairing_state({"pairing": False}) is False
    assert pairing_state({"pairingMode": True}) is True
    assert pairing_state({"pairing": True, "pairingMode": False}) is True
    assert pairing_state({"pairing": "false"}) is None
    assert pairing_state(None) is None


@pytest.mark.asyncio
async def test_start_with_exact_confirmation_and_two_connected_surrounds():
    speaker = FakeAccessorySpeaker()
    outcome = await change_accessory_pairing(
        speaker, start=True, confirmation=PAIRING_CONFIRMATION
    )
    assert outcome == "Accessory discovery request submitted"
    assert speaker.calls == [
        ("capability", "/accessories"),
        ("GET", "/accessories"),
        ("PUT", "/accessories", {"pairing": True}),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "confirmation",
    [None, "", "yes", "I UNDERSTAND THIS MAY INTERRUPT SURROUND SPEAKER"],
)
async def test_start_rejects_missing_or_bad_confirmation_without_read_or_write(confirmation):
    speaker = FakeAccessorySpeaker()
    with pytest.raises(ValueError, match="confirmation"):
        await change_accessory_pairing(speaker, start=True, confirmation=confirmation)
    assert speaker.calls == []


@pytest.mark.asyncio
async def test_unsupported_speaker_never_reads_or_writes():
    speaker = FakeAccessorySpeaker(advertised=False)
    with pytest.raises(ValueError, match="does not advertise"):
        await change_accessory_pairing(
            speaker, start=True, confirmation=PAIRING_CONFIRMATION
        )
    assert speaker.calls == [("capability", "/accessories")]


@pytest.mark.asyncio
@pytest.mark.parametrize("start,state", [(True, True), (False, False)])
async def test_idempotent_pairing_does_not_send_write(start, state):
    speaker = FakeAccessorySpeaker(state=state)
    result = await change_accessory_pairing(
        speaker, start=start, confirmation=PAIRING_CONFIRMATION
    )
    assert "already" in result
    assert not [call for call in speaker.calls if call[0] == "PUT"]


@pytest.mark.asyncio
async def test_cancel_active_pairing_only():
    speaker = FakeAccessorySpeaker(state=True)
    assert await change_accessory_pairing(speaker, start=False) == (
        "Accessory discovery cancellation submitted"
    )
    assert speaker.calls[-1] == ("PUT", "/accessories", {"pairing": False})


@pytest.mark.asyncio
async def test_unknown_pairing_status_refuses_to_write():
    speaker = FakeAccessorySpeaker()

    async def read_bad_status():
        speaker.calls.append(("GET", "/accessories"))
        return {"pairing": "UNKNOWN", "serialnum": "SECRET"}

    speaker.get_accessories = read_bad_status
    with pytest.raises(ValueError, match="state unknown"):
        await change_accessory_pairing(
            speaker, start=True, confirmation=PAIRING_CONFIRMATION
        )
    assert not [call for call in speaker.calls if call[0] == "PUT"]


@pytest.mark.asyncio
async def test_invalid_operation_type_no_io():
    speaker = FakeAccessorySpeaker()
    with pytest.raises(ValueError, match="boolean"):
        await change_accessory_pairing(speaker, start="yes", confirmation=PAIRING_CONFIRMATION)
    assert speaker.calls == []


@pytest.mark.asyncio
async def test_services_are_registered_without_touching_speaker(monkeypatch):
    """Test HA wiring and preflight, rather than only pure helper methods."""
    speaker = FakeAccessorySpeaker(state=False)
    actions = {}

    class Services:
        def register(self, domain, action, handler, **kwargs):
            actions[(domain, action)] = handler

    device = SimpleNamespace(primary_config_entry="cfg-1")
    registry = SimpleNamespace(
        async_get=lambda device_id: device if device_id in ("soundbar", "bass_module") else None
    )
    monkeypatch.setattr("bose.dr.async_get", lambda hass: registry)
    hass = SimpleNamespace(
        services=Services(),
        data={"bose": {"cfg-1": {"speaker": speaker, "speaker_ha_device_id": "soundbar"}}},
    )
    assert setup(hass, {}) is True
    assert speaker.calls == []
    assert ("bose", "start_accessory_pairing") in actions
    assert ("bose", "stop_accessory_pairing") in actions

    start = actions[("bose", "start_accessory_pairing")]
    with pytest.raises(ValueError, match="confirmation"):
        await start(SimpleNamespace(data={"device_id": "soundbar"}))
    assert speaker.calls == []

    with pytest.raises(ValueError, match="not found"):
        await start(
            SimpleNamespace(data={
                "device_id": "other",
                "confirmation": PAIRING_CONFIRMATION,
            })
        )
    assert speaker.calls == []

    # Selecting a connected bass-module device must NOT retarget the request.
    with pytest.raises(ValueError, match="not a Bose accessory"):
        await start(SimpleNamespace(data={
            "device_id": "bass_module",
            "confirmation": PAIRING_CONFIRMATION,
        }))
    assert speaker.calls == []

    await start(SimpleNamespace(data={
        "device_id": "soundbar",
        "confirmation": PAIRING_CONFIRMATION,
    }))
    assert speaker.calls[-1] == ("PUT", "/accessories", {"pairing": True})

    speaker.state = True
    await actions[("bose", "stop_accessory_pairing")](
        SimpleNamespace(data={"device_id": "soundbar"})
    )
    assert speaker.calls[-1] == ("PUT", "/accessories", {"pairing": False})


def test_service_descriptors_require_explicit_confirmation():
    root = Path(__file__).resolve().parents[1]
    services = yaml.safe_load(
        (root / "custom_components/bose/services.yaml").read_text()
    )
    assert services["start_accessory_pairing"]["fields"]["confirmation"]["required"] is True
    assert "start_accessory_pairing" in services
    assert "stop_accessory_pairing" in services
