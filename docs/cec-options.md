# Soundbar 700 HDMI-CEC troubleshooting options

The Bose soundbar's existing CEC selector is unchanged in behaviour. Only
human-readable Home Assistant descriptions of Options 2–7 were revised.

Bose documents these as *troubleshooting scenarios*, not the exact internal
CEC command/firmware implementation. On your soundbar:

| Option | Home Assistant label | Bose-recommended situation |
| --- | --- | --- |
| Default | Default (CEC active) | Normal CEC operation |
| Off | Off (CEC inactive) | CEC disabled |
| 2 | Option 2 (older device compatibility) | Unexpected/absent control with older devices |
| 3 | Option 3 (TV power-on command missing) | TV doesn't send expected on event |
| 4 | Option 4 (TV audio not sent to soundbar) | TV speaker output rather than soundbar |
| 5 | Option 5 (no audio after HDMI reconnect) | Sound doesn't resume after reconnection |
| 6 | Option 6 (TV powers back on) | TV/device powers itself back on after off |
| 7 | Option 7 (TV power-on and power-off issues) | Both missing on event and defective off response |

Primary official reference, **Bose Smart Soundbar 700**:
https://support.bose.com.au/article/soundbar-700-hdmi-cec-settings?language=en_US

Japanese reference:
https://www.bose.co.jp/ja_jp/support/articles/HC1337/productCodes/bose_soundbar_700/article.html

The descriptions do not guarantee a specific TV model will work better
with another setting. Do not change CEC modes to verify a label-only update.
