"""Prove the actual vendored pybose library preserves paired surround state."""

import pytest
from bose._pybose.BoseAuth import BoseAuth
from bose._pybose.BoseSpeaker import BoseSpeaker

def make_speaker():
    auth=BoseAuth()
    auth.set_access_token("fake-token","fake-refresh","fake-user")
    return BoseSpeaker(bose_auth=auth,host="fake.invalid",device_id="fake-device")

@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("bass","rear","expected"),[
        (False,None,{"subs":False,"rears":True}),
        (None,False,{"subs":True,"rears":False}),
        (True,None,{"subs":True,"rears":True}),
    ]
)
async def test_actual_bundled_library_preserves_other_accessory(bass,rear,expected):
    speaker=make_speaker()
    async def getter():return {"enabled":{"subs":True,"rears":True}}
    calls=[]
    async def request(resource,verb,body=None,**kwargs):
        calls.append((resource,verb,body))
        return True
    speaker.get_accessories=getter
    speaker._request=request
    assert await speaker.put_accessories(subs_enabled=bass,rears_enabled=rear) is True
    assert calls==[("/accessories","PUT",{"enabled":expected})]

@pytest.mark.asyncio
async def test_actual_bundled_library_blocks_ambiguous_status():
    speaker=make_speaker()
    async def getter():return {"enabled":{"subs":True}}
    async def unexpected(*args,**kwargs):
        raise AssertionError("must not write")
    speaker.get_accessories=getter
    speaker._request=unexpected
    with pytest.raises(ValueError,match="rears status unknown"):
        await speaker.put_accessories(subs_enabled=False)
