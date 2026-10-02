# E2E Test Report

## PARLE-G ₹5 scenario

The repository contains `tests/test_e2e.py` for the required business scenario:

category → product → purchase/batch → stock → sale → duplicate-sale check → return → backup.

The current runner cannot execute the live FastAPI E2E because declared dependencies such as `python-jose` and `python-barcode` are not installed locally and external package installation is unavailable. This is therefore recorded as **UNVERIFIED**, not PASS.

## Executed verification

- `python -m py_compile backend/app/main.py`: PASS
- `python -m pytest -q tests/test_contract.py`: **8 PASS**
- `python tests/smoke_static.py`: PASS; 73 routes discovered
- frontend `npm run build`: BLOCKED because local `node_modules`/Vite are absent and package installation is unavailable
- Docker build: BLOCKED by unavailable container/package downloads
