# Reservation desks

Two desks take bookings against a per-replay ledger.

- `services/` holds one adapter per desk: Studio and Archive.
- `common/` is the reservation kit both desks import: request validation, the ledger, renewals and catalog limits.
- `config/catalog.json` is the allocation catalog. `config/platform-release.lock` records the contents of the current platform distribution.
- `replay.mjs` dispatches operations (`book`, `renew`, `import`, `cancel`, `lookup`, `usage`, `summary`) and stages releases.
- `utilization.mjs` builds the daily statement for each desk.

Ownership is listed in `CODEOWNERS`.
