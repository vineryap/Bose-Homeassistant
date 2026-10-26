"""CEC option descriptions are traceable to Bose Soundbar 700 support."""
import json
from pathlib import Path
import pytest

CEC_LABELS = {
    "option2":"Option 2 (older device compatibility)",
    "option3":"Option 3 (TV power-on command missing)",
    "option4":"Option 4 (TV audio not sent to soundbar)",
    "option5":"Option 5 (no audio after HDMI reconnect)",
    "option6":"Option 6 (TV powers back on)",
    "option7":"Option 7 (TV power-on and power-off issues)",
}

@pytest.mark.parametrize("filename",["strings.json","translations/en.json"])
def test_cec_option_labels(filename):
    path=Path(__file__).resolve().parents[1]/"custom_components/bose"/filename
    values=json.loads(path.read_text())["entity"]["select"]["cec_settings"]["state"]
    assert {name:values[name] for name in CEC_LABELS} == CEC_LABELS
