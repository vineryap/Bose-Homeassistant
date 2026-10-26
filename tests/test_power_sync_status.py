"""Read-only Power Sync sensor: body sanitized; no write commands."""
from types import SimpleNamespace
import pytest
from bose import sensor
from bose.soundbar_diagnostics import status_value, BoseSoundbarStatusSensor
from .conftest import FakeHass, FakeSpeaker

def test_power_sync_status_uses_only_boolean_enabled():
    assert status_value({"enabled":True, "powerOnDevice":"PRIVATE-DEVICE-ID"},"power_sync")=="enabled"
    assert status_value({"enabled":False, "powerOnDevice":"PRIVATE-DEVICE-ID"},"power_sync")=="disabled"
    for body in ({},{"enabled":"true"},{"enabled":1},{"powerOnDevice":"PRIVATE-DEVICE-ID"},None):
        assert status_value(body,"power_sync")=="unknown"

@pytest.mark.asyncio
async def test_power_sync_sensor_get_and_push_are_read_only():
    speaker=FakeSpeaker(capabilities=("/system/power/macro",))
    calls=[]
    async def get():
        calls.append("GET")
        return {"enabled":True, "powerOnDevice":"PRIVATE-DEVICE-ID", "powerOnTv":False}
    speaker.get_power_sync_status=get
    entity=BoseSoundbarStatusSensor(speaker, "power_sync")
    assert entity.native_value=="unknown"
    await entity.async_update()
    assert entity.native_value=="enabled"
    assert calls==["GET"] and not speaker.requests
    speaker.notify("/system/power/macro", {"enabled":False,"powerOnDevice":"PRIVATE-DEVICE-ID"})
    assert entity.native_value=="disabled"
    assert entity.should_poll is False
    assert "PRIVATE" not in str(entity.extra_state_attributes)

@pytest.mark.asyncio
async def test_power_sync_sensor_is_capability_gated():
    speaker=FakeSpeaker(capabilities=("/system/power/macro",))
    hass=FakeHass()
    hass.data={"bose":{"a":{"speaker":speaker,"coordinator":None,"accessories":{}}}}
    added=[]
    await sensor.async_setup_entry(
        hass,SimpleNamespace(entry_id="a",data={"ip":"fake"}),
        lambda entities,**kwargs:added.extend(entities),
    )
    assert [ent._mode for ent in added]==["power_sync"]
    assert not speaker.requests

@pytest.mark.asyncio
async def test_power_sync_failure_reports_unavailable():
    speaker=FakeSpeaker()
    entity=BoseSoundbarStatusSensor(speaker, "power_sync")
    async def get():
        raise TimeoutError("fake failure")
    speaker.get_power_sync_status=get
    await entity.async_update()
    assert entity.available is False

@pytest.mark.asyncio
async def test_bundled_library_uses_exact_read_only_resource():
    from bose._pybose.BoseAuth import BoseAuth
    from bose._pybose.BoseSpeaker import BoseSpeaker

    auth=BoseAuth()
    auth.set_access_token("synthetic","synthetic-refresh","synthetic-user")
    speaker=BoseSpeaker(bose_auth=auth,host="fake.invalid",device_id="fake")
    calls=[]
    async def fake_request(resource,method,body=None,**kwargs):
        calls.append((resource,method,body))
        return {"enabled":True,"powerOnDevice":"PRIVATE-ID","powerOnTv":False}
    speaker._request=fake_request
    result=await speaker.get_power_sync_status()
    assert result["enabled"] is True
    assert calls==[("/system/power/macro","GET",None)]
