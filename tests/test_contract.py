import ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/'backend/app/main.py').read_text(); TREE=ast.parse(SRC)
ROUTES={(d.func.attr,d.args[0].value) for n in ast.walk(TREE) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) for d in n.decorator_list if isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and isinstance(d.func.value,ast.Name) and d.func.value.id=='app' and d.args and isinstance(d.args[0],ast.Constant)}
def test_required_routes_present():
    required=['/api/health','/api/readiness','/api/products','/api/sales','/api/sales/sync','/api/offline/catalog','/api/orders','/api/returns','/api/purchases','/api/customers/{cid}/payment','/api/backup','/api/restore','/api/ai/command','/api/ai/parse-intent','/api/voice/transcribe','/api/upi/qr','/api/barcodes/pdf']
    assert all(x in {p for _,p in ROUTES} for x in required)
def test_idempotency_and_locking_are_present():
    assert 'with_for_update()' in SRC and 'idempotency_key' in SRC and 'duplicate' in SRC and 'sales_sync' in SRC
def test_security_controls_present():
    assert 'check_login_rate' in SRC and 'X-Content-Type-Options' in SRC and 'require_user' in SRC and 'Authorization' in SRC
def test_no_runtime_table_creation(): assert 'Base.metadata.create_all(engine)' not in SRC
def test_ai_does_not_execute_sql():
    ai=SRC[SRC.index('@app.post("/api/ai/command")'):SRC.index('@app.get("/api/backup")')]
    assert 'execute(' not in ai and 'SQL' in ai and 'response_format' in SRC
def test_fefo_and_batch_safety():
    assert 'expiry_date.is_(None),Batch.expiry_date' in SRC and 'OUT_OF_STOCK' in SRC and 'restore_batches' in SRC and 'batch_allocations' in SRC
def test_voice_upi_offline():
    assert '/api/voice/transcribe' in SRC and '/api/upi/qr' in SRC and '/api/sales/sync' in SRC
def test_pwa_assets():
    for x in ['sw.js','manifest.webmanifest','icon-192.png','icon-512.png']: assert (ROOT/'frontend/public'/x).exists()
