# Soundbar 700 diagnostics and optical auto-wake (owner test fork v1.3.7)

This experimental fork adds three user-visible entities, in addition to the
already available audio-format attribute and read-only accessory status.

## 1. Soundbar Audio Mode (read-only diagnostic sensor)

Uses existing `pybose.get_audio_mode()`, which performs `GET /audio/mode`.
The Bose Music Android app independently identifies this endpoint for
dialogue-related mode changes. The sensor displays the response's `value`
only if it is a short alphanumeric enum-like token; never exports its
`properties` or other metadata. UI does not provide a new mode setter.

## 2. Soundbar Firmware Update Status (read-only diagnostic sensor)

Uses existing `pybose.get_system_update_status()`, `GET /system/update/status`.
It recognizes short `status` / `state` / `phase` / `updateState` text codes
or `updateAvailable` / `available` booleans and otherwise displays `unknown`.
It never initiates a firmware check/download/update or exposes an unbounded
raw response with identifiers or URLs. Firmware-specific schema is
unverified on the owner's Soundbar 700; 'unknown' is a valid safe fallback.

## 3. Optical Auto-Wake (explicit configuration switch)

The Bose Music APK identifies `/system/power/mode/opticalAutoWake` resource
and an opt-in `PUT {"enabled": boolean}` update. The switch performs a
read-only `GET` at integration setup to establish its initial state.
If GET fails or returns no boolean `enabled`, switch stays unavailable and
**refuses to write**. On explicit user toggle, sends exactly one validated
`PUT`, never on startup. Reports a mismatch if the response explicitly
returns the opposite enabled value. The setting affects optical wake behavior,
not wireless pairing or soundbar firmware.

Both GET and PUT are backed by **mock tests**, not live device evidence.

## Suggested owner tests, ordered

1. Back up HA and record the old fork version and Bose entity names.
2. Update HACS owner fork v1.3.7 and restart HA during a quiet time.
3. Check the new **Soundbar Audio Mode** and **Soundbar Firmware Update Status**
   sensor entities. If a sensor says `unknown` or unavailable, report that
   result; do not send raw or state-changing commands to investigate.
4. Check **Optical Auto-Wake** switch initial state via GET. If available,
   optionally toggle once and restore the original state afterwards, observing
   whether the Bose app displays the same value. **Skip toggling if the setting
   is involved in your everyday TV workflow or there is no convenient
   opportunity to restore it.**
5. Review the Bass Module and Surround Speakers connection sensors; expect
   wired bass and wireless rears based on the previous sanitized snapshot.
6. **Do not test Start Accessory Pairing just to validate this release.**
   The effects on the two already-connected wireless surround speakers are
   unknown. The soundbar's JP bass module has never become detectable and
   HACS pairing is unlikely to resolve that by itself.

No full TV directional/IR remote, new RadioAct overrides, firmware update
operations, factory reset or SERVICE port communications are implemented.

## Rollback

Reinstall the previous v1.3.6 HACS owner-fork release and restart, or restore
your HA backup if the integration no longer loads. Never delete the Bose
configuration entry merely to change the fork version.
