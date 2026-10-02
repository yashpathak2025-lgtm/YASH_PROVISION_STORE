# FEATURE MATRIX — CURRENT RELEASE

Status is evidence-based. COMPLETE means the implementation exists across UI/backend/database/workflow and has automated evidence where the current runner can execute it. Runtime-dependent items remain PARTIAL/UNVERIFIED until executed in their target environment.

| Feature | Frontend | Backend | Database | Workflow | Test | Status | Evidence |
|---|---|---|---|---|---|---|---|
| AI provider abstraction | Yes | Yes | N/A | Preview/confirm | Contract | COMPLETE* | `/api/ai/command`, provider adapters |
| Hindi/Hinglish AI | Yes | Yes | N/A | Provider prompt | Contract | PARTIAL* | provider-dependent |
| Voice STT | MediaRecorder | OpenAI STT | N/A | transcript→preview | Static | PARTIAL* | `/api/voice/transcribe` |
| Voice confirmation | Yes | Yes | Audit | preview→confirm | Contract | COMPLETE | mutation requires confirm |
| ZXing barcode camera | Yes | Lookup | Product barcode unique | scan→cart | Static | PARTIAL* | `BrowserMultiFormatReader` |
| A4 barcode labels | Yes | PDF | Product barcode | 15/30/50 | Static | COMPLETE* | `/api/barcodes/pdf` |
| Dynamic UPI QR | Yes | UPI URI | N/A | QR→manual verification→sale | Contract | COMPLETE* | `/api/upi/qr` |
| Offline POS | IndexedDB | Sync endpoint | Sale idempotency | offline→replay | Contract | COMPLETE* | `/api/sales/sync` |
| FEFO | UI inventory | Batch consumption | Batch allocations | sale/cancel/return | Contract | COMPLETE* | `consume_batches`, `restore_batches` |
| Purchase idempotency | UI UUID | Unique key | Alembic 0003 | duplicate-safe | Contract | COMPLETE* | `Purchase.idempotency_key` |
| RBAC | Role-aware UI | Server enforcement | User role | deny/allow | Contract | COMPLETE* | `require_user` |
| Audit timeline | Yes | Yes | AuditLog | sensitive actions | Static | COMPLETE* | `/api/audit` |

`*` means implementation is complete but live target-environment verification is still required where external provider/browser/PostgreSQL infrastructure is involved.
