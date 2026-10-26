"""Contract and fail-closed behaviour for a Power Sync master switch."""

import asyncio
from types import SimpleNamespace

import pytest

from bose import switch
from bose.power_sync import BosePowerSyncSwitch, read_power_sync
from .conftest import FakeHass, FakeSpeaker

RESOURCE = "/system/power/macro"


def speaker():
    return FakeSpeaker(capabilities=(RESOURCE,))


def entity_for(s):
    entity = BosePowerSyncSwitch(s)
    entity.async_write_ha_state = lambda: None
    return entity


@pytest.mark.parametrize("bad", [
    None, [], {}, {"enabled": False},
    {"enabled": False, "powerOnTv": False},
    {"enabled": False, "powerOnDevice": "TV"},
    {"enabled": 0, "powerOnDevice": "TV", "powerOnTv": False},
    {"enabled": False, "powerOnDevice": None, "powerOnTv": False},
    {"enabled": False, "powerOnDevice": "TV", "powerOnTv": "false"},
    {"enabled": False, "powerOnDevice": "X" * 1025, "powerOnTv": False},
])
def test_incomplete_power_sync_cannot_authorise_write(bad):
    assert read_power_sync(bad) is None


@pytest.mark.asyncio
async def test_initialisation_is_read_only_and_opt_in():
    s = speaker()
    calls = []
    async def getter():
        calls.append("GET")
        return {"enabled": False, "powerOnDevice": "synthetic-device", "powerOnTv": True}
    s.get_power_sync_status = getter
    s.set_power_sync = lambda **kw: pytest.fail("write not permitted during setup")
    ent = entity_for(s)
    assert ent.available is False
    await ent.async_update()
    assert ent.is_on is False
    assert ent.available
    assert calls == ["GET"]
    assert not s.requests
    assert "synthetic-device" not in str(ent.extra_state_attributes)


@pytest.mark.asyncio
async def test_turn_on_then_off_preserves_every_other_field():
    s = speaker()
    data = {"enabled": False, "powerOnDevice": "DEVICE-PRIVATE", "powerOnTv": True}
    calls = []
    async def getter():
        calls.append(("GET",))
        return data.copy()
    async def setter(**kwargs):
        calls.append(("PUT", kwargs.copy()))
        data.update({
            "enabled": kwargs["enabled"],
            "powerOnTv": kwargs["power_on_tv"],
            "powerOnDevice": kwargs["power_on_device"],
        })
        return data.copy()
    s.get_power_sync_status = getter
    s.set_power_sync = setter
    ent = entity_for(s)
    await ent.async_update()
    calls.clear()
    await ent.async_turn_on()
    assert ent.is_on is True
    assert calls == [("GET",), ("PUT", {
        "enabled": True, "power_on_device": "DEVICE-PRIVATE", "power_on_tv": True,
    }), ("GET",)]
    calls.clear()
    await ent.async_turn_off()
    assert ent.is_on is False
    assert calls == [("GET",), ("PUT", {
        "enabled": False, "power_on_device": "DEVICE-PRIVATE", "power_on_tv": True,
    }), ("GET",)]


@pytest.mark.asyncio
async def test_same_requested_state_avoids_write():
    s = speaker()
    calls = []
    async def getter():
        calls.append("GET")
        return {"enabled": False, "powerOnDevice": "", "powerOnTv": False}
    async def setter(**kwargs):
        pytest.fail("should be no PUT for same value")
    s.get_power_sync_status = getter
    s.set_power_sync = setter
    ent = entity_for(s)
    await ent.async_turn_off()
    assert calls == ["GET"]
    assert ent.is_on is False


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [
    {"enabled": False},
    {"enabled": False, "powerOnDevice": "id"},
    {"enabled": "false", "powerOnDevice": "id", "powerOnTv": False},
])
async def test_incomplete_get_refuses_write(bad):
    s = speaker()
    async def getter(): return bad
    async def setter(**kwargs): pytest.fail("cannot write without all fields")
    s.get_power_sync_status = getter
    s.set_power_sync = setter
    ent = entity_for(s)
    with pytest.raises(ValueError, match="Incomplete"):
        await ent.async_turn_on()
    assert not ent.available


@pytest.mark.asyncio
async def test_get_timeout_refuses_write():
    s = speaker()
    async def getter(): raise TimeoutError("synthetic disconnect")
    async def setter(**kwargs): pytest.fail("cannot write if GET fails")
    s.get_power_sync_status = getter
    s.set_power_sync = setter
    ent = entity_for(s)
    with pytest.raises(ValueError, match="Cannot read"):
        await ent.async_turn_on()
    assert not ent.available


