# V4 -> V5 audit summary

V4 was inspected from the supplied ZIP, not assumed missing from the checklist.

## V4 findings
- PostgreSQL compatibility existed, but SQLite fallback and `Base.metadata.create_all()` were used; no real Alembic migration history.
- Sale/order stock mutations lacked PostgreSQL row locking.
- Sales had idempotency, but online orders did not.
- Product images were represented as `image_url`; no permanent upload/storage workflow.
- Batch/expiry models and true FEFO were incomplete.
- Returns/offers/recommendations/backup/reporting were not wired through the frontend.
- AI was deterministic and limited to a few commands; it correctly did not execute arbitrary SQL.
- Offline sales were queued in localStorage, but the frontend was not a complete IndexedDB sync system.
- Render configuration did not solve the free Postgres expiry/backup limitation.
- The supplied smoke checklist existed, but there was no evidence in the ZIP of a completed automated end-to-end run.

## V5 changes
The V5 package adds the core production controls listed in the README and feature matrix, including:
- idempotent sales and orders
- PostgreSQL row locking for stock-changing workflows
- negative-stock protection
- product image compression/storage in PostgreSQL
- variants and batch records
- FEFO batch consumption when lot data exists
- customer/supplier ledgers and payments
- purchase, return, offer and recommendation endpoints
- owner backup export
- CSV/PDF/XLSX summary exports
- controlled AI preview/confirm workflow
- PWA shell and offline POS retry queue
- audit logging
- Render/Docker deployment files
- static smoke tests

## Verification boundary
A ZIP can be statically inspected and compiled, but it cannot truthfully prove hardware/browser/provider integrations. The included E2E checklist is the required final verification against the deployed URL and the actual scanner/printer/phone hardware.

This distinction is intentional: “feature exists” is not the same as “feature was tested in the real workflow.”
