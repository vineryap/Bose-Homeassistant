## Fixed
- Updated HDMI-CEC Options 2–7 with Bose's documented troubleshooting descriptions.
- Preserved the other accessory's enabled state when toggling Bass Module or Surround Speakers, rather than sending a null value.
- Prevented incomplete accessory notifications from incorrectly changing enable-switch states.
- Prevented duplicate audio-level writes after timeouts and rejected invalid slider values.
- Preserved audio slider values when partial notifications omit the level.

## Notes
- This is an experimental fork. Back up Home Assistant before updating.
