# Bose Soundbar 700 — temporary HACS test build

Test fork: https://github.com/vineryap/Bose-Homeassistant
Original: https://github.com/cavefire/Bose-Homeassistant
Integration version: 1.3.8.

This fork BUNDLES locally tested pybose source at commit 3d41927 in custom_components/bose/_pybose:
token log redaction, physical remote pairing helpers, audio format getter, extended audio settings, read-only firmware update status, opt-in accessory pairing, and optical auto-wake read/write helpers.
The normal upstream pybose pip dependency is removed to avoid loading its unmodified version.

**New HACS features since v1.3.6:** three read-only accessory connection/pairing sensors; explicit and confirmation-gated accessory pairing start/stop services (not hardware-tested); a read-only Soundbar Audio Mode sensor, a read-only Firmware Update Status sensor; and an explicit Optical Auto-Wake switch. Optical auto-wake is not changed on install or restart. No firmware update/start action is exposed by these new sensors.

This is a temporary test build, not an upstream release or cloud-independent Bose authentication.

## Backup and install

1. Create a FULL Home Assistant backup from Settings > System > Backups and download it. Record your existing Bose integration version and media_player entity IDs. Prefer a time the soundbar is not actively being used.
2. In HACS, go to Custom repositories and add https://github.com/vineryap/Bose-Homeassistant as category Integration.
3. The fork uses the SAME domain 'bose' as the upstream custom integration. You CANNOT run both in one HA. If HACS reports a duplicate, remove the UPSTREAM HACS installation/repository first (do not delete the Bose device/configuration entry from Devices & Services), then install the fork.
4. Install/redownload the fork. Confirm /config/custom_components/bose/manifest.json shows version 1.3.8 AND /config/custom_components/bose/_pybose/BoseSpeaker.py exists. If either check fails, STOP.
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

This version passed **98 offline HACS integration tests** and its combined bundled pybose version passed **175 offline unit tests**. These are mock-only checks, not proof of any real Soundbar 700 or Bass Module 700 API response. No automatic pairing or radio changes were performed.


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
