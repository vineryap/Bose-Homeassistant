# Soundbar 700 software remote: verified scope and protocol boundary

Rechecked 26 October 2026. Offline interoperability research only.

## Already supported without a Bose Universal Remote

Power, volume, mute, source selection and source-dependent playback are
available through the existing HA media_player integration and the sample
`docs/virtual-remote.yaml`. External TV control depends on the TV/CEC
integration, not the physical Bose BLE pairing interface.

## Unsupported remote commands

The owner's Soundbar 700 advertises `/injectKey` in ProductController v1.0
and `/system/buttonEvent`, but there is **no verified request method,
payload, key enum or permitted command set**.

All six archived Bose Music Android DEX files were checked for literal
`/injectKey` or `/system/buttonEvent`. Neither occurs. The available generic
FrontDoor binaries also yielded no such command declaration. Existing
public `pybose` code does not establish the request schema.

The app's `PUT /remote/integration` `ACTION_SEND_KEY` is used in the
remote setup flow; it does not prove ordinary unrestricted TV key sending.

**Do not guess command payloads or send live key/pairing writes.**

## Power Sync and pairing

Live read-only `GET /system/power/macro` reports `enabled` and
`powerOnTv`, but omits `powerOnDevice`. Bose Music requests physical
Universal Remote pairing before enabling Power Sync. These observations
are consistent, but do not establish that pairing directly causes
the field omission. The integration must not synthesize the missing field.

## Unblocking full remote emulation

Obtain a genuine model-specific ProductController handler or reliable
protocol capture showing method, body, keys, permissions and safety
limits. Then add mock-only tests before seeking explicit permission
for any controlled hardware experiment.

Official Bose compatible IR guidance:
https://support.bose.co.uk/article/ssb700-soundbar-using-another-remote-to-control-your-bose-system---ka08c000001pxwpaa2
