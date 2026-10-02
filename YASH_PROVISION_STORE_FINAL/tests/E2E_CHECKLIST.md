# V5 final end-to-end checklist

Run this against the actual browser deployment.

1. Login as owner; create manager/staff.
2. Create category and product with Hindi + English name, SKU, barcode, prices, unit and reorder level.
3. Upload a product image; reload/redeploy and confirm image remains.
4. Add a variant and verify variant barcode/SKU.
5. Type barcode into POS; use camera scanner where BarcodeDetector is supported; test USB/Bluetooth keyboard scanner.
6. Complete cash sale; confirm stock movement and sale record.
7. Submit the same idempotency key twice; second call must not create another sale.
8. Create online order; confirm stock reservation; cancel and confirm stock restoration.
9. Complete another order; confirm it becomes a sale exactly once.
10. Receive purchase with supplier, batch and expiry; confirm stock and supplier due.
11. Pay supplier; confirm due decreases.
12. Create customer credit sale; confirm ledger/outstanding; record payment.
13. Return part of a sale; confirm stock restoration and credit adjustment where applicable.
14. Run Hindi AI stock query; run stock-add preview; confirm; verify audit and stock movement.
15. Generate barcode A4 PDF and scan printed label.
16. Generate QR codes from `/api/qr` for store/product/order/UPI payloads.
17. Check low-stock, expiry, slow-moving/no-sale and report endpoints.
18. Export CSV/PDF/XLSX.
19. Disconnect network; make POS sale; reconnect; verify idempotent queue sync.
20. Download owner backup JSON; copy it to a safe location; restore only into a disposable test database and verify records.
21. Verify staff cannot use owner-only endpoints.
22. Verify audit shows who changed what, old value, new value and timestamp.
23. Test on Android Chrome and iPhone Safari separately.
24. Test the actual receipt printer/scanner hardware used by the store.
