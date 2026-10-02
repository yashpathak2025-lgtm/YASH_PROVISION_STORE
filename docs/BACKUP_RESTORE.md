# Backup and Restore

## Backup

Owner-only `GET /api/backup` exports the application tables as JSON, including binary image fields as base64.

## Restore

`POST /api/restore` is owner-only. Without `confirm=true` it performs a dry-run count. With `confirm=true`, it replaces the application tables in a single transaction. Test restores must be performed against a disposable database first.

## Verification rule

A backup is not considered disaster-recovery verified until a PostgreSQL restore has been performed and the resulting application passes the E2E suite.
