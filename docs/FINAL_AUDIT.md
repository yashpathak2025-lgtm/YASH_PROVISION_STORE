# FINAL AUDIT — YASH_PROVISION_STORE_FINAL

Audit/rework date: 2026-10-02

## Scope

The current `YASH_PROVISION_STORE_FINAL` archive was re-audited from source, not from the previous audit claims. The specifically requested gap list was checked against `backend/app/main.py`, Alembic revisions, `frontend/src/main.tsx`, package manifests and tests.

## Requested gap disposition

| Gap | Result | Evidence |
|---|---|---|
| Regex-only AI | FIXED WITH PROVIDER ABSTRACTION | `AI_PROVIDER=openai|gemini`; JSON-only provider parsing; fallback explicitly labelled controlled parser |
| Arbitrary SQL risk | FIXED | AI path contains no SQL execution/tool access; schema validation before workflow |
| Hindi/Hinglish structured commands | IMPROVED / PROVIDER-DEPENDENT | provider prompt supports Hindi/English/Hinglish and Hindi/English numbers; fallback remains intentionally limited |
| Voice STT | IMPLEMENTED, PROVIDER-DEPENDENT | MediaRecorder frontend + `/api/voice/transcribe`; requires `OPENAI_API_KEY` |
| Voice destructive confirmation | IMPLEMENTED | transcript returns to editable command UI; AI mutations require Preview then CONFIRM |
| Live camera barcode | IMPLEMENTED | `@zxing/browser` `BrowserMultiFormatReader` integration |
| Barcode PDF 15/30/50 | IMPLEMENTED | backend A4 PDF endpoint + frontend selectable quantities |
| Dynamic UPI QR | IMPLEMENTED | `/api/upi/qr`, UPI URI contains merchant VPA, amount and reference |
| Offline IndexedDB sales | IMPLEMENTED | `YPS_OFFLINE_V2` IndexedDB catalog/sales stores |
| UUID idempotent replay | IMPLEMENTED | `crypto.randomUUID()` + `/api/sales/sync` server-side sale idempotency |
| Batch fields | IMPLEMENTED | Batch model + purchase mfg/expiry persistence |
| FEFO | IMPLEMENTED | valid batches sorted by expiry; expired lots skipped |
| Strict batch shortage | IMPLEMENTED | `OUT_OF_STOCK` if batched stock cannot satisfy valid quantity |
| Batch restoration on return/cancel | IMPLEMENTED | persisted `batch_allocations` and `restore_batches()` |
| Purchase idempotency separate from invoice | FIXED | Alembic `0003_transaction_batch_ai` + `Purchase.idempotency_key` |
| Supplier payable | EXISTING + VERIFIED IN CODE | purchase due + supplier due + supplier payment ledger |
| RBAC | FIXED/REINFORCED | backend `require_user()` normalizes role and checks every protected route |
| Audit timeline | IMPLEMENTED | `/api/audit` + frontend timeline UI |

## Automated verification

- Python compilation: PASS
- Static/contract tests: **8 PASS**
- Static smoke route scan: PASS, **74 routes discovered**
- Frontend production build: NOT VERIFIED in this runner because `node_modules`/Vite are not installed and package-network access is unavailable.
- PostgreSQL integration/E2E: NOT VERIFIED in this runner because required Python packages are unavailable locally.
- Docker build/start: NOT VERIFIED in this runner because container image/package downloads are unavailable.

## Important remaining provider/runtime limitations

1. A real OpenAI/Gemini key is required for broad natural-language parsing. Without it, the application explicitly does not pretend the fallback parser is an LLM.
2. Voice transcription requires an OpenAI API key; browser recording itself is implemented.
3. UPI QR generation is not settlement confirmation. The UI explicitly requires a human verification click before creating the UPI sale.
4. Camera scanning uses ZXing browser decoding and still requires browser camera permission/HTTPS in production.
5. Full PostgreSQL concurrency and the PARLE-G end-to-end scenario still require an environment with the declared dependencies and PostgreSQL runtime.

These are runtime verification limitations, not hidden behind fake success states.
