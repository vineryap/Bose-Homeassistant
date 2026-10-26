"""Tests for the Bose switch platform."""

from bose.switch import BoseAccessorySwitch, BoseStandbySettingSwitch

from .conftest import FakeHass, FakeSpeaker


def _accessory_switch(speaker):
    entity = BoseAccessorySwitch(
        speaker,
        {"productName": "Test"},
        {"enabled": {"subs": True}},
        None,
        "Subwoofers",
        "subs",
    )
    entity.async_write_ha_state = lambda: None
    return entity


async def _no_answer():
    raise TimeoutError("no response from the speaker within 10 seconds")


async def test_failed_update_goes_unavailable_instead_of_raising():
    """A speaker that does not answer must not break the poll (issue #82)."""
    speaker = FakeSpeaker()
    speaker.get_accessories = _no_answer
    entity = _accessory_switch(speaker)

    await entity.async_update()

    assert not entity.available


async def test_update_recovers_when_the_speaker_answers_again():
    """Availability comes back with the first successful read."""
    speaker = FakeSpeaker()

    async def answers():
        return {"enabled": {"subs": False}}

    speaker.get_accessories = answers
    entity = _accessory_switch(speaker)
    entity._attr_available = False  # noqa: SLF001

    await entity.async_update()

    assert entity.available
    assert entity.is_on is False


async def test_push_restores_availability():
    """A notification proves the speaker is alive again."""
    speaker = FakeSpeaker()
    entity = _accessory_switch(speaker)
    entity._attr_available = False  # noqa: SLF001

    speaker.notify("/accessories", {"enabled": {"subs": True}})

    assert entity.available
    assert entity.is_on is True


async def test_standby_switch_survives_a_failed_update():
    """The standby switch gets the same protection."""
    speaker = FakeSpeaker()
    speaker.get_system_timeout = _no_answer
    entity = BoseStandbySettingSwitch(
        speaker, {"productName": "Test"}, None, FakeHass()
    )
    entity.async_write_ha_state = lambda: None

    await entity.async_update()

    assert not entity.available


async def test_accessory_partial_pairing_notification_does_not_disable_speakers():
    speaker=FakeSpeaker()
    sub=_accessory_switch(speaker)
    assert sub.is_on is True
    speaker.notify("/accessories", {"pairing":True})
    assert sub.is_on is True
    speaker.notify("/accessories", {"enabled":{"rears":False}})
    assert sub.is_on is True
    speaker.notify("/accessories", {"enabled":{"subs":None}})
    assert sub.is_on is True
    speaker.notify("/accessories", {"enabled":{"subs":"false"}})
    assert sub.is_on is True
    speaker.notify("/accessories", {"enabled":{"subs":False}})
    assert sub.is_on is False


async def test_accessory_switch_success_updates_state_only_after_ack():
    speaker=FakeSpeaker()
    sub=_accessory_switch(speaker)
    calls=[]
    async def write(**kwargs):
        calls.append(kwargs)
        return True
    speaker.put_accessories=write
    await sub.async_turn_off()
    assert sub.is_on is False
    await sub.async_turn_on()
    assert sub.is_on is True
    assert calls==[{"subs_enabled":False},{"subs_enabled":True}]


async def test_accessory_switch_rejection_or_timeout_preserves_state():
    import pytest
    speaker=FakeSpeaker()
    sub=_accessory_switch(speaker)
    async def refused(**kwargs):
        return False
    speaker.put_accessories=refused
    with pytest.raises(ValueError,match="refused"):
        await sub.async_turn_off()
    assert sub.is_on is True
    async def offline(**kwargs):
        raise TimeoutError("fake timeout")
    speaker.put_accessories=offline
    with pytest.raises(TimeoutError):
        await sub.async_turn_off()
    assert sub.is_on is True
