"""Prevent duplicate raw audio writes on errors while preserving working probes."""

from types import SimpleNamespace
import pytest

from bose.number import BoseAudioSlider
from .conftest import FakeSpeaker, FakeCoordinator

def slider(speaker, audio=None, option="bass"):
    entity=BoseAudioSlider(
        speaker,
        SimpleNamespace(data={"ip":"example.invalid"}),
        option,
        audio or {"value":0, "properties":{"min":-10,"max":10,"step":1}},
        FakeCoordinator(speaker),
    )
    return entity

@pytest.mark.asyncio
async def test_advertised_setting_one_high_level_write_only():
    speaker=FakeSpeaker(capabilities=("/audio/bass",),known_options=("bass",))
    ent=slider(speaker)
    await ent.async_set_native_value(3)
    assert ent.native_value == 3
    assert speaker.settings["bass"]==3
    assert speaker.requests==[]  # no direct fallback

@pytest.mark.asyncio
async def test_successful_probed_unadvertised_setting_uses_one_write():
    speaker=FakeSpeaker(known_options=("midrange",))
    ent=slider(speaker,option="midrange")
    await ent.async_set_native_value(-3)
    assert ent.native_value==-3
    assert speaker.requests==[{
        "resource":"/audio/midrange", "method":"POST",
        "body":{"value":-3},"checkCapabilities":False,
    }]

@pytest.mark.asyncio
async def test_network_timeout_is_not_retried_and_state_unchanged():
    speaker=FakeSpeaker(capabilities=("/audio/bass",),known_options=("bass",))
    ent=slider(speaker)
    calls=[]
    async def timeout(*args,**kwargs):
        calls.append(args)
        raise TimeoutError("fake transport timeout")
    speaker.set_audio_setting=timeout
    with pytest.raises(TimeoutError):
        await ent.async_set_native_value(7)
    assert len(calls)==1
    assert ent.native_value==0
    assert speaker.requests==[]

@pytest.mark.asyncio
async def test_failed_unadvertised_write_not_retried():
    speaker=FakeSpeaker()
    ent=slider(speaker)
    calls=[]
    async def fail(*args,**kwargs):
        calls.append(args)
        raise OSError("offline")
    speaker._request=fail
    with pytest.raises(OSError):
        await ent.async_set_native_value(7)
    assert len(calls)==1
    assert ent.native_value==0

@pytest.mark.asyncio
@pytest.mark.parametrize("bad",[True,None,"5",float('nan'),float('inf'),2.5,-11,11,[],{}])
async def test_invalid_setting_no_network_call(bad):
    speaker=FakeSpeaker(capabilities=("/audio/bass",),known_options=("bass",))
    ent=slider(speaker)
    with pytest.raises(ValueError,match="invalid or out of range"):
        await ent.async_set_native_value(bad)
    assert speaker.settings=={}
    assert speaker.requests==[]

@pytest.mark.asyncio
async def test_response_mismatch_rejected_without_false_ui_state():
    speaker=FakeSpeaker(capabilities=("/audio/bass",),known_options=("bass",))
    ent=slider(speaker)
    async def wrong(*args,**kwargs):return {"value":4}
    speaker.set_audio_setting=wrong
    with pytest.raises(ValueError,match="did not confirm"):
        await ent.async_set_native_value(5)
    assert ent.native_value==0


def test_partial_slider_notifications_never_reset_to_zero():
    speaker=FakeSpeaker(capabilities=("/audio/bass",))
    ent=slider(speaker)
    ent._parse_message({"header":{"resource":"/audio/bass"},"body":{"properties":{"min":-20}}})
    assert ent.native_value==0
    ent._parse_audio({"value":6})
    assert ent.native_value==6
    ent._parse_audio({"status":"active"})
    assert ent.native_value==6
    ent._parse_audio({"value":"0"})
    assert ent.native_value==6
    ent._parse_audio({})
    assert ent.native_value==6
