# Bose Bass Module / Surround Speakers diagnostics (development branch)

This feature is developed on the **local** branch `feature/accessory-diagnostics-readonly`; it is **not part of the published v1.3.6 HACS release**. Do not expect the entities on a running v1.3.6 installation.

## What was added

Three **read-only** sensor entities on the soundbar:
- **Bass Module Connection:** `wired`, `wireless`, `mixed`, `disconnected` or `unknown`.
- **Surround Speakers Connection:** the same connection states.
- **Accessory Pairing Status:** `active`, `inactive` or `unknown`.

The connection sensors also report *aggregate* counts: `available_count`, `wireless_count` and `wired_count`. They never expose accessory serial numbers, MAC addresses or Bose-account information.

They reuse the existing `/accessories` GET snapshot during HACS startup and listen for changes pushed by the soundbar. No additional startup GET and **no pairing/enable/disable requests** are sent. Automatic polling is disabled; an explicit entity refresh can issue a GET to `/accessories`.

A `wired` result means **currently wired**, not necessarily incapable of wireless connection. A `disconnected` result means no accessories of that category are available; it is not proof that pairing would fail.

## Boundaries

- There is **no Start Pairing or Stop Pairing button** in this change. Those are a distinct, high-priority design TODO.
- The archived Bose Music app includes a `PUT` accessory pairing DTO with a `pairing` boolean. Resource routing and impact on already paired surround speakers still need independent verification. Never send speculative writes.
- It is safe to test the new sensors in a mocked integration environment; no direct soundbar commands are necessary for unit tests.
- For a later Home Assistant test, install only an explicitly released fork version after backing up Home Assistant and testing at a quiet time.

## Local validation

Run `.venv/bin/python -m pytest tests -q`; development branch currently passes **58 tests**, including nine new diagnostics tests. Those cover sanitization, malformed or absent status, capability gating, pushing status without writes, and optional GET-only refresh.
