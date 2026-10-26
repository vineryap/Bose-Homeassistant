"""Auto Standby must not clobber the other power timeout setting."""

import pytest
from bose.switch import BoseStandbySettingSwitch
from .conftest import FakeHass, FakeSpeaker


def standby(speaker):
    entity=BoseStandbySettingSwitch(
        speaker, {"productName":"Test"}, None, FakeHass()
    )
    entity.async_write_ha_state=lambda:None
    return entity


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("requested","original_video"),[(True,True),(False,True),(True,False),(False,False)]
)
async def test_standby_change_preserves_video_timeout(requested,original_video):
    speaker=FakeSpeaker()
    calls=[]
    async def getter():
        calls.append(("GET",))
        return {"noAudio":not requested,"noVideo":original_video}
    async def setter(no_audio,no_video):
        calls.append(("PUT",no_audio,no_video))
        return {"noAudio":no_audio,"noVideo":no_video}
    speaker.get_system_timeout=getter
    speaker.set_system_timeout=setter
    entity=standby(speaker)
    if requested:
        await entity.async_turn_on()
    else:
        await entity.async_turn_off()
    assert calls==[("GET",),("PUT",requested,original_video)]
    assert entity.is_on is requested


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid",[
    {}, {"noAudio":True}, {"noAudio":True,"noVideo":None},
    {"noAudio":True,"noVideo":"false"},{"noAudio":1,"noVideo":True},None,
])
async def test_unknown_timeout_refuses_any_write(invalid):
    speaker=FakeSpeaker()
    calls=[]
    async def getter():return invalid
    async def setter(*args):
        calls.append(args)
    speaker.get_system_timeout=getter
    speaker.set_system_timeout=setter
    entity=standby(speaker)
    with pytest.raises(ValueError,match="timeout state"):
        await entity.async_turn_off()
    assert calls==[]


@pytest.mark.asyncio
async def test_standby_noop_when_state_already_matches():
    speaker=FakeSpeaker()
    calls=[]
    async def getter():return {"noAudio":True,"noVideo":True}
    async def setter(*args):calls.append(args)
    speaker.get_system_timeout=getter
    speaker.set_system_timeout=setter
    entity=standby(speaker)
    await entity.async_turn_on()
    assert calls==[]


@pytest.mark.asyncio
async def test_standby_timeout_does_not_retry_or_change_ui():
    speaker=FakeSpeaker()
    calls=[]
    async def getter():return {"noAudio":False,"noVideo":True}
    async def setter(*args):
        calls.append(args)
        raise TimeoutError("fake timeout")
    speaker.get_system_timeout=getter
    speaker.set_system_timeout=setter
    entity=standby(speaker)
    await entity.async_update()
    assert entity.is_on is False
    with pytest.raises(TimeoutError):
        await entity.async_turn_on()
    assert len(calls)==1
    assert entity.is_on is False


@pytest.mark.asyncio
async def test_standby_mismatched_ack_no_false_ui():
    speaker=FakeSpeaker()
    async def getter():return {"noAudio":False,"noVideo":True}
    async def setter(*args):return {"noAudio":False,"noVideo":True}
    speaker.get_system_timeout=getter
    speaker.set_system_timeout=setter
    entity=standby(speaker)
    await entity.async_update()
    with pytest.raises(ValueError,match="confirm"):
        await entity.async_turn_on()
    assert entity.is_on is False


@pytest.mark.asyncio
async def test_partial_standby_push_preserves_current_value():
    speaker=FakeSpeaker()
    async def getter():return {"noAudio":True,"noVideo":False}
    speaker.get_system_timeout=getter
    entity=standby(speaker)
    await entity.async_update()
    assert entity.is_on is True
    speaker.notify("/system/power/timeouts",{"noVideo":True})
    assert entity.is_on is True
    speaker.notify("/system/power/timeouts",{"noAudio":"false"})
    assert entity.is_on is True
    speaker.notify("/system/power/timeouts",{"noAudio":False})
    assert entity.is_on is False