@pytest.mark.asyncio
async def test_write_timeout_never_retried_or_claimed_success():
    s = speaker()
    calls = []
    async def getter():
        return {"enabled": False, "powerOnDevice": "", "powerOnTv": True}
    async def setter(**kwargs):
        calls.append(kwargs)
        raise TimeoutError("synthetic timeout after possible application")
    s.get_power_sync_status = getter
    s.set_power_sync = setter
    ent = entity_for(s)
    with pytest.raises(TimeoutError):
        await ent.async_turn_on()
    assert len(calls) == 1
    assert not ent.available
    assert ent.is_on is None


@pytest.mark.asyncio
@pytest.mark.parametrize("after", [
    {"enabled": False, "powerOnDevice": "private", "powerOnTv": False},
    {"enabled": True, "powerOnDevice": "different", "powerOnTv": False},
    {"enabled": True, "powerOnDevice": "private", "powerOnTv": True},
    {"enabled": True},
])
async def test_readback_mismatch_or_missing_field_fails_closed(after):
    s = speaker()
    calls = []
    async def getter():
        calls.append("GET")
        return (
            {"enabled": False, "powerOnDevice": "private", "powerOnTv": False}
            if len(calls) == 1 else after
        )
    async def setter(**kwargs): calls.append("PUT")
    s.get_power_sync_status = getter
    s.set_power_sync = setter
    ent = entity_for(s)
    with pytest.raises(ValueError, match="could not be verified"):
        await ent.async_turn_on()
    assert calls == ["GET", "PUT", "GET"]
    assert not ent.available


@pytest.mark.asyncio
async def test_serialises_concurrent_turn_on_requests():
    s = speaker()
    barrier = asyncio.Event()
    data = {"enabled": False, "powerOnDevice": "device", "powerOnTv": False}
    calls = []
    async def getter():
        calls.append("GET")
        return data.copy()
    async def setter(**kwargs):
        calls.append("PUT")
        await barrier.wait()
        data["enabled"] = kwargs["enabled"]
    s.get_power_sync_status = getter
    s.set_power_sync = setter
    ent = entity_for(s)
    first = asyncio.create_task(ent.async_turn_on())
    await asyncio.sleep(0)
    second = asyncio.create_task(ent.async_turn_on())
    await asyncio.sleep(0)
    assert calls == ["GET", "PUT"]
    barrier.set()
    await asyncio.gather(first, second)
    assert calls == ["GET", "PUT", "GET", "GET"]
    assert ent.is_on is True


@pytest.mark.asyncio
async def test_partial_notification_does_not_enable_new_control():
    s = speaker()
    ent = entity_for(s)
    s.notify(RESOURCE, {"enabled": False})
    assert not ent.available
    s.notify(RESOURCE, {"enabled": False, "powerOnDevice": "", "powerOnTv": False})
    assert ent.available and ent.is_on is False
    s.notify(RESOURCE, {"enabled": True})
    assert ent.is_on is False


@pytest.mark.asyncio
async def test_setup_adds_config_control_only_for_advertised_capability():
    s = speaker()
    hass = FakeHass()
    hass.data = {"bose": {"entry": {
        "speaker": s, "system_info": {}, "accessories": {},
    }}}
    added = []
    await switch.async_setup_entry(
        hass,
        SimpleNamespace(entry_id="entry", data={}),
        lambda entities, **kwargs: added.extend(entities),
    )
    assert [type(e).__name__ for e in added] == ["BosePowerSyncSwitch"]
    assert not s.requests


@pytest.mark.asyncio
async def test_vendored_pybose_power_sync_has_exact_bose_music_payload():
    from bose._pybose.BoseAuth import BoseAuth
    from bose._pybose.BoseSpeaker import BoseSpeaker
    auth = BoseAuth()
    auth.set_access_token("synthetic", "synthetic-refresh", "synthetic-person")
    device = BoseSpeaker(bose_auth=auth, host="fake.invalid", device_id="fake")
    requests = []
    async def request(resource, method, body=None, **kwargs):
        requests.append((resource, method, body))
        return {"enabled": True}
    device._request = request
    await device.set_power_sync(True, "synthetic-device", False)
    assert requests == [(
        "/system/power/macro", "PUT",
        {"enabled": True, "powerOnDevice": "synthetic-device", "powerOnTv": False},
    )]
