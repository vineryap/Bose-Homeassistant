# Bose Soundbar 700 — temporary HACS test build

Test fork: https://github.com/vineryap/Bose-Homeassistant
Original: https://github.com/cavefire/Bose-Homeassistant
Integration version: 1.3.12.

This fork BUNDLES locally tested pybose source at commit b91811f in custom_components/bose/_pybose:
token log redaction, physical remote pairing helpers, audio format getter, extended audio settings, read-only firmware update status, opt-in accessory pairing, and optical auto-wake read/write helpers.
The normal upstream pybose pip dependency is removed to avoid loading its unmodified version.

**New HACS features since v1.3.6:** three read-only accessory connection/pairing sensors; explicit and confirmation-gated accessory pairing start/stop services (not hardware-tested); a read-only Soundbar Audio Mode sensor, a read-only Firmware Update Status sensor; and an explicit Optical Auto-Wake switch. Optical auto-wake is not changed on install or restart. No firmware update/start action is exposed by these new sensors.

This is a temporary test build, not an upstream release or cloud-independent Bose authentication.

## Backup and install

1. Create a FULL Home Assistant backup from Settings > System > Backups and download it. Record your existing Bose integration version and media_player entity IDs. Prefer a time the soundbar is not actively being used.
2. In HACS, go to Custom repositories and add https://github.com/vineryap/Bose-Homeassistant as category Integration.
3. The fork uses the SAME domain 'bose' as the upstream custom integration. You CANNOT run both in one HA. If HACS reports a duplicate, remove the UPSTREAM HACS installation/repository first (do not delete the Bose device/configuration entry from Devices & Services), then install the fork.
4. Install/redownload the fork. Confirm /config/custom_components/bose/manifest.json shows version 1.3.12 AND /config/custom_components/bose/_pybose/BoseSpeaker.py exists. If either check fails, STOP.
5. Restart Home Assistant. Check Settings > Devices & Services > Bose, existing media_player and Bose entities, then Settings > System > Logs for errors. Normal connection/auth may use Bose cloud services for token refresh.

If HACS will not install the fork due to version/source conflicts, an alternative after a FULL BACKUP is to replace the ENTIRE /config/custom_components/bose folder with custom_components/bose from this fork, restart, and inspect logs. Do not mix old/new files.

## Safe live tests you can personally run (READ-ONLY FIRST)

Open Home Assistant Developer Tools > Actions, choose bose.send_custom_request, select the Bose device, set method GET, and test ONE route at a time:

| Resource | Expected use | Risk/caveat |
| --- | --- | --- |
| /system/info | Baseline device information | Contains private device details; do not share raw output |
| /system/capabilities | Check actual 700-supported routes | Share only sanitized endpoint paths |
| /audio/format | Audio codec currently decoded | Format varies by input |
| /system/update/status | Read firmware update status | Does not initiate update; may be unsupported |
| /remote | Read physical BLE remote pairing state | GET has not been device-verified; may fail |
| /system/power/mode/opticalAutoWake | Read auto-wake state | App shows this setting is Off; GET still unverified |

The generic action returns a response or an error. Unsupported endpoints are expected to fail cleanly. Do not call PUT/POST/DELETE to begin pairing, reset a device, change CEC or install firmware until a separate, deliberate test plan is approved.

Afterward, report each endpoint's success/error and whether your existing media player remains responsive. Redact serials, MACs, IPs, tokens, emails and GUIDs from shared logs/responses.

## Digital soundbar remote — no physical Bose remote required

Your Bose media_player entity already supports power, volume, mute, source selection, playback and track changes when the active source supports them. For a button layout, paste docs/virtual-remote.yaml into a new Dashboard > Manual card after replacing EVERY media_player.soundbar with the Bose media_player entity ID. The standard media-control card includes source selection.

NOT implemented: emulating the encrypted/paired physical BLE remote; TV directional/menu/number keys; unrestricted TV IR sending. The Bose /remote pairing API is NOT a digital key sender. The /remote/integration API is a stateful TV setup/test process, not proven as a safe unrestricted remote-control service. Existing HA TV integrations or a compatible IR blaster can add such keys separately.

## Rollback

Restore the saved /config/custom_components/bose folder or full Home Assistant backup. Alternatively remove the fork from HACS and reinstall the original cavefire/Bose-Homeassistant source/version, then restart HA. Preserve the configured Bose device and account settings where possible; there is no need to delete your HA Bose config entry just to switch source.

## Validation

This version passed **176 offline HACS integration tests** and its combined bundled pybose version passed **204 offline unit tests**. These are mock-only checks, not proof of any real Soundbar 700 or Bass Module 700 API response. No automatic pairing or radio changes were performed.


## v1.3.8 audio mode test

The **Audio Mode** select already existed; v1.3.8 fixes its Bose Music method
from POST to PUT and preserves its supported choices on partial updates.
With the soundbar idle, first note its current value (typically Normal).
If the selector advertises Dialogue as a choice, try it once, compare it with
the Bose app's Dialogue Mode state, then restore the original value. Do not
select an unadvertised value or send manual JSON to bypass the safeguards.
If the change fails, capture only the sanitized error and revert to v1.3.7.
The read-only **Soundbar Audio Mode** sensor should agree with the selector.

