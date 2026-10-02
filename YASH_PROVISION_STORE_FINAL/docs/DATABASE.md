# Database

PostgreSQL is the production source of truth. SQLite remains useful for local smoke/integration tests.

Important tables include users, categories, products, product_images, variants, batches, customers, suppliers, sales, sale_items, orders, order_items, stock_movements, credit_ledger, purchases, purchase_items, supplier_payments, expenses, returns, return_items, offers, audit_logs, notifications, settings and payments.

Integrity controls include unique SKU/barcode/order/sale/return/payment identifiers and non-negative stock/price constraints. PostgreSQL row locking is used on stock-changing product reads.

Run migrations with `alembic upgrade head` (Docker does this automatically).
