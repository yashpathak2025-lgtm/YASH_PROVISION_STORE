# Architecture

## Runtime

Browser React/Vite PWA → FastAPI API → SQLAlchemy ORM → PostgreSQL.

The browser never receives database credentials. Business writes go through application services/endpoints, authorization, validation, and database transactions.

## Transaction model

Stock-changing PostgreSQL operations acquire a row lock before checking availability. Sale/order/purchase/return writes are committed as one transaction and use unique transaction/idempotency keys where applicable.

## Storage

Product images are stored in PostgreSQL as compressed JPEG bytes in this release, avoiding ephemeral Render filesystem storage. Object storage can be introduced behind the same application boundary later.

## Frontend offline model

IndexedDB stores pending sales with locally generated UUID idempotency keys. Reconnect attempts are sequential; the server remains authoritative for stock and duplicate prevention.

## Deployment

The Docker image builds the React application, installs Python dependencies, copies Alembic migrations, runs `alembic upgrade head`, then starts Uvicorn.
