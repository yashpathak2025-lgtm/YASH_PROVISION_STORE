# Offline POS Sync

The POS uses IndexedDB database `YPS_OFFLINE_V2` with two stores:

- `catalog` — cached active products for offline lookup
- `sales` — pending sale payloads keyed by `idempotency_key`

## Offline sale flow

1. Browser detects offline state.
2. POS creates a cryptographically random UUID with `crypto.randomUUID()`.
3. Sale is persisted locally as `PENDING_SYNC`.
4. UI continues using cached products.
5. When connectivity returns, `/api/sales/sync` replays the payload.
6. Server uses the UUID as the sale idempotency key.
7. Duplicate replay returns the original sale rather than creating another sale.
8. Only a successful server response removes the pending record.

The server remains authoritative for stock. PostgreSQL row locking decides whether competing sales can consume the remaining stock.

The browser cannot guarantee offline freshness; stale stock is therefore rejected by the server during replay rather than trusted from IndexedDB.
