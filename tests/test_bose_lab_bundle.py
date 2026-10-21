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
    ):
        assert callable(getattr(BoseSpeaker, name))


def test_lab_manifest_does_not_pull_stale_pybose_from_pypi():
    manifest = json.loads(
        (Path(__file__).resolve().parents[1] / "custom_components/bose/manifest.json").read_text()
    )
    assert manifest["version"] == "1.3.7"
    assert not any(req.lower().startswith("pybose") for req in manifest["requirements"])
    assert (Path(__file__).resolve().parents[1] / "custom_components/bose/_pybose/LICENSE").exists()
