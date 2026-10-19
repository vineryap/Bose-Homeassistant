# Vendored pybose — temporary home-lab test build

This directory contains the open-source `cavefire/pybose` library (GPLv3),
adapted as a nested Python package for integration testing only.

Base: upstream `main` commit `c4fd766`.
Combined feature source: local `~/dev/pybose` branch
`local/bose-testing`, commit `9ff76bb`.

Included patches:
- Token redaction in WebSocket debug logs
- Physical Bose Universal Remote status/pairing helpers (untested on hardware)
- Public audio format getter
- Midrange and systemSurroundLevel audio setting support
- Read-only firmware update status

The only additional source modification is `from .BoseAuth import BoseAuth`
in `BoseSpeaker.py`, needed for this nested import namespace.

This is **not** intended as an upstream dependency update or long-term
vendoring strategy. After separate upstream pybose PR releases, switch back
to its released pip dependency.

The original vendor package © its authors; see LICENSE. Neither archived
Bose binaries nor user data/credentials are included.