CEC Option 7 is now labelled; it is only a display improvement. Do not change
CEC modes solely to test its label.

## v1.3.9 accessory and CEC test

The integration now preserves the *other* accessory's enabled state when
enabling/disabling the Bass Module or Rear Speakers. It also ignores partial
accessory notifications lacking the selected enabled flag. This was tested
with mocked connection state, **not by toggling the user's live surrounds**.

After backup and HACS v1.3.9 restart:
1. Inspect the [officially sourced CEC Option 2–7 labels](docs/cec-options.md). Merely open the list;
   **do not change the selected CEC mode**.
2. Inspect the Bass Module and Rear Speaker enabled switches and the existing
   connection diagnostic sensors. They should agree with the official Bose app.
3. If you naturally adjust one audio slider, watch for a responsive state
   change. The integration now sends one command, and preserves its previous
   displayed value if a write fails. No extra button press is needed.
4. **Avoid toggling a working surround or bass module merely to test this
   release.** The changes are designed to prevent accidental disruption.

Any missing/unknown accessory enabled state now prevents the switch from
writing rather than guessing a value. The safe rollback remains HACS v1.3.8.

## v1.3.10 Power Sync and Standby test

- New **Soundbar Power Sync** diagnostic appears only if this Bose model
  advertises `/system/power/macro`. It reports only Enabled, Disabled or
  Unknown. It never sends a power or settings command. This GET has not yet
  been verified on the owner's hardware; an unavailable or missing sensor is
  a useful compatibility result, not a reason to force an API request.
- The existing **Auto Standby** switch continues to control the `noAudio`
  boolean in `/system/power/timeouts`, not every Bose Music standby timer
  choice. On a deliberate change, it first reads `noAudio` and `noVideo`,
  refuses changes if either is unknown and preserves `noVideo`. No
  automatic setting writes occur on installation or restart.
- Initial test: update HACS and restart, inspect the Power Sync diagnostic
  state if present, and verify the Auto Standby switch shows the same
  enabled/disabled state as before. **Do not toggle Standby or Power Sync
  just to test this release**. If you naturally adjust Auto Standby later,
  check that the Bose Music app and HA agree afterwards.
- Rollback: reinstall prior **v1.3.9** from HACS and restart Home Assistant,
  or restore the integration backup.

## v1.3.11 Power Sync master switch test

The existing read-only Soundbar Power Sync diagnostic was already
hardware-verified in v1.3.10: it displays Disabled and matches Bose Music.
This release adds a distinct **Power Sync** configuration switch.

Power Sync affects how the Bose system handles power control of the TV and
connected devices. The master switch uses the official three-field request
shape and leaves the other two settings unchanged. It never writes on
installation, reload or restart. Because a setting change can affect the
connected TV, do not casually toggle it during normal viewing.

Safe initial test:
1. Back up Home Assistant and update the Bose integration to v1.3.11.
2. Restart Home Assistant. Check whether the new Power Sync switch shows Off
   while the read-only Power Sync diagnostic still says Disabled.
3. If the new switch is unavailable, the soundbar may not supply
   powerOnDevice and powerOnTv in its GET response. **Do not force a manual
   write**; share the observed status or a privacy-redacted error instead.
4. At a convenient time, if comfortable changing TV power behaviour, switch
   Power Sync On once in HA. Confirm the Bose app and the HA diagnostic agree.
   Restore its previous Off state. Note whether TV power behaviour changes.
5. Do not change HDMI-CEC, accessory pairing, or unrelated configuration.
   If a control fails, do not repeatedly retry; report the result.

Restore previous v1.3.10 through HACS if needed. Live PUT behaviour has not
yet been independently tested, so the new switch remains experimental.

## v1.3.12 Power Sync field diagnostics and Standby Timer naming

**Soundbar Power Sync** retains its Enabled/Disabled diagnostic value.
Open Home Assistant Developer Tools > States and inspect the corresponding
sensor attributes (not a raw device/API request).

- `configuration`: complete/incomplete/unknown describes whether the GET
  provides all required fields for the experimental Power Sync master switch.
- `enabled_field`, `power_on_device_field`, `power_on_tv_field`:
  show only boolean/string/missing/null/invalid/unknown. They never expose
  device identifiers or any raw field values.
- If the Power Sync switch is disabled and `configuration=incomplete`, the
  other field-status attributes help identify why. **Do not interpret that
  result as definitive proof of a missing Bose remote:** the Bose app asks
  for one, but the response schema alone cannot prove causality.
- Do not bypass the switch's completeness checks, pair accessories/remotes
  or change the Power Sync state to collect diagnostics.

The existing `auto_standby` entity is now named **Standby Timer** without
changing its translation/unique-ID logic. For the Bose Soundbar 700, the
owner's guide documents standby after 20 minutes without audio/interaction
and the option to disable this timer in Bose Music. Offline Bose app request
inspection confirms a boolean PUT /system/power/timeouts payload
(`noAudio` and `noVideo`), not an arbitrary configurable timer interval.
On corresponds to the standard inactivity timer; Off corresponds to Never.
The setter still preserves the separate `noVideo` field.

Bose 700 manual: https://assets.bose.com/content/dam/Bose_DAM/Web/consumer_electronics/global/products/speakers/bose_soundbar_700/pdf/810651_og_soundbar-700_en.pdf
