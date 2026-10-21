# Bose HACS v1.3.7 — Experimental Soundbar 700 testing build

This release is from the owner's **unofficial test fork**. It is not a
release from the original Bose Home Assistant maintainer.

## New since v1.3.6

- Three read-only accessory diagnostics: bass module connection type,
  surround-speaker connection type, and accessory pairing status. Accessory
  serials, MAC addresses and tokens are not displayed in these sensors.
- Experimental start/cancel accessory-discovery services. Starting requires
  exact typed confirmation, live GET preflight and capability check; the
  services serialize concurrent requests and refuse stale/reconnected
  connections. **Hardware behavior remains unverified.** Do not test pairing
  just to test the release if existing wireless surrounds are important.
- Soundbar Audio Mode read-only diagnostic sensor (uses `GET /audio/mode`).
- Soundbar Firmware Update Status read-only diagnostic sensor (uses
  `GET /system/update/status`). This sensor NEVER initiates updates.
- Optical Auto-Wake explicit, reversible switch (uses `GET` and, only on
  user toggle, `PUT /system/power/mode/opticalAutoWake` with
  `{"enabled": boolean}`). No setting changes on installation or HA startup.
- Bundled pybose includes all prior patches and the verified Android-app
  request shapes for opt-in accessory discovery and optical auto-wake.

## Limitations and testing

**No full digital TV/IR navigation remote.** The Bose 700 advertises
`/injectKey`, but the payload and accepted key codes are undocumented.
No guessed key commands are included.

**Do not attempt wireless pairing of a Japan-market Bass Module 700 solely
to test this integration.** Its radio feature may be disabled/missing,
and the effect of entering accessory pairing mode on existing wireless
surrounds is unknown.

Backup Home Assistant first, update the existing
[vineryap/Bose-Homeassistant](https://github.com/vineryap/Bose-Homeassistant)
HACS custom repository to version `1.3.7`, then restart Home Assistant.
Review the [updated safe test and rollback instructions](../LAB_TESTING.md)
and [specific new sensor/switch instructions](soundbar-status-v137.md).

## Validation

- **90 HACS mocked tests passed**.
- **163 combined pybose mocked tests passed**.
- Python source compiled successfully.
- **No live Bose soundbar, bass module, surround speaker or HA instance was
  touched by development or automated tests.**

To roll back, reinstall **v1.3.6** in HACS and restart HA, or restore the
saved integration from a backup.
