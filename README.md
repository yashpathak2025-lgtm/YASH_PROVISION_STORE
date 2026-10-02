# YASH PROVISION STORE — FINAL

Production-oriented FastAPI + React PWA source release for a small Indian provision/retail store.

## Important verification note

This repository is the single final release: `YASH_PROVISION_STORE_FINAL`.

It is not labelled 100% production-certified because the build runner used for this delivery could not download missing npm/Python packages or run Docker/PostgreSQL/browser integration. Those gaps are explicitly recorded in `docs/FINAL_AUDIT.md`.

## Local development

### Backend

```bash
cd backend
py -m pip install -r requirements.txt
cd ..
set DATABASE_URL=sqlite:///./yash_provision_store_final.db
alembic upgrade head
uvicorn app.main:app --reload --app-dir backend
```

### Docker

```bash
docker compose up --build
```

The image builds the React frontend, installs backend dependencies, runs Alembic migrations, and starts Uvicorn.

## Security model

- PostgreSQL is the production source of truth.
- Business writes are authorized server-side.
- Stock mutations use PostgreSQL row locking where supported.
- Sale/order/return/payment operations use unique transaction/idempotency identifiers.
- AI never receives arbitrary SQL/database access.
- Without an AI provider configuration, the system does not pretend that deterministic parsing is an LLM.

## Offline POS

Pending sales are stored in IndexedDB and retried with UUID idempotency keys when connectivity returns. The server remains authoritative for stock and duplicate prevention.

## Backup

Owner-only JSON backup and explicitly confirmed restore are available. A restore is considered disaster-recovery verified only after testing against a disposable PostgreSQL database.

## Render

See `docs/RENDER_DEPLOYMENT.md`. Free hosting should be treated as testing/hobby infrastructure, not as a permanent business backup strategy.

## Testing

```bash
pytest -q tests/test_contract.py tests/test_e2e.py
```

The integration E2E test is designed to run after installing the full requirements and uses the PARLE-G ₹5 business workflow.
