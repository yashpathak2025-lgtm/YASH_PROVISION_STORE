# Initial Audit — V5 starting repository

Audit date: 2026-10-02

## Repository evidence

The supplied archive contained 26 files. The backend was a single `backend/app/main.py` (~687 lines), the frontend a single `frontend/src/main.tsx` (~60 lines), one baseline Alembic revision, one static smoke test, and deployment files.

## Findings

| Area | Status | Evidence |
|---|---|---|
| PostgreSQL support | PARTIAL | SQLAlchemy/psycopg configuration existed, but runtime created tables directly with `Base.metadata.create_all()` instead of relying on Alembic. |
| Alembic migration history | PARTIAL | Only a baseline migration existed and it imported application metadata at runtime; migration path was not executable from repository root until fixed. |
| Product CRUD | PARTIAL | Add/edit/archive endpoints existed, but frontend exposed add/list only and restore was not exposed. |
| Product variants | PARTIAL | Model/endpoints existed; POS and stock workflows operated on product IDs, not variant IDs. |
| Image storage | PARTIAL | Images were stored in PostgreSQL and compressed, but upload validation was primarily MIME based and no explicit secure filename/storage abstraction existed. |
| Barcode | PARTIAL | Manual/keyboard and BarcodeDetector camera flows existed; browser support was not universal and the frontend had no comprehensive scan/unknown-product workflow. |
| QR | PARTIAL | Generic QR generation existed, but there were no typed store/customer/product/order/UPI flows. |
| AI | FAKE/MOCKED for LLM claims | The parser was deterministic regex logic. It must not be described as an LLM. |
| Voice | MISSING | No speech-to-text workflow existed. |
| Inventory | PARTIAL | Stock movements and negative-stock checks existed; batch-aware and variant-aware inventory were incomplete. |
| FEFO | PARTIAL | Batch consumption sorted by expiry, but legacy stock could bypass lots and batch assignment was not enforced. |
| Purchases | PARTIAL | Purchase/stock/batch/supplier-due flow existed; idempotency was incorrectly checked against invoice number. |
| Supplier ledger | PARTIAL | Supplier purchase/payment data existed but no authoritative ledger transaction table. |
| Customer/Udhaar | PARTIAL | Credit balance and ledger existed; payment records were not modeled as a general payment entity. |
| Online order | PARTIAL | Reservation/cancellation/completion existed, but state transitions were overly permissive. |
| POS | PARTIAL | Cash sale was transactional and idempotent; payment record and full receipt workflow were missing. |
| Returns | BROKEN/PARTIAL | A return record existed, but duplicate/partial-return protection was insufficient. |
| Offline POS | PARTIAL | Queue used localStorage, not IndexedDB as required. |
| Conflict handling | PARTIAL | PostgreSQL row locking existed for product sales/orders, but no explicit conflict response contract or offline conflict state existed. |
| Offers | PARTIAL | Offer records existed but checkout did not apply them server-side. |
| Recommendations | PARTIAL | Frequently-bought-together used actual sales data; other recommendation modes were absent. |
| Reports | PARTIAL | Summary and CSV/PDF/XLSX existed; requested report breadth and date filters were incomplete. |
| Analytics | PARTIAL | Historical sales/stock metrics existed; prediction depth and labelled estimates were limited. |
| Security | PARTIAL | JWT, password hashing, role checks existed; rate limiting/security headers and stronger auth hardening were absent. |
| Audit log | PARTIAL | Sensitive operations were logged, but coverage was not exhaustive. |
| Backup/restore | BROKEN | Backup exported data, but restore only restored settings and was not a real database restore. |
| PWA | PARTIAL | Manifest/service worker existed, but icons/cache versioning/offline behavior were incomplete. |
| Deployment | PARTIAL | Docker/Render files existed, but Docker did not run migrations and deployment docs did not establish a verified release pipeline. |
| Monitoring | PARTIAL | Health endpoint existed; readiness/database health and operational failure views were incomplete. |
| Testing | UNTESTED | Only static route/source checks existed; no executable business E2E suite was present. |
