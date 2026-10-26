"""Tests that the HACS lab loads its shipped library, not stale PyPI pybose."""

import json
from pathlib import Path

from bose._pybose.BoseSpeaker import BoseSpeaker


def test_bundled_bose_speaker_exports_local_methods():
    assert BoseSpeaker.__module__ == "bose._pybose.BoseSpeaker"
    for name in (
        "get_audio_format",
        "get_system_update_status",
        "get_universal_remote_pairing_status",
        "start_universal_remote_pairing",
        "stop_universal_remote_pairing",
        "start_accessory_pairing",
        "stop_accessory_pairing",
        "get_optical_auto_wake",
        "set_optical_auto_wake",
        "get_power_sync_status",
    ):
        assert callable(getattr(BoseSpeaker, name))


def test_lab_manifest_does_not_pull_stale_pybose_from_pypi():
    manifest = json.loads(
        (Path(__file__).resolve().parents[1] / "custom_components/bose/manifest.json").read_text()
    )
    assert manifest["version"] == "1.3.10"
    assert not any(req.lower().startswith("pybose") for req in manifest["requirements"])
    assert (Path(__file__).resolve().parents[1] / "custom_components/bose/_pybose/LICENSE").exists()


async def test_bundled_audio_mode_setter_uses_bose_music_put():
    from bose._pybose.BoseAuth import BoseAuth

    auth = BoseAuth()
    auth.set_access_token("fake-access", "fake-refresh", "fake-person")
    speaker = BoseSpeaker(bose_auth=auth, host="example.invalid", device_id="fake")
    requests = []

    async def pretend_request(resource, verb, body=None, **kwargs):
        requests.append((resource, verb, body))
        return {"value": body["value"]}

    speaker._request = pretend_request
    assert await speaker.set_audio_mode("DIALOG") is True
    assert requests == [
        ("/audio/mode", "PUT", {"value": "DIALOG"})
    ]
