"""Opt-in Bose accessory discovery orchestration with a safety preflight.

Bose Music sends PUT /accessories {"pairing": boolean}; the impact of
discovery on currently linked surround speakers has not been live verified.
No pairing can happen without an explicit service call and confirmation.
"""

from __future__ import annotations

from typing import Any

from ._pybose import BoseSpeaker


PAIRING_CONFIRMATION = "I UNDERSTAND THIS MAY INTERRUPT SURROUND SPEAKERS"


def pairing_state(payload: Any) -> bool | None:
    """Return a strictly boolean pairing state, supporting two firmware keys."""
    if not isinstance(payload, dict):
        return None
    for key in ("pairing", "pairingMode"):
        state = payload.get(key)
        if type(state) is bool:
            return state
    return None


async def change_accessory_pairing(
    speaker: BoseSpeaker,
    *,
    start: bool,
    confirmation: str | None = None,
) -> str:
    """Start/cancel pairing explicitly, refusing unknown state or capabilities.

    Only this callable is permitted to invoke paired-state writes in HACS.
    A caller must deliberately request an operation; no update or startup path
    invokes it. Hardware effects are still unverified.
    """
    if type(start) is not bool:
        raise ValueError("Pairing operation must be a boolean")
    if start and confirmation != PAIRING_CONFIRMATION:
        raise ValueError("Explicit accessory-discovery confirmation is required")
    if not speaker.has_capability("/accessories"):
        raise ValueError("This speaker does not advertise /accessories")

    snapshot = await speaker.get_accessories()
    state = pairing_state(snapshot)
    if state is None:
        raise ValueError("Pairing state unknown; refusing to send accessory write")
    if state == start:
        return "Accessory pairing already active" if start else "Accessory pairing already inactive"

    if start:
        await speaker.start_accessory_pairing()
        return "Accessory discovery request submitted"
    await speaker.stop_accessory_pairing()
    return "Accessory discovery cancellation submitted"
