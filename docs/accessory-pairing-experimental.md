# Experimental Bose bass/surround accessory discovery

**Status:** LOCAL DEVELOPMENT ONLY. This feature lives on the local branch
`feature/accessory-pairing-experimental` (based on the read-only diagnostics branch).
**It is not in public HACS release `v1.3.6`.** The published version and the user's
installed Home Assistant are unchanged.

## Proven command format, unverified effect

Original Bose Music APK (classes4.dex) serializes pairing requests through
`AccessoriesPairingRequestGson`; the application's typed resource registry
maps type **30101** to **`/accessories`** at version **1.0**.
It issues **`PUT /accessories`** with a JSON body:

- `{"pairing": true}` to start discovery.
- `{"pairing": false}` to cancel discovery.

These commands are separate from Bose audio Bluetooth pairing and BLE Universal
Remote pairing. **No live test has established whether accessory discovery could
interrupt, reassign or unlink already-connected surround speakers.**

## Local code

- `pybose` independent branch `feature/accessory-pairing` at commit `e0ba9d6`.
- `pybose` combined local test branch `local/bose-testing` at commit `9357858`
  includes this additional patch with the prior five changes.
- HACS vendor copy includes those same six patches; action implementation
  `custom_components/bose/accessory_pairing.py` is opt-in only.
- Existing read-only sensors for sub/rear transport and pairing status remain available.

**Automatic startup, polling, device discovery or a dashboard button never calls
the state-changing library methods.**

## Experimental actions (only after explicit permission)

The current development branch declares:

- `bose.start_accessory_pairing`: requires **soundbar** device ID and an exact
  confirmation text: `I UNDERSTAND THIS MAY INTERRUPT SURROUND SPEAKERS`.
- `bose.stop_accessory_pairing`: requires soundbar device ID; cancels an active
  session but refuses if read-only pairing state is unknown.

Both actions check speaker's `/accessories` capability, read `GET /accessories`,
and suppress redundant state-changing PUTs. The guard recognizes either
`pairing` (observed in the owner's response) or `pairingMode` (Android DTO).
Missing or malformed status blocks write.

### Concurrency and status propagation safeguards

Pairing services use a lock per Bose configuration entry, so simultaneous
Start/Stop requests cannot overlap their status-read/write cycles.
Reconnection during the status preflight refuses to write to a stale speaker.

After an acknowledged Start or Stop, a 15-second same-speaker grace window
remembers the requested state. It suppresses duplicate Starts when firmware
reports delayed status updates, but allows deliberate Stop immediately.
A new speaker connection invalidates this remembered state. All Start calls
still require exact confirmation.

This is an **in-memory safety guard**, not a radio-level idempotency guarantee.
If a speaker accepts a write but the response is lost, its actual state can
remain uncertain; no retry or automatic pairing occurs.

The generic `bose.send_custom_request` service still permits raw writes. An
advanced user can bypass these experimental service safeguards intentionally;
this is not recommended for accessory pairing.

### No live execution yet

The user already tried Bose Music's normal discovery repeatedly, and the Japan
Bass Module 700 appears permanently wired. There is **no compelling reason to
risk both working wireless surround speakers solely to validate the HACS button**.

A future opt-in test must preserve the starting `/accessories` snapshot, include
immediate cancellation and a wired fallback for the sub, and be performed only
when the user accepts possible surround reconnection work. The HACS service
registration itself does not start pairing.

## Offline acceptance tests

- Independent pybose base branch: **130 unit tests passing**.
- Combined pybose local branch: **153 unit tests passing**.
- HACS experimental branch: **78 offline tests passing** (read-only diagnostics
  +20 dedicated start/stop, confirmation, concurrency and reconnection tests).
- Simulated no-op behavior on already active/inactive state.
- Rejection of mismatched confirmation text, unsupported capability and
  malformed pairing state before any PUT.
- Mocked existing connected rears; no unintended automatic requests.
- No live hardware, Bose cloud, or installed Home Assistant touched.

For production, prefer upstream separate pybose PRs, then an optional released
HACS integration update; do not put this experimental branch into production
before an owner-approved test.
